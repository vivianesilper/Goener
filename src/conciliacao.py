"""Etapa 2 — Conciliação entre faturas da Enel e cobranças da Goener.

Passo a passo:
  1. `calcular_valor_esperado`: aplica a regra de negócio em cada fatura.
  2. `cruzar_faturas_cobrancas`: junta fatura e boleto pelo par (cliente, mês).
  3. `classificar`: decide a situação de cada caso (OK, a maior, a menor...).
  4. `identificar_causa`: testa hipóteses para explicar cada divergência.
  5. `calcular_impactos`: quanto cada caso custa em R$ e a economia do cliente.
"""
import numpy as np
import pandas as pd

from src import config as cfg

COLUNAS_CLIENTE = ["id_cliente", "nome", "cidade", "desconto_contratado", "status",
                   "data_cancelamento", "flag_revisao", "motivo_revisao"]


# =============================================================================
# 1. Regra de negócio
# =============================================================================
def calcular_valor_esperado(energia_kwh, tarifa, desconto):
    """valor = energia compensada × tarifa × (1 − desconto), arredondado em 2 casas.

    Funciona tanto com números quanto com colunas inteiras (Series).
    Exemplo do enunciado: 500 kWh × 0,95 × (1 − 0,15) = 403,75.
    """
    return np.round(energia_kwh * tarifa * (1 - desconto), cfg.CASAS_DECIMAIS)


def mes_apos_cancelamento(mes_referencia, data_cancelamento):
    """True quando o mês começa DEPOIS da data de cancelamento (não pode ser cobrado).

    Ex.: cancelado em 08/07 -> julho (começa 01/07) ainda é cobrado; agosto não.
    """
    return data_cancelamento.notna() & (mes_referencia > data_cancelamento)


# =============================================================================
# 2. Cruzamento
# =============================================================================
def cruzar_faturas_cobrancas(clientes, faturas, cobrancas):
    """Uma linha por (cliente, mês) com fatura e/ou boleto, mais uma linha por boleto duplicado.

    Usa junção completa (outer): assim aparecem fatura sem boleto E boleto sem fatura.
    """
    fat = faturas.rename(columns={"flag_revisao": "revisao_fatura", "motivo_revisao": "motivo_fatura"})
    fat = fat[["id_cliente", "uc", "mes_referencia", "consumo_kwh", "energia_compensada_kwh",
               "tarifa_kwh", "revisao_fatura", "motivo_fatura"]]

    cob = cobrancas.rename(columns={"flag_revisao": "revisao_cobranca", "motivo_revisao": "motivo_cobranca"})
    cob = cob[["id_cobranca", "id_cliente", "mes_referencia", "valor_cobrado", "data_vencimento",
               "data_pagamento", "status_pagamento", "cobranca_duplicada", "revisao_cobranca",
               "motivo_cobranca"]]

    principais = cob[~cob["cobranca_duplicada"]]
    duplicadas = cob[cob["cobranca_duplicada"]]

    casos = fat.merge(principais, on=["id_cliente", "mes_referencia"], how="outer", indicator="origem")
    # Boleto duplicado vira uma linha própria, com a mesma fatura do mês para comparação
    duplicadas = duplicadas.merge(fat, on=["id_cliente", "mes_referencia"], how="left")
    duplicadas["origem"] = "both"
    if not duplicadas.empty:
        casos = pd.concat([casos, duplicadas], ignore_index=True)

    casos["origem"] = casos["origem"].astype(str).map(
        {"both": "fatura e cobrança", "left_only": "só fatura", "right_only": "só cobrança"})
    casos["cobranca_duplicada"] = casos["cobranca_duplicada"].eq(True)

    cli = clientes[COLUNAS_CLIENTE].rename(columns={
        "status": "status_cliente", "flag_revisao": "revisao_cliente", "motivo_revisao": "motivo_cliente"})
    casos = casos.merge(cli, on="id_cliente", how="left")

    casos["valor_esperado"] = calcular_valor_esperado(
        casos["energia_compensada_kwh"], casos["tarifa_kwh"], casos["desconto_contratado"])
    casos["diferenca"] = np.round(casos["valor_cobrado"] - casos["valor_esperado"], cfg.CASAS_DECIMAIS)
    return casos


# =============================================================================
# 3. Classificação
# =============================================================================
def classificar_caso(caso):
    """Devolve (classificação, motivo) de um caso. A ordem dos testes importa:
    primeiro o que torna a cobrança indevida, depois a falta de dados, por fim o valor.
    """
    tem_fatura = caso["origem"] != "só cobrança"
    tem_cobranca = caso["origem"] != "só fatura"
    cancelado_no_mes = (pd.notna(caso["data_cancelamento"])
                        and caso["mes_referencia"] > caso["data_cancelamento"])

    if tem_fatura and pd.isna(caso["id_cliente"]):
        return cfg.FATURA_SEM_CLIENTE, "UC da fatura não existe no cadastro de clientes."

    if tem_cobranca:
        if caso["cobranca_duplicada"]:
            return cfg.COBRANCA_INDEVIDA, "Boleto duplicado: já existe outro boleto para o mesmo cliente e mês."
        if cancelado_no_mes:
            return cfg.COBRANCA_INDEVIDA, (f"Cliente cancelado em {caso['data_cancelamento']:%d/%m/%Y}; "
                                           "mês começa depois do cancelamento.")
        if not tem_fatura:
            return cfg.COBRANCA_INDEVIDA, "Não existe fatura da Enel para este cliente e mês."

    if not tem_cobranca:
        if cancelado_no_mes:
            return cfg.NAO_COBRAVEL, "Correto não cobrar: mês posterior ao cancelamento."
        if pd.isna(caso["valor_esperado"]):
            return cfg.INCONCLUSIVO, f"Sem cobrança e sem dados para calcular o valor ({_motivos(caso)})."
        return cfg.FATURA_SEM_COBRANCA, "Enel registrou energia compensada, mas a Goener não emitiu boleto."

    if pd.isna(caso["valor_esperado"]) or caso["revisao_fatura"] is True:
        return cfg.INCONCLUSIVO, f"Dados insuficientes ou contraditórios: {_motivos(caso)}."

    if abs(caso["diferenca"]) <= cfg.TOLERANCIA_ARREDONDAMENTO:
        return cfg.OK, "Valor cobrado igual ao esperado (tolerância de arredondamento)."
    if caso["diferenca"] > 0:
        return cfg.COBRADO_A_MAIOR, f"Cobrado R$ {caso['diferenca']:.2f} acima do esperado."
    return cfg.COBRADO_A_MENOR, f"Cobrado R$ {abs(caso['diferenca']):.2f} abaixo do esperado."


def _motivos(caso):
    motivos = [caso.get(c) for c in ("motivo_cliente", "motivo_fatura")]
    return "; ".join(m for m in motivos if isinstance(m, str) and m) or "dado ausente"


# =============================================================================
# 4. Causa provável das divergências
# =============================================================================
def identificar_causa(caso):
    """Recalcula o valor com hipóteses de erro comuns e vê qual reproduz o valor cobrado.

    Se uma hipótese bate com o valor cobrado (dentro da tolerância), ela é a causa provável.
    """
    cobrado = caso["valor_cobrado"]
    if pd.isna(cobrado) or pd.isna(caso["energia_compensada_kwh"]) or pd.isna(caso["desconto_contratado"]):
        return None

    def bate(valor):
        return pd.notna(valor) and abs(cobrado - round(valor, cfg.CASAS_DECIMAIS)) <= cfg.TOLERANCIA_ARREDONDAMENTO

    energia, tarifa, desconto = caso["energia_compensada_kwh"], caso["tarifa_kwh"], caso["desconto_contratado"]
    if bate(caso["valor_esperado"]):
        return None
    for fator in cfg.FATORES_ESCALA:
        if bate(caso["valor_esperado"] * fator):
            return f"Vírgula deslocada: cobrado {fator:g}× o valor correto (erro de digitação)"
    if bate(energia * tarifa):
        return "Desconto contratado não aplicado (cobrado o valor cheio da energia)"
    if bate(caso["consumo_kwh"] * tarifa * (1 - desconto)):
        return "Cobrança calculada sobre o consumo total, não sobre a energia compensada"
    return "Sem padrão identificado: conferir boleto manualmente"


# =============================================================================
# 5. Impacto financeiro e economia
# =============================================================================
def zerar_esperado_quando_nao_cobravel(casos):
    """Quando não deveria existir boleto, o valor correto da cobrança é zero."""
    sem_direito = casos["classificacao"].isin([cfg.COBRANCA_INDEVIDA, cfg.NAO_COBRAVEL])
    casos.loc[sem_direito, "valor_esperado"] = 0.0
    casos.loc[sem_direito, "diferenca"] = casos.loc[sem_direito, "valor_cobrado"]
    return casos


def calcular_impactos(casos):
    """Separa o impacto em colunas para os indicadores e o Power BI somarem direto."""
    classe = casos["classificacao"]
    casos["valor_a_maior"] = np.where(classe == cfg.COBRADO_A_MAIOR, casos["diferenca"], 0.0)
    casos["valor_a_menor"] = np.where(classe == cfg.COBRADO_A_MENOR, -casos["diferenca"], 0.0)
    casos["receita_perdida"] = np.where(classe == cfg.FATURA_SEM_COBRANCA, casos["valor_esperado"], 0.0)
    casos["valor_indevido"] = np.where(classe == cfg.COBRANCA_INDEVIDA, casos["valor_cobrado"], 0.0)

    # Economia do cliente: quanto pagaria à Enel pela energia (sem desconto) menos o boleto Goener.
    cobrado_valido = classe.isin([cfg.OK, cfg.COBRADO_A_MAIOR, cfg.COBRADO_A_MENOR])
    valor_cheio = np.round(casos["energia_compensada_kwh"] * casos["tarifa_kwh"], cfg.CASAS_DECIMAIS)
    casos["economia_contratada"] = np.where(cobrado_valido, valor_cheio - casos["valor_esperado"], 0.0)
    casos["economia_real"] = np.where(cobrado_valido, valor_cheio - casos["valor_cobrado"], 0.0)

    # Situação do boleto na data de corte (base para a inadimplência na Etapa 3)
    vencida = casos["data_vencimento"] < cfg.DATA_CORTE
    casos["vencida"] = vencida
    casos["vencida_nao_paga"] = vencida & (casos["status_pagamento"] != "pago")
    return casos


# =============================================================================
# Orquestração
# =============================================================================
COLUNAS_SAIDA = [
    "classificacao", "motivo", "causa_provavel", "id_cliente", "nome", "cidade", "status_cliente",
    "data_cancelamento", "uc", "mes_referencia", "consumo_kwh", "energia_compensada_kwh", "tarifa_kwh",
    "desconto_contratado", "valor_esperado", "id_cobranca", "valor_cobrado", "diferenca",
    "valor_a_maior", "valor_a_menor", "receita_perdida", "valor_indevido",
    "economia_contratada", "economia_real", "data_vencimento", "data_pagamento",
    "status_pagamento", "vencida", "vencida_nao_paga", "origem",
]


def executar_conciliacao(clientes, faturas, cobrancas):
    """Roda a Etapa 2 completa e devolve uma linha por caso conciliado."""
    casos = cruzar_faturas_cobrancas(clientes, faturas, cobrancas)
    casos[["classificacao", "motivo"]] = casos.apply(classificar_caso, axis=1, result_type="expand")
    casos["causa_provavel"] = casos.apply(identificar_causa, axis=1)
    pista = (casos["classificacao"] == cfg.INCONCLUSIVO) & casos["causa_provavel"].notna()
    casos.loc[pista, "causa_provavel"] = "Pista: " + casos.loc[pista, "causa_provavel"].str.lower()
    casos = zerar_esperado_quando_nao_cobravel(casos)
    casos = calcular_impactos(casos)
    casos["classificacao"] = pd.Categorical(casos["classificacao"], cfg.ORDEM_CLASSIFICACAO, ordered=True)
    return (casos[COLUNAS_SAIDA]
            .sort_values(["classificacao", "id_cliente", "mes_referencia"])
            .reset_index(drop=True))
