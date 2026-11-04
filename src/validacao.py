"""Etapa 4 — Prevenção: validações reutilizáveis para bases novas e lotes de cobrança.

Duas barreiras:
  1. `validar_base` / `validar_arquivo`: CONTRATO DE DADOS. Recebe uma base nova (como chegou)
     e devolve tudo que está fora do padrão, antes de entrar no processo.
  2. `validar_lote_cobranca`: TRAVA ANTES DA EMISSÃO. Confere os boletos que serão emitidos contra
     a regra de negócio; nada sai com valor errado, duplicado ou para cliente cancelado.

Cada regra é uma função pequena que devolve uma máscara True para as linhas inválidas.
Para criar uma regra nova basta escrever a função e incluí-la no contrato da aba.
"""
from dataclasses import dataclass
from typing import Callable

import pandas as pd

from src import config as cfg
from src import limpeza

COLUNAS_RESULTADO = ["aba", "linha", "coluna", "regra", "valor"]


@dataclass(frozen=True)
class Regra:
    coluna: str
    descricao: str
    invalida: Callable[[pd.DataFrame], pd.Series]  # recebe a aba, devolve True onde a regra falha


# =============================================================================
# Blocos de regra reutilizáveis
# =============================================================================
def _texto(df, coluna):
    """Coluna como texto no formato de troca (datas ISO), aceitando base bruta ou tratada."""
    serie = df[coluna]
    if pd.api.types.is_datetime64_any_dtype(serie):
        formato = "%Y-%m" if coluna == "mes_referencia" else "%Y-%m-%d"
        return serie.dt.strftime(formato).astype("string")
    return serie.astype("string").str.strip()


def vazio(coluna):
    return lambda df: df[coluna].isna() | (_texto(df, coluna) == "")


def fora_do_formato(coluna, padrao):
    return lambda df: df[coluna].notna() & ~_texto(df, coluna).str.fullmatch(padrao).fillna(False)


def fora_da_lista(coluna, permitidos):
    return lambda df: df[coluna].notna() & ~_texto(df, coluna).isin(permitidos)


def numero(df, coluna):
    """Número só se estiver no formato padrão (ponto decimal); senão NaN."""
    return pd.to_numeric(_texto(df, coluna).where(_texto(df, coluna).str.fullmatch(limpeza.PADRAO_NUMERO)),
                         errors="coerce")


def fora_da_faixa(coluna, minimo=None, maximo=None, minimo_exclusivo=False):
    def regra(df):
        valor = numero(df, coluna)
        falha = pd.Series(False, index=df.index)
        if minimo is not None:
            falha |= (valor <= minimo) if minimo_exclusivo else (valor < minimo)
        if maximo is not None:
            falha |= valor > maximo
        return falha.fillna(False)
    return regra


def repetido(*colunas):
    return lambda df: df.duplicated(list(colunas), keep=False)


def _data(df, coluna):
    return pd.to_datetime(_texto(df, coluna), format="%Y-%m-%d", errors="coerce")


# =============================================================================
# Contratos por aba
# =============================================================================
PADRAO_DOCUMENTO = rf"\d{{{cfg.DIGITOS_CPF}}}|\d{{{cfg.DIGITOS_CNPJ}}}"
PADRAO_ID_CLIENTE = r"C\d+"
PADRAO_ID_COBRANCA = r"GB\d+"

CONTRATOS = {
    cfg.ABA_CLIENTES: [
        Regra("id_cliente", "obrigatório", vazio("id_cliente")),
        Regra("id_cliente", "formato C + números", fora_do_formato("id_cliente", PADRAO_ID_CLIENTE)),
        Regra("id_cliente", "único na base", repetido("id_cliente")),
        Regra("nome", "obrigatório", vazio("nome")),
        Regra("nome", "sem espaços nas pontas", lambda df: df["nome"].notna()
              & (df["nome"].astype("string") != df["nome"].astype("string").str.strip())),
        Regra("cpf_cnpj", "11 (CPF) ou 14 (CNPJ) dígitos, sem pontuação",
              fora_do_formato("cpf_cnpj", PADRAO_DOCUMENTO)),
        Regra("uc", "obrigatória", vazio("uc")),
        Regra("uc", f"{cfg.DIGITOS_UC} dígitos com zeros à esquerda", fora_do_formato("uc", limpeza.PADRAO_UC)),
        Regra("uc", "única entre clientes", repetido("uc")),
        Regra("desconto_contratado", "obrigatório", vazio("desconto_contratado")),
        Regra("desconto_contratado", "fração com ponto decimal (ex.: 0.15)",
              fora_do_formato("desconto_contratado", limpeza.PADRAO_FRACAO)),
        Regra("data_adesao", "data AAAA-MM-DD", fora_do_formato("data_adesao", limpeza.PADRAO_DATA)),
        Regra("status", "ativo ou cancelado", fora_da_lista("status", cfg.STATUS_CLIENTE_VALIDOS)),
        Regra("data_cancelamento", "obrigatória para cliente cancelado",
              lambda df: (_texto(df, "status") == "cancelado") & vazio("data_cancelamento")(df)),
        Regra("data_cancelamento", "vazia para cliente ativo",
              lambda df: (_texto(df, "status") == "ativo") & ~vazio("data_cancelamento")(df)),
        Regra("data_cancelamento", "data AAAA-MM-DD",
              fora_do_formato("data_cancelamento", limpeza.PADRAO_DATA)),
        Regra("data_cancelamento", "não pode ser anterior à adesão",
              lambda df: (_data(df, "data_cancelamento") < _data(df, "data_adesao")).fillna(False)),
    ],
    cfg.ABA_FATURAS: [
        Regra("uc", f"{cfg.DIGITOS_UC} dígitos com zeros à esquerda", fora_do_formato("uc", limpeza.PADRAO_UC)),
        Regra("mes_referencia", "mês AAAA-MM", fora_do_formato("mes_referencia", limpeza.PADRAO_MES)),
        Regra("consumo_kwh", "número com ponto decimal", fora_do_formato("consumo_kwh", limpeza.PADRAO_NUMERO)),
        Regra("consumo_kwh", "não pode ser negativo", fora_da_faixa("consumo_kwh", minimo=0)),
        Regra("energia_compensada_kwh", "obrigatória", vazio("energia_compensada_kwh")),
        Regra("energia_compensada_kwh", "não pode ser negativa", fora_da_faixa("energia_compensada_kwh", minimo=0)),
        Regra("energia_compensada_kwh", "não pode ser maior que o consumo",
              lambda df: (numero(df, "energia_compensada_kwh") > numero(df, "consumo_kwh").abs()).fillna(False)),
        Regra("tarifa_kwh", "número positivo com ponto decimal",
              lambda df: fora_do_formato("tarifa_kwh", limpeza.PADRAO_NUMERO)(df)
              | fora_da_faixa("tarifa_kwh", minimo=0, minimo_exclusivo=True)(df)),
        Regra("uc", "uma fatura por UC e mês", repetido("uc", "mes_referencia")),
    ],
    cfg.ABA_COBRANCAS: [
        Regra("id_cobranca", "formato GB + números", fora_do_formato("id_cobranca", PADRAO_ID_COBRANCA)),
        Regra("id_cobranca", "único na base", repetido("id_cobranca")),
        Regra("id_cliente", "formato C + números", fora_do_formato("id_cliente", PADRAO_ID_CLIENTE)),
        Regra("mes_referencia", "mês AAAA-MM", fora_do_formato("mes_referencia", limpeza.PADRAO_MES)),
        Regra("valor_cobrado", "número com ponto decimal (sem R$)",
              fora_do_formato("valor_cobrado", limpeza.PADRAO_NUMERO)),
        Regra("valor_cobrado", "maior que zero", fora_da_faixa("valor_cobrado", minimo=0, minimo_exclusivo=True)),
        Regra("data_vencimento", "data AAAA-MM-DD", fora_do_formato("data_vencimento", limpeza.PADRAO_DATA)),
        Regra("data_pagamento", "data AAAA-MM-DD", fora_do_formato("data_pagamento", limpeza.PADRAO_DATA)),
        Regra("status_pagamento", "pago ou em aberto",
              fora_da_lista("status_pagamento", cfg.STATUS_PAGAMENTO_VALIDOS)),
        Regra("data_pagamento", "obrigatória quando status é pago",
              lambda df: (_texto(df, "status_pagamento").str.lower() == "pago") & vazio("data_pagamento")(df)),
        Regra("id_cliente", "um boleto por cliente e mês", repetido("id_cliente", "mes_referencia")),
    ],
}


# =============================================================================
# Barreira 1: contrato de dados
# =============================================================================
def validar_base(df, aba, contrato=None):
    """Aplica o contrato da aba e devolve uma linha por violação (vazio = base dentro do padrão)."""
    contrato = contrato if contrato is not None else CONTRATOS[aba]
    violacoes = []
    for regra in contrato:
        falhas = df.index[regra.invalida(df).to_numpy(dtype=bool)]
        violacoes += [{"aba": aba, "linha": idx + 2, "coluna": regra.coluna, "regra": regra.descricao,
                       "valor": df.at[idx, regra.coluna]} for idx in falhas]
    return pd.DataFrame(violacoes, columns=COLUNAS_RESULTADO)


def validar_relacionamentos(clientes, faturas, cobrancas):
    """Confere se as abas se ligam: UC da fatura e cliente da cobrança precisam existir no cadastro."""
    ucs = set(_texto(clientes, "uc"))
    ids = set(_texto(clientes, "id_cliente"))
    violacoes = [{"aba": cfg.ABA_FATURAS, "linha": idx + 2, "coluna": "uc",
                  "regra": "UC precisa existir no cadastro de clientes", "valor": faturas.at[idx, "uc"]}
                 for idx in faturas.index[~_texto(faturas, "uc").isin(ucs)]]
    violacoes += [{"aba": cfg.ABA_COBRANCAS, "linha": idx + 2, "coluna": "id_cliente",
                   "regra": "cliente precisa existir no cadastro", "valor": cobrancas.at[idx, "id_cliente"]}
                  for idx in cobrancas.index[~_texto(cobrancas, "id_cliente").isin(ids)]]
    return pd.DataFrame(violacoes, columns=COLUNAS_RESULTADO)


def validar_arquivo(caminho=cfg.ARQUIVO_BASE):
    """Valida um arquivo novo inteiro (as três abas e o relacionamento entre elas)."""
    abas = limpeza.carregar_base(caminho)
    resultados = [validar_base(df, aba) for aba, df in abas.items()]
    resultados.append(validar_relacionamentos(abas[cfg.ABA_CLIENTES], abas[cfg.ABA_FATURAS],
                                              abas[cfg.ABA_COBRANCAS]))
    return pd.concat(resultados, ignore_index=True)


def resumo_violacoes(violacoes):
    return (violacoes.groupby(["aba", "coluna", "regra"], sort=False).size()
            .reset_index(name="linhas_fora_do_padrao"))


# =============================================================================
# Barreira 2: trava antes da emissão dos boletos
# =============================================================================
def validar_lote_cobranca(clientes, faturas, cobrancas_propostas):
    """Concilia o lote ANTES de emitir. Só sai boleto classificado como OK.

    Devolve (aprovados, bloqueados, faltantes):
      - aprovados: boletos que batem com a fatura e a regra;
      - bloqueados: boletos com valor errado, duplicados, sem fatura ou de cliente cancelado;
      - faltantes: faturas cobráveis sem boleto no lote (evita receita perdida).
    """
    from src.conciliacao import executar_conciliacao  # import local: evita dependência circular

    casos = executar_conciliacao(clientes, faturas, cobrancas_propostas)
    tem_boleto = casos["id_cobranca"].notna()
    aprovados = casos[tem_boleto & (casos["classificacao"] == cfg.OK)]
    bloqueados = casos[tem_boleto & (casos["classificacao"] != cfg.OK)]
    faltantes = casos[casos["classificacao"] == cfg.FATURA_SEM_COBRANCA]
    return aprovados, bloqueados, faltantes
