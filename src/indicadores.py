"""Etapa 3 — Indicadores para a gestão, calculados a partir da conciliação."""
import pandas as pd

from src import config as cfg

COLUNAS_IMPACTO = ["valor_a_maior", "valor_a_menor", "receita_perdida", "valor_indevido"]


def boletos_legitimos(conciliacao):
    """Boletos que deveriam existir: exclui duplicados e cobranças de cliente cancelado."""
    tem_boleto = conciliacao["id_cobranca"].notna()
    return conciliacao[tem_boleto & (conciliacao["classificacao"] != cfg.COBRANCA_INDEVIDA)]


def taxa_inadimplencia(boletos):
    """Valor vencido e não pago ÷ total vencido (na data de corte)."""
    total_vencido = boletos.loc[boletos["vencida"], "valor_cobrado"].sum()
    nao_pago = boletos.loc[boletos["vencida_nao_paga"], "valor_cobrado"].sum()
    return nao_pago / total_vencido if total_vencido else 0.0


def resumo_financeiro(conciliacao):
    """Responde às perguntas da gestão em um único dicionário de números."""
    legitimos = boletos_legitimos(conciliacao)
    indevidos = conciliacao[conciliacao["classificacao"] == cfg.COBRANCA_INDEVIDA]
    vencidos = legitimos[legitimos["vencida"]]
    return {
        "valor_faturado": legitimos["valor_cobrado"].sum(),
        "cobrado_a_maior": conciliacao["valor_a_maior"].sum(),
        "cobrado_a_menor": conciliacao["valor_a_menor"].sum(),
        "receita_perdida": conciliacao["receita_perdida"].sum(),
        "cobranca_indevida": indevidos["valor_cobrado"].sum(),
        "cobranca_indevida_ja_paga": indevidos.loc[indevidos["status_pagamento"] == "pago", "valor_cobrado"].sum(),
        "economia_real": conciliacao["economia_real"].sum(),
        "economia_contratada": conciliacao["economia_contratada"].sum(),
        "total_vencido": vencidos["valor_cobrado"].sum(),
        "vencido_nao_pago": vencidos.loc[vencidos["vencida_nao_paga"], "valor_cobrado"].sum(),
        "inadimplencia": taxa_inadimplencia(legitimos),
        "inadimplencia_com_indevidas": taxa_inadimplencia(conciliacao[conciliacao["id_cobranca"].notna()]),
    }


def maiores_divergencias(conciliacao, quantidade=cfg.QTD_MAIORES_DIVERGENCIAS):
    """Casos com maior impacto em R$, de qualquer tipo, com a causa provável."""
    casos = conciliacao.assign(impacto=conciliacao[COLUNAS_IMPACTO].sum(axis=1))
    casos = casos[casos["impacto"] > 0].nlargest(quantidade, "impacto")
    casos["causa"] = casos["causa_provavel"].fillna(casos["motivo"])
    return casos[["classificacao", "id_cliente", "nome", "mes_referencia", "valor_esperado",
                  "valor_cobrado", "impacto", "causa"]].reset_index(drop=True)


def evolucao_mensal(conciliacao):
    """Os mesmos indicadores, mês de referência a mês."""
    legitimos = boletos_legitimos(conciliacao)
    impacto = conciliacao.groupby("mes_referencia")[
        COLUNAS_IMPACTO + ["economia_real", "economia_contratada"]].sum()
    impacto["casos_com_erro"] = (conciliacao[~conciliacao["classificacao"].isin(
        [cfg.OK, cfg.NAO_COBRAVEL, cfg.INCONCLUSIVO])].groupby("mes_referencia").size())
    faturado = legitimos.groupby("mes_referencia").agg(
        valor_faturado=("valor_cobrado", "sum"),
        total_vencido=("valor_cobrado", lambda s: s[legitimos.loc[s.index, "vencida"]].sum()),
        vencido_nao_pago=("valor_cobrado", lambda s: s[legitimos.loc[s.index, "vencida_nao_paga"]].sum()))
    mensal = faturado.join(impacto).fillna({"casos_com_erro": 0})
    mensal["inadimplencia"] = (mensal["vencido_nao_pago"] / mensal["total_vencido"]).fillna(0)
    mensal["casos_com_erro"] = mensal["casos_com_erro"].astype(int)
    return mensal
