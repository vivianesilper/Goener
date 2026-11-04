"""Etapa 1 — Tratamento e qualidade dos dados.

Organização:
  1. Funções de normalização: recebem UM valor bruto e devolvem o valor padronizado
     (ou None quando não dá para recuperar). São reaproveitadas na Etapa 4 (validação).
  2. Funções `tratar_<aba>`: aplicam as normalizações, procuram problemas de negócio
     e registram cada achado no log com a ação tomada e o porquê.
  3. `verificar_relacionamentos`: confere se as abas se ligam entre si.

Toda linha que precisa de olhar humano recebe `flag_revisao = True` e o motivo em
`motivo_revisao`. Assim a conciliação (Etapa 2) sabe quando o caso é inconclusivo.
"""
import re
import unicodedata

import pandas as pd

from src import config as cfg
from src.log_inconsistencias import LogInconsistencias

# Padrão final esperado de cada tipo de campo. Valor que já chega assim não é logado.
PADRAO_UC = rf"\d{{{cfg.DIGITOS_UC}}}"
PADRAO_DATA = r"\d{4}-\d{2}-\d{2}"
PADRAO_MES = r"\d{4}-\d{2}"
PADRAO_NUMERO = r"-?\d+(\.\d+)?"
PADRAO_FRACAO = r"0(\.\d+)?|1(\.0+)?"

PALAVRAS_MINUSCULAS_NOME = {"da", "de", "do", "das", "dos", "e", "em"}


# =============================================================================
# 1. Normalização de valores individuais
# =============================================================================
def somente_digitos(valor):
    """Remove tudo que não é número: '009082600-0' -> '0090826000'."""
    if pd.isna(valor):
        return None
    return re.sub(r"\D", "", str(valor)) or None


def normalizar_uc(valor):
    """UC com exatamente 10 dígitos, recolocando zeros à esquerda perdidos pelo Excel."""
    digitos = somente_digitos(valor)
    if digitos is None or len(digitos) > cfg.DIGITOS_UC:
        return None
    return digitos.zfill(cfg.DIGITOS_UC)


def normalizar_documento(valor):
    """CPF com 11 dígitos ou CNPJ com 14, recolocando zeros à esquerda.

    Até 11 dígitos é tratado como CPF; de 12 a 14 como CNPJ.
    """
    digitos = somente_digitos(valor)
    if digitos is None or len(digitos) > cfg.DIGITOS_CNPJ:
        return None
    tamanho = cfg.DIGITOS_CPF if len(digitos) <= cfg.DIGITOS_CPF else cfg.DIGITOS_CNPJ
    return digitos.zfill(tamanho)


def tipo_documento(documento):
    if documento is None:
        return None
    return "CPF" if len(documento) == cfg.DIGITOS_CPF else "CNPJ"


def normalizar_numero(valor):
    """Converte '0,9184', 'R$ 9.666,09', '256.71' e '361' em float.

    Se o texto tem vírgula, é formato brasileiro (ponto = milhar, vírgula = decimal).
    """
    if pd.isna(valor):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).replace("R$", "").replace(" ", "").strip()
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def normalizar_percentual(valor):
    """Desconto como fração: '15%', '15', '15,0' e '0.15' viram 0.15."""
    numero = normalizar_numero(str(valor).replace("%", "")) if pd.notna(valor) else None
    if numero is None:
        return None
    return round(numero / 100, 4) if numero > 1 else numero


def normalizar_data(valor):
    """Aceita 'AAAA-MM-DD' e 'DD/MM/AAAA' (padrão brasileiro)."""
    if pd.isna(valor):
        return None
    texto = str(valor).strip()[:10]
    formato = "%Y-%m-%d" if re.fullmatch(PADRAO_DATA, texto) else "%d/%m/%Y"
    data = pd.to_datetime(texto, format=formato, errors="coerce")
    return None if pd.isna(data) else data


def normalizar_mes(valor):
    """Mês de referência como 1º dia do mês. Aceita '2026-04', '04/2026' e 'abr/26'."""
    if pd.isna(valor):
        return None
    texto = str(valor).strip().lower()
    if m := re.fullmatch(r"(\d{4})-(\d{2})", texto):
        ano, mes = int(m[1]), int(m[2])
    elif m := re.fullmatch(r"(\d{2})/(\d{4})", texto):
        ano, mes = int(m[2]), int(m[1])
    elif (m := re.fullmatch(r"([a-z]{3})/(\d{2})", texto)) and m[1] in cfg.MESES_PT:
        ano, mes = 2000 + int(m[2]), cfg.MESES_PT[m[1]]
    else:
        return None
    return pd.Timestamp(year=ano, month=mes, day=1)


def normalizar_texto(valor):
    """Tira espaços nas pontas e espaços duplos."""
    if pd.isna(valor):
        return None
    return re.sub(r"\s+", " ", str(valor)).strip()


def normalizar_nome(valor):
    """'  OTÁVIO BEZERRA NOGUEIRA ' -> 'Otávio Bezerra Nogueira' ('da', 'de'... minúsculos)."""
    texto = normalizar_texto(valor)
    if texto is None:
        return None
    palavras = texto.lower().split(" ")
    return " ".join(p if p in PALAVRAS_MINUSCULAS_NOME and i > 0 else p.capitalize()
                    for i, p in enumerate(palavras))


def chave_texto(valor):
    """Versão sem acento e minúscula, usada só para comparar textos."""
    texto = normalizar_texto(valor) or ""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()


# =============================================================================
# Auxiliares de log
# =============================================================================
def _preparar(df_bruto, coluna_chave):
    """Copia a aba e guarda de onde veio cada linha (linha do Excel) para rastreio."""
    df = df_bruto.copy()
    df.insert(0, "linha_origem", df.index + 2)  # +2: cabeçalho e índice começando em 0
    df["registro"] = (df[coluna_chave].astype(str).str.strip()
                      + " (linha " + df["linha_origem"].astype(str) + ")")
    df["flag_revisao"] = False
    df["motivo_revisao"] = ""
    return df


def _sinalizar(df, indices, motivo):
    """Marca linhas para revisão humana sem apagá-las."""
    df.loc[indices, "flag_revisao"] = True
    df.loc[indices, "motivo_revisao"] = (df.loc[indices, "motivo_revisao"]
                                         .where(df.loc[indices, "motivo_revisao"] == "",
                                                df.loc[indices, "motivo_revisao"] + "; ")
                                         + motivo)


def _padronizar_coluna(df, coluna, funcao, padrao, log, aba, problema, justificativa,
                       formatar=str):
    """Aplica `funcao` na coluna e registra no log cada valor que estava fora do padrão.

    - Valor recuperável  -> ação 'corrigido'.
    - Valor irrecuperável -> fica vazio e vai para revisão humana.
    `padrao` é a expressão regular do formato final; `formatar` transforma o
    valor tratado em texto quando o padrão for uma comparação direta.
    """
    originais = df[coluna]
    tratados = originais.map(funcao)
    texto_original = originais.astype("string").str.strip()
    if padrao is None:  # compara texto tratado com o original (ex.: nomes, cidades)
        fora_padrao = originais.notna() & (originais.astype("string")
                                           != tratados.map(lambda v: formatar(v) if v is not None else None))
    else:
        fora_padrao = originais.notna() & ~texto_original.str.fullmatch(padrao).fillna(False)

    for idx in df.index[fora_padrao & tratados.notna()]:
        log.registrar(aba, df.at[idx, "registro"], coluna, problema, originais[idx],
                      formatar(tratados[idx]), cfg.CORRIGIDO, justificativa)

    irrecuperaveis = df.index[originais.notna() & tratados.isna()]
    for idx in irrecuperaveis:
        log.registrar(aba, df.at[idx, "registro"], coluna, f"{coluna} ilegível",
                      originais[idx], None, cfg.REVISAO,
                      "Não foi possível interpretar o valor com segurança.")
    _sinalizar(df, irrecuperaveis, f"{coluna} ilegível")
    df[coluna] = tratados
    return df


def _fmt_data(valor):
    return valor.strftime("%Y-%m-%d")


def _fmt_mes(valor):
    return valor.strftime("%Y-%m")


def _registrar_linhas(df, indices, log, aba, coluna, problema, acao, justificativa,
                      tratar_valor=None):
    """Registra várias linhas de uma vez. `tratar_valor` mostra o valor depois da correção."""
    for idx in indices:
        valor = df.at[idx, coluna] if coluna in df.columns else None
        tratado = tratar_valor(valor) if tratar_valor else valor
        log.registrar(aba, df.at[idx, "registro"], coluna, problema, valor, tratado, acao,
                      justificativa)


# =============================================================================
# 2. Tratamento por aba
# =============================================================================
def tratar_clientes(df_bruto, log):
    aba = cfg.ABA_CLIENTES
    df = _preparar(df_bruto, "id_cliente")

    # --- formatos -------------------------------------------------------------
    df = _padronizar_coluna(df, "id_cliente", lambda v: normalizar_texto(v).upper(), r"C\d+",
                            log, aba, "id_cliente fora do padrão", "Padronizado em maiúsculas sem espaços.")
    df = _padronizar_coluna(df, "nome", normalizar_nome, None, log, aba,
                            "Nome com espaços extras ou caixa despadronizada",
                            "Removidos espaços nas pontas; nome em formato Título para evitar falsos duplicados.")
    df = _padronizar_coluna(df, "cidade", lambda v: normalizar_nome(v), None, log, aba,
                            "Cidade com espaços extras ou caixa despadronizada",
                            "Mesma cidade escrita de formas diferentes ('FORTALEZA', ' fortaleza ') "
                            "quebraria agrupamentos por cidade.")
    df = _padronizar_coluna(df, "uc", normalizar_uc, PADRAO_UC, log, aba,
                            "UC sem os 10 dígitos (zeros à esquerda perdidos ou pontuação)",
                            "A UC é a chave de ligação com as faturas; o Excel removeu os zeros à esquerda. "
                            "Recolocados até completar 10 dígitos.")
    df = _corrigir_documentos(df, log, aba)
    df = _padronizar_coluna(df, "desconto_contratado", normalizar_percentual, PADRAO_FRACAO, log, aba,
                            "Desconto em formato misto (15%, 15, 15,0, 0.15)",
                            "Convertido para fração (0.15). Valores > 1 interpretados como percentual.")
    for coluna in ("data_adesao", "data_cancelamento"):
        df = _padronizar_coluna(df, coluna, normalizar_data, PADRAO_DATA, log, aba,
                                "Data em formato DD/MM/AAAA misturado com AAAA-MM-DD",
                                "Convertida para AAAA-MM-DD. Premissa: barras = padrão brasileiro "
                                "(nenhuma data tem mês > 12 na 2ª posição, o que confirma).",
                                formatar=_fmt_data)
    df = _padronizar_coluna(df, "status", lambda v: normalizar_texto(v).lower(), None, log, aba,
                            "Status com caixa/espaços despadronizados", "Padronizado em minúsculas.")

    # --- regras de negócio ---------------------------------------------------
    sem_desconto = df.index[df["desconto_contratado"].isna() & df_bruto["desconto_contratado"].isna()]
    _registrar_linhas(df, sem_desconto, log, aba, "desconto_contratado", "Desconto contratado vazio",
                      cfg.REVISAO, "Sem desconto não é possível calcular a cobrança. Não inventamos um "
                      "valor: o cliente segue na base e a conciliação fica 'Inconclusiva' até o "
                      "comercial informar o contrato.")
    _sinalizar(df, sem_desconto, "desconto vazio")

    fora_faixa = df.index[df["desconto_contratado"].notna()
                          & ~df["desconto_contratado"].between(cfg.DESCONTO_MIN, cfg.DESCONTO_MAX)]
    _registrar_linhas(df, fora_faixa, log, aba, "desconto_contratado", "Desconto fora de 0% a 100%",
                      cfg.REVISAO, "Valor impossível; precisa de confirmação do contrato.")
    _sinalizar(df, fora_faixa, "desconto fora da faixa")

    status_invalido = df.index[~df["status"].isin(cfg.STATUS_CLIENTE_VALIDOS)]
    _registrar_linhas(df, status_invalido, log, aba, "status", "Status desconhecido",
                      cfg.REVISAO, "Só existem 'ativo' e 'cancelado'.")
    _sinalizar(df, status_invalido, "status inválido")

    cancelado = df["status"] == "cancelado"
    sem_data = df.index[cancelado & df["data_cancelamento"].isna()]
    _registrar_linhas(df, sem_data, log, aba, "data_cancelamento", "Cliente cancelado sem data de cancelamento",
                      cfg.REVISAO, "Sem a data não dá para saber a partir de quando parar de cobrar.")
    _sinalizar(df, sem_data, "cancelado sem data")

    ativo_com_data = df.index[~cancelado & df["data_cancelamento"].notna()]
    _registrar_linhas(df, ativo_com_data, log, aba, "data_cancelamento", "Cliente ativo com data de cancelamento",
                      cfg.REVISAO, "Status e data se contradizem.")
    _sinalizar(df, ativo_com_data, "ativo com data de cancelamento")

    cancel_antes_adesao = df.index[df["data_cancelamento"] < df["data_adesao"]]
    _registrar_linhas(df, cancel_antes_adesao, log, aba, "data_cancelamento", "Cancelamento antes da adesão",
                      cfg.REVISAO, "Datas impossíveis.")
    _sinalizar(df, cancel_antes_adesao, "cancelamento antes da adesão")

    df = _remover_clientes_duplicados(df, log, aba)
    _sinalizar_chaves_repetidas(df, "uc", log, aba, "Mesma UC em clientes diferentes",
                                "Uma UC pertence a um único cliente; a fatura não teria dono definido.")
    _sinalizar_chaves_repetidas(df, "cpf_cnpj", log, aba, "Mesmo CPF/CNPJ em clientes diferentes",
                                "Pode ser legítimo (um titular com várias UCs), mas merece conferência.")
    return df


def _corrigir_documentos(df, log, aba):
    """CPF/CNPJ só com dígitos e com o tamanho correto.

    Premissa: os documentos são fictícios (o enunciado avisa) e quase nenhum tem
    dígito verificador válido, então validamos apenas a quantidade de dígitos.
    """
    originais = df["cpf_cnpj"]
    digitos = originais.map(somente_digitos)
    tratados = originais.map(normalizar_documento)

    for idx in df.index:
        bruto, sem_pontos, final = originais[idx], digitos[idx], tratados[idx]
        if final is None:
            log.registrar(aba, df.at[idx, "registro"], "cpf_cnpj", "CPF/CNPJ com tamanho impossível",
                          bruto, None, cfg.REVISAO, "Não tem 11 nem 14 dígitos mesmo após correções.")
            _sinalizar(df, [idx], "documento inválido")
        elif len(sem_pontos) not in (cfg.DIGITOS_CPF, cfg.DIGITOS_CNPJ):
            log.registrar(aba, df.at[idx, "registro"], "cpf_cnpj",
                          "CPF/CNPJ com zeros à esquerda perdidos", bruto, final, cfg.CORRIGIDO,
                          "O Excel trata documento como número e apaga zeros iniciais. Completado "
                          "com zeros até 11 dígitos (CPF) ou 14 (CNPJ).")
        elif str(bruto) != final:
            log.registrar(aba, df.at[idx, "registro"], "cpf_cnpj", "CPF/CNPJ com pontuação",
                          bruto, final, cfg.CORRIGIDO, "Guardado só com dígitos para permitir comparação.")
    df["cpf_cnpj"] = tratados
    df.insert(df.columns.get_loc("cpf_cnpj") + 1, "tipo_documento", tratados.map(tipo_documento))
    return df


def _remover_clientes_duplicados(df, log, aba):
    """Mesmo id_cliente repetido. Se os dados são iguais após padronizar, descarta a cópia."""
    colunas_dados = ["nome", "cpf_cnpj", "uc", "cidade", "desconto_contratado",
                     "data_adesao", "status", "data_cancelamento"]
    repetidos = df[df.duplicated("id_cliente", keep=False)]
    descartar = []
    for id_cliente, grupo in repetidos.groupby("id_cliente"):
        identicos = len(grupo[colunas_dados].astype(str).drop_duplicates()) == 1
        for idx in grupo.index[1:]:
            if identicos:
                log.registrar(aba, df.at[idx, "registro"], "id_cliente", "Cliente duplicado",
                              id_cliente, f"mantida linha {grupo.iloc[0]['linha_origem']}", cfg.DESCARTADO,
                              "Depois de padronizar, os dados são idênticos à outra linha (só mudava "
                              "caixa/pontuação). Manter os dois dobraria as faturas na conciliação.")
                descartar.append(idx)
            else:
                log.registrar(aba, df.at[idx, "registro"], "id_cliente",
                              "Cliente duplicado com dados diferentes", id_cliente, None, cfg.REVISAO,
                              "Não dá para saber qual versão é a correta.")
                _sinalizar(df, grupo.index, "cliente duplicado com dados diferentes")
    return df.drop(index=descartar)


def _sinalizar_chaves_repetidas(df, coluna, log, aba, problema, justificativa):
    repetidos = df.index[df[coluna].notna() & df.duplicated(coluna, keep=False)]
    _registrar_linhas(df, repetidos, log, aba, coluna, problema, cfg.REVISAO, justificativa)
    _sinalizar(df, repetidos, problema.lower())


def tratar_faturas(df_bruto, log):
    aba = cfg.ABA_FATURAS
    df = df_bruto.copy()
    df["chave"] = "UC " + df["uc"].astype(str).str.strip() + " | " + df["mes_referencia"].astype(str)
    df = _preparar(df, "chave").drop(columns="chave")

    df = _padronizar_coluna(df, "uc", normalizar_uc, PADRAO_UC, log, aba,
                            "UC sem os 10 dígitos (zeros perdidos, espaço ou hífen)",
                            "Removidos espaços/hífens e recolocados zeros à esquerda para casar com o cadastro.")
    df = _padronizar_coluna(df, "mes_referencia", normalizar_mes, PADRAO_MES, log, aba,
                            "Mês de referência em 3 formatos (2026-04, 04/2026, abr/26)",
                            "Convertido para AAAA-MM.", formatar=_fmt_mes)
    for coluna in ("consumo_kwh", "energia_compensada_kwh", "tarifa_kwh"):
        df = _padronizar_coluna(df, coluna, normalizar_numero, PADRAO_NUMERO, log, aba,
                                "Número com vírgula decimal", "Convertido para número com ponto decimal.")

    # --- regras de negócio ---------------------------------------------------
    negativo = df["consumo_kwh"] < 0
    sinal_trocado = df.index[negativo & (df["energia_compensada_kwh"].fillna(0) <= df["consumo_kwh"].abs())]
    _registrar_linhas(df, sinal_trocado, log, aba, "consumo_kwh", "Consumo negativo", cfg.CORRIGIDO,
                      "Consumo não pode ser negativo. A energia compensada é positiva e cabe no valor "
                      "absoluto, indicando sinal invertido na exportação. Usado o valor absoluto.",
                      tratar_valor=abs)
    df.loc[sinal_trocado, "consumo_kwh"] = df.loc[sinal_trocado, "consumo_kwh"].abs()
    outros_negativos = df.index[df["consumo_kwh"] < 0]
    _registrar_linhas(df, outros_negativos, log, aba, "consumo_kwh", "Consumo negativo", cfg.REVISAO,
                      "Negativo e incompatível com a energia compensada.")
    _sinalizar(df, outros_negativos, "consumo negativo")

    sem_compensada = df.index[df["energia_compensada_kwh"].isna()]
    _registrar_linhas(df, sem_compensada, log, aba, "energia_compensada_kwh", "Energia compensada vazia",
                      cfg.REVISAO, "É a base do cálculo da cobrança. Não estimamos: a conciliação desse "
                      "mês fica 'Inconclusiva' até a fatura ser consultada na Enel.")
    _sinalizar(df, sem_compensada, "energia compensada vazia")

    compensada_maior = df.index[df["energia_compensada_kwh"] > df["consumo_kwh"]]
    _registrar_linhas(df, compensada_maior, log, aba, "energia_compensada_kwh",
                      "Energia compensada maior que o consumo", cfg.REVISAO,
                      "Impossível pela regra (compensada nunca supera o consumo). Não sabemos qual dos "
                      "dois está errado, então o caso fica 'Inconclusivo'.")
    _sinalizar(df, compensada_maior, "compensada > consumo")

    sem_valor = df.index[(df["energia_compensada_kwh"] < 0) | (df["tarifa_kwh"] <= 0)]
    _registrar_linhas(df, sem_valor, log, aba, "tarifa_kwh", "Compensada negativa ou tarifa zerada",
                      cfg.REVISAO, "Valores impossíveis.")
    _sinalizar(df, sem_valor, "valor impossível")

    tarifa_do_mes = df.groupby("mes_referencia")["tarifa_kwh"].transform(lambda s: s.mode().iloc[0])
    tarifa_diferente = df.index[df["tarifa_kwh"].notna() & (df["tarifa_kwh"] != tarifa_do_mes)]
    _registrar_linhas(df, tarifa_diferente, log, aba, "tarifa_kwh", "Tarifa diferente da tarifa do mês",
                      cfg.REVISAO, "A tarifa da Enel é única por mês na base; diferença sugere digitação.")
    _sinalizar(df, tarifa_diferente, "tarifa fora do padrão do mês")

    return _remover_faturas_duplicadas(df, log, aba)


def _remover_faturas_duplicadas(df, log, aba):
    """Mesma UC e mesmo mês. Cópia idêntica é descartada; versões diferentes vão para revisão."""
    chave = ["uc", "mes_referencia"]
    valores = chave + ["consumo_kwh", "energia_compensada_kwh", "tarifa_kwh"]
    copias = df.index[df.duplicated(valores, keep="first")]
    _registrar_linhas(df, copias, log, aba, "uc", "Fatura duplicada (mesma UC, mês e valores)",
                      cfg.DESCARTADO, "Linha repetida na exportação. Mantê-la faria a fatura contar duas "
                      "vezes nos indicadores.")
    df = df.drop(index=copias)

    conflito = df.index[df.duplicated(chave, keep=False)]
    _registrar_linhas(df, conflito, log, aba, "uc", "Duas faturas diferentes para a mesma UC e mês",
                      cfg.REVISAO, "Não dá para saber qual é a verdadeira.")
    _sinalizar(df, conflito, "fatura duplicada com valores diferentes")
    return df


def tratar_cobrancas(df_bruto, log):
    aba = cfg.ABA_COBRANCAS
    df = _preparar(df_bruto, "id_cobranca")

    df = _padronizar_coluna(df, "id_cliente", lambda v: normalizar_texto(v).upper(), r"C\d+", log, aba,
                            "id_cliente fora do padrão", "Padronizado em maiúsculas sem espaços.")
    df = _padronizar_coluna(df, "mes_referencia", normalizar_mes, PADRAO_MES, log, aba,
                            "Mês de referência fora do padrão", "Convertido para AAAA-MM.", formatar=_fmt_mes)
    df = _padronizar_coluna(df, "valor_cobrado", normalizar_numero, PADRAO_NUMERO, log, aba,
                            "Valor em texto no formato brasileiro (R$ 1.234,56)",
                            "Convertido para número. Vírgula = decimal, ponto = milhar.")
    for coluna in ("data_vencimento", "data_pagamento"):
        df = _padronizar_coluna(df, coluna, normalizar_data, PADRAO_DATA, log, aba,
                                "Data em formato DD/MM/AAAA misturado com AAAA-MM-DD",
                                "Convertida para AAAA-MM-DD (premissa: padrão brasileiro).", formatar=_fmt_data)
    df = _padronizar_coluna(df, "status_pagamento", lambda v: normalizar_texto(v).lower(), None, log, aba,
                            "Status com caixa despadronizada (PAGO, Pago, Em Aberto)",
                            "Padronizado em minúsculas.")

    # --- regras de negócio ---------------------------------------------------
    negativo = df.index[df["valor_cobrado"] < 0]
    _registrar_linhas(df, negativo, log, aba, "valor_cobrado", "Valor do boleto negativo", cfg.CORRIGIDO,
                      "Boleto não tem valor negativo; tratado como sinal invertido (valor absoluto). "
                      "A conciliação confirma se o valor absoluto bate com o esperado.",
                      tratar_valor=abs)
    df.loc[negativo, "valor_cobrado"] = df.loc[negativo, "valor_cobrado"].abs()

    zerado = df.index[df["valor_cobrado"] == 0]
    _registrar_linhas(df, zerado, log, aba, "valor_cobrado", "Boleto com valor zero", cfg.REVISAO,
                      "Boleto emitido sem valor.")
    _sinalizar(df, zerado, "valor zero")

    status_invalido = df.index[~df["status_pagamento"].isin(cfg.STATUS_PAGAMENTO_VALIDOS)]
    _registrar_linhas(df, status_invalido, log, aba, "status_pagamento", "Status de pagamento desconhecido",
                      cfg.REVISAO, "Só existem 'pago' e 'em aberto'.")
    _sinalizar(df, status_invalido, "status inválido")

    pago = df["status_pagamento"] == "pago"
    pago_sem_data = df.index[pago & df["data_pagamento"].isna()]
    _registrar_linhas(df, pago_sem_data, log, aba, "data_pagamento", "Status 'pago' sem data de pagamento",
                      cfg.REVISAO, "Mantido como pago (o status vem do sistema de cobrança), mas o "
                      "financeiro precisa confirmar a baixa no banco.")
    _sinalizar(df, pago_sem_data, "pago sem data")

    aberto_com_data = df.index[~pago & df["data_pagamento"].notna()]
    _registrar_linhas(df, aberto_com_data, log, aba, "data_pagamento", "Status 'em aberto' com data de pagamento",
                      cfg.REVISAO, "Status e data se contradizem.")
    _sinalizar(df, aberto_com_data, "em aberto com data de pagamento")

    pagamento_antes = df.index[df["data_pagamento"] < df["mes_referencia"]]
    _registrar_linhas(df, pagamento_antes, log, aba, "data_pagamento",
                      "Pagamento antes do mês de referência", cfg.REVISAO, "Data impossível.")
    _sinalizar(df, pagamento_antes, "pagamento antes do mês de referência")

    id_repetido = df.index[df.duplicated("id_cobranca", keep=False)]
    _registrar_linhas(df, id_repetido, log, aba, "id_cobranca", "id_cobranca repetido", cfg.REVISAO,
                      "O identificador do boleto deveria ser único.")
    _sinalizar(df, id_repetido, "id_cobranca repetido")

    return _marcar_cobrancas_duplicadas(df, log, aba)


def _marcar_cobrancas_duplicadas(df, log, aba):
    """Mais de um boleto para o mesmo cliente e mês.

    Não apagamos: boleto é documento financeiro e o cliente pode ter recebido os dois.
    Mantemos como principal o boleto pago (ou o de menor número) e marcamos os demais
    com `cobranca_duplicada = True`. Na Etapa 2 eles viram 'Cobrança indevida'.
    """
    df["cobranca_duplicada"] = False
    ordem = df.assign(_pago=df["status_pagamento"] == "pago").sort_values(
        ["id_cliente", "mes_referencia", "_pago", "id_cobranca"], ascending=[True, True, False, True])
    extras = ordem.index[ordem.duplicated(["id_cliente", "mes_referencia"], keep="first")]
    df.loc[extras, "cobranca_duplicada"] = True
    for idx in extras:
        principal = ordem[(ordem["id_cliente"] == df.at[idx, "id_cliente"])
                          & (ordem["mes_referencia"] == df.at[idx, "mes_referencia"])].iloc[0]
        log.registrar(aba, df.at[idx, "registro"], "id_cobranca", "Cobrança duplicada (mesmo cliente e mês)",
                      df.at[idx, "id_cobranca"], f"principal: {principal['id_cobranca']}", cfg.REVISAO,
                      "Boleto é documento financeiro: não apagamos. Mantido o boleto pago (ou o mais "
                      "antigo) como principal; este será classificado como 'Cobrança indevida' e o "
                      "financeiro decide se cancela ou estorna.")
    return df


# =============================================================================
# 3. Relacionamento entre as abas
# =============================================================================
def verificar_relacionamentos(clientes, faturas, cobrancas, log):
    """Liga faturas ao cliente pela UC e confere se tudo tem correspondência."""
    mapa_uc = clientes.dropna(subset=["uc"]).drop_duplicates("uc").set_index("uc")["id_cliente"]
    faturas.insert(faturas.columns.get_loc("uc") + 1, "id_cliente", faturas["uc"].map(mapa_uc))

    orfas = faturas.index[faturas["id_cliente"].isna()]
    _registrar_linhas(faturas, orfas, log, cfg.ABA_FATURAS, "uc", "Fatura de UC que não existe no cadastro",
                      cfg.REVISAO, "Sem cliente não há desconto nem a quem cobrar. A fatura é mantida e "
                      "aparece na conciliação como 'Fatura sem cliente' para o comercial investigar "
                      "(cliente não cadastrado ou UC digitada errada).")
    _sinalizar(faturas, orfas, "UC fora do cadastro")

    sem_cadastro = cobrancas.index[~cobrancas["id_cliente"].isin(clientes["id_cliente"])]
    _registrar_linhas(cobrancas, sem_cadastro, log, cfg.ABA_COBRANCAS, "id_cliente",
                      "Cobrança de cliente que não existe no cadastro", cfg.REVISAO,
                      "Não há como validar o valor cobrado.")
    _sinalizar(cobrancas, sem_cadastro, "cliente fora do cadastro")

    adesao = faturas["id_cliente"].map(clientes.set_index("id_cliente")["data_adesao"])
    antes_adesao = faturas.index[faturas["mes_referencia"] < adesao.dt.to_period("M").dt.to_timestamp()]
    _registrar_linhas(faturas, antes_adesao, log, cfg.ABA_FATURAS, "mes_referencia",
                      "Fatura de mês anterior à adesão do cliente", cfg.REVISAO,
                      "Antes da adesão o cliente não recebia créditos da Goener.")
    _sinalizar(faturas, antes_adesao, "fatura antes da adesão")
    return faturas, cobrancas


# =============================================================================
# Orquestração
# =============================================================================
def carregar_base(caminho=cfg.ARQUIVO_BASE):
    """Lê as três abas como texto para não perder zeros à esquerda nem formatos originais."""
    abas = [cfg.ABA_CLIENTES, cfg.ABA_FATURAS, cfg.ABA_COBRANCAS]
    return {aba: pd.read_excel(caminho, sheet_name=aba, dtype=str) for aba in abas}


def executar_tratamento(caminho=cfg.ARQUIVO_BASE):
    """Roda a Etapa 1 completa. Devolve as três bases tratadas e o log."""
    log = LogInconsistencias()
    brutas = carregar_base(caminho)
    clientes = tratar_clientes(brutas[cfg.ABA_CLIENTES], log)
    faturas = tratar_faturas(brutas[cfg.ABA_FATURAS], log)
    cobrancas = tratar_cobrancas(brutas[cfg.ABA_COBRANCAS], log)
    faturas, cobrancas = verificar_relacionamentos(clientes, faturas, cobrancas, log)
    return {"brutas": brutas, "clientes": clientes, "faturas": faturas,
            "cobrancas": cobrancas, "log": log}
