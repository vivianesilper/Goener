"""Gera o ERROS_E_LOGS.md a partir do log, sempre em sincronia com o código."""
from datetime import datetime

import pandas as pd

from src import config as cfg

ICONE_ACAO = {cfg.CORRIGIDO: "🟢 Corrigido", cfg.DESCARTADO: "🔴 Descartado",
              cfg.REVISAO: "🟡 Revisão humana"}
EXEMPLOS_POR_PROBLEMA = 3

PREMISSAS = [
    "Datas com barra (`04/10/2025`) seguem o padrão brasileiro **DD/MM/AAAA**. Nenhuma data da base "
    "tem valor maior que 12 na posição do mês, o que confirma a leitura.",
    "Desconto maior que 1 é percentual (`15` = 15%); menor ou igual a 1 já é fração (`0.15`).",
    "Valor com vírgula é formato brasileiro (`R$ 9.666,09`: ponto = milhar, vírgula = decimal).",
    "CPF/CNPJ são fictícios (o enunciado avisa) e quase nenhum tem dígito verificador válido, por isso "
    "validamos só a quantidade de dígitos (11 ou 14).",
    "Consumo e boleto negativos são **sinal invertido** na exportação: usamos o valor absoluto e a "
    "conciliação confirma se o número bate com o esperado.",
    "Nenhum valor ausente foi inventado ou estimado: registros sem dado essencial ficam na base, "
    "marcados para revisão, e a conciliação classifica o caso como **Inconclusivo**.",
    "Boletos duplicados **não são apagados** (são documentos financeiros): ficam marcados e viram "
    "**Cobrança indevida** na conciliação.",
    "Na data de corte (15/10/2026), boleto **pago no próprio dia 15/10 conta como pago** (a data de "
    "corte entra no período). A inadimplência usa o `status_pagamento` da base; isso equivale à "
    "situação na data de corte porque nenhum pagamento é posterior a 15/10. Só um boleto foi pago "
    "exatamente no dia 15/10 (GB50385, C1066, ref. ago/2026, R$ 562,51, vencido em 10/09).",
]


def _tabela_markdown(df):
    """DataFrame -> tabela Markdown (sem depender do pacote tabulate)."""
    texto = df.astype(str).apply(lambda col: col.str.replace("|", "\\|").str.replace("\n", " "))
    linhas = ["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
    linhas += ["| " + " | ".join(linha) + " |" for linha in texto.itertuples(index=False)]
    return "\n".join(linhas)


def _exemplos(grupo):
    amostra = grupo.head(EXEMPLOS_POR_PROBLEMA)
    return "<br>".join(f"`{o}` → `{t}`" for o, t in zip(amostra["valor_original"], amostra["valor_tratado"]))


def gerar_markdown(log, brutas, tratadas, conciliacao=None, caminho=cfg.ARQUIVO_MARKDOWN_ERROS):
    df_log = log.como_dataframe()
    partes = [
        "# Erros encontrados e log de inconsistências",
        f"> Gerado automaticamente por `src/relatorio_erros.py` em {datetime.now():%d/%m/%Y %H:%M}. "
        "Não edite à mão: rode o notebook de novo para atualizar.",
        "## 1. Visão geral",
        _visao_geral(df_log, brutas, tratadas),
        "### O que cada ação significa",
        "| Ação | Quando usamos |\n|---|---|\n"
        f"| {ICONE_ACAO[cfg.CORRIGIDO]} | O valor certo pode ser recuperado sem dúvida (formato, zeros, sinal). |\n"
        f"| {ICONE_ACAO[cfg.DESCARTADO]} | Cópia exata de outro registro; mantê-la contaria o mesmo fato duas vezes. |\n"
        f"| {ICONE_ACAO[cfg.REVISAO]} | Falta informação ou há contradição; uma pessoa precisa decidir. O registro fica na base. |",
        "## 2. Premissas adotadas",
        "\n".join(f"{i}. {p}" for i, p in enumerate(PREMISSAS, 1)),
        "## 3. Problemas por aba",
    ]
    for aba in (cfg.ABA_CLIENTES, cfg.ABA_FATURAS, cfg.ABA_COBRANCAS):
        partes += [f"### Aba `{aba}`", _problemas_da_aba(df_log[df_log["aba"] == aba])]

    for titulo, acao in (("## 4. Registros que precisam de revisão humana", cfg.REVISAO),
                         ("## 5. Registros descartados", cfg.DESCARTADO)):
        detalhe = df_log[df_log["acao"] == acao][["aba", "registro", "problema", "valor_original", "valor_tratado"]]
        partes += [titulo, f"Total: **{len(detalhe)}**", _tabela_markdown(detalhe)]

    if conciliacao is not None:
        partes += _secao_conciliacao(conciliacao)

    partes += [f"## {7 if conciliacao is not None else 6}. Log completo",
               f"As {len(df_log)} linhas do log (uma por valor tratado) estão em:",
               "- `output/base_tratada.xlsx`, aba `log_inconsistencias`\n"
               "- `output/powerbi/log_inconsistencias.csv`"]
    caminho.write_text("\n\n".join(partes) + "\n", encoding="utf-8")
    return caminho


def _visao_geral(df_log, brutas, tratadas):
    linhas = []
    for aba, chave in ((cfg.ABA_CLIENTES, "clientes"), (cfg.ABA_FATURAS, "faturas"),
                       (cfg.ABA_COBRANCAS, "cobrancas")):
        log_aba = df_log[df_log["aba"] == aba]
        linhas.append({
            "Aba": f"`{aba}`",
            "Linhas originais": len(brutas[aba]),
            "Linhas tratadas": len(tratadas[chave]),
            "Tipos de problema": log_aba["problema"].nunique(),
            ICONE_ACAO[cfg.CORRIGIDO]: (log_aba["acao"] == cfg.CORRIGIDO).sum(),
            ICONE_ACAO[cfg.DESCARTADO]: (log_aba["acao"] == cfg.DESCARTADO).sum(),
            ICONE_ACAO[cfg.REVISAO]: (log_aba["acao"] == cfg.REVISAO).sum(),
        })
    resumo = pd.DataFrame(linhas)
    total = resumo.drop(columns="Aba").sum()
    resumo.loc[len(resumo)] = {"Aba": "**Total**", **total.to_dict()}
    return _tabela_markdown(resumo)


def _reais(valor):
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def _secao_conciliacao(conciliacao):
    """Seção 6: erros de cobrança (Etapa 2), com impacto em R$ e causa provável."""
    impacto = {cfg.COBRADO_A_MAIOR: "valor_a_maior", cfg.COBRADO_A_MENOR: "valor_a_menor",
               cfg.FATURA_SEM_COBRANCA: "receita_perdida", cfg.COBRANCA_INDEVIDA: "valor_indevido"}
    resumo = []
    for classe, grupo in conciliacao.groupby("classificacao", observed=False, sort=True):
        resumo.append({"Classificação": classe, "Casos": len(grupo),
                       "Impacto (R$)": _reais(grupo[impacto[classe]].sum()) if classe in impacto else "—"})

    divergentes = conciliacao[conciliacao["classificacao"].isin([cfg.COBRADO_A_MAIOR, cfg.COBRADO_A_MENOR])]
    causas = (divergentes.groupby("causa_provavel")
              .agg(Casos=("id_cliente", "size"), Diferenca=("diferenca", "sum"))
              .sort_values("Diferenca", ascending=False).reset_index())
    causas["Diferenca"] = causas["Diferenca"].map(_reais)
    causas.columns = ["Causa provável", "Casos", "Diferença total"]

    problemas = conciliacao[conciliacao["classificacao"] != cfg.OK].copy()
    problemas["mes_referencia"] = problemas["mes_referencia"].dt.strftime("%Y-%m")
    for coluna in ("valor_esperado", "valor_cobrado", "diferenca"):
        problemas[coluna] = problemas[coluna].map(lambda v: _reais(v) if pd.notna(v) else "—")
    problemas["causa_provavel"] = problemas["causa_provavel"].fillna("—")
    problemas["uc"] = problemas["uc"].fillna("—")
    problemas["id_cliente"] = problemas["id_cliente"].fillna("—")
    problemas = problemas[["classificacao", "id_cliente", "uc", "mes_referencia", "id_cobranca",
                           "valor_esperado", "valor_cobrado", "diferenca", "motivo", "causa_provavel"]]
    problemas["id_cobranca"] = problemas["id_cobranca"].fillna("—")

    return [
        "## 6. Erros de cobrança encontrados na conciliação (Etapa 2)",
        "Cada par (cliente, mês) foi conferido pela regra **energia compensada × tarifa × (1 − desconto)**, "
        f"com tolerância de {_reais(cfg.TOLERANCIA_ARREDONDAMENTO)}.",
        "### Resumo por classificação", _tabela_markdown(pd.DataFrame(resumo)),
        "### Causas prováveis das divergências",
        "A causa é encontrada recalculando o boleto com erros comuns (sem desconto, sobre o consumo total, "
        "vírgula deslocada) e vendo qual deles reproduz exatamente o valor cobrado.",
        _tabela_markdown(causas),
        f"### Todos os casos que não estão OK ({len(problemas)})", _tabela_markdown(problemas),
    ]


def _problemas_da_aba(log_aba):
    linhas = []
    for (problema, acao, justificativa), grupo in log_aba.groupby(
            ["problema", "acao", "justificativa"], sort=False):
        linhas.append({"Problema": problema, "Qtd": len(grupo), "Ação": ICONE_ACAO[acao],
                       "Por quê": justificativa, "Exemplos (original → tratado)": _exemplos(grupo)})
    return _tabela_markdown(pd.DataFrame(linhas))
