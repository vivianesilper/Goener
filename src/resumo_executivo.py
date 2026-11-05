"""Resumo executivo (1 página) para gestor não técnico, em PDF e HTML.

Todos os números vêm da análise: nada é digitado à mão. Se a base mudar, o resumo muda junto.
"""
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src import config as cfg
from src.graficos import reais

MESES_EXTENSO = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
                 "setembro", "outubro", "novembro", "dezembro"]


def _mil(valor):
    """R$ 6.058,61 -> 'R$ 6,1 mil' (leitura rápida para a gestão)."""
    return f"R$ {valor / 1000:,.1f} mil".replace(".", ",")


def _pct(valor):
    return f"{valor:.1%}".replace(".", ",")


# =============================================================================
# Conteúdo
# =============================================================================
def montar_conteudo(resumo, conciliacao, mensal, log, violacoes_original):
    """Transforma os números da análise em frases para quem não é técnico."""
    errados = conciliacao[conciliacao["classificacao"] == cfg.COBRADO_A_MAIOR]
    indevidos = conciliacao[conciliacao["classificacao"] == cfg.COBRANCA_INDEVIDA]
    faltantes = conciliacao[conciliacao["classificacao"] == cfg.FATURA_SEM_COBRANCA]
    impacto_total = resumo["cobrado_a_maior"] + resumo["receita_perdida"] + resumo["cobranca_indevida"]
    inicio, fim = conciliacao["mes_referencia"].min(), conciliacao["mes_referencia"].max()
    duplicados = indevidos["motivo"].str.startswith("Boleto duplicado").sum()
    pendentes = (log.como_dataframe()["acao"] == cfg.REVISAO).sum()
    causas = errados.groupby("causa_provavel").agg(casos=("id_cliente", "size"), valor=("diferenca", "sum"))

    def causa(trecho):
        linha = causas[causas.index.str.contains(trecho)]
        return (int(linha["casos"].sum()), linha["valor"].sum())

    sem_desconto, sobre_consumo, virgula = causa("Desconto"), causa("consumo total"), causa("Vírgula")

    return {
        "titulo": "Resumo executivo · Conciliação Enel × cobranças Goener",
        "periodo": f"{MESES_EXTENSO[inicio.month - 1]} a {MESES_EXTENSO[fim.month - 1]} de {fim.year}",
        "frase": (f"De <b>{_mil(resumo['valor_faturado'])}</b> faturados no período, <b>{_mil(impacto_total)} "
                  f"({_pct(impacto_total / resumo['valor_faturado'])})</b> foram afetados por erros de cobrança. "
                  "Todos os erros de valor foram <b>contra o cliente</b>, e as causas são falhas de processo "
                  "que podem ser corrigidas."),
        "indicadores": [
            ("Cobrado a mais", _mil(resumo["cobrado_a_maior"]),
             f"{len(errados)} boletos de {errados['id_cliente'].nunique()} clientes"),
            ("Deixou de ser faturado", _mil(resumo["receita_perdida"]), f"{len(faltantes)} faturas sem boleto"),
            ("Cobrança indevida", _mil(resumo["cobranca_indevida"]),
             f"{len(indevidos)} boletos, {'nenhum' if not resumo['cobranca_indevida_ja_paga'] else 'alguns'} pago"),
            ("Inadimplência", _pct(resumo["inadimplencia"]), f"{_mil(resumo['vencido_nao_pago'])} vencidos"),
        ],
        "economia": (f"Com o desconto Goener, os clientes economizaram <b>{_mil(resumo['economia_real'])}</b> "
                     f"(economia recebida). O contrato prometia {_mil(resumo['economia_contratada'])}: "
                     f"a diferença foi cobrada a mais e precisa ser devolvida."),
        "causas": [
            f"<b>Desconto não aplicado</b>: {sem_desconto[0]} boletos cobraram o valor cheio da energia ({_mil(sem_desconto[1])}).",
            f"<b>Cálculo sobre o consumo total</b> em vez da energia solar compensada: {sobre_consumo[0]} boletos ({_mil(sobre_consumo[1])}).",
            f"<b>Valor digitado errado</b>: {virgula[0]} boletos com a vírgula deslocada, cobrando 10 vezes o valor ({_mil(virgula[1])}).",
            f"<b>Cancelamento não bloqueia a cobrança</b>: {len(indevidos) - duplicados} clientes cancelados receberam boleto "
            f"e {duplicados} boletos saíram em duplicidade.",
            f"<b>Dados sem padrão</b>: o arquivo tinha {len(violacoes_original):,} problemas de formato. ".replace(",", ".")
            + f"Todos foram tratados, e {pendentes} registros precisam de confirmação de uma pessoa.",
        ],
        "agora": [
            f"<b>Cancelar os {len(indevidos)} boletos indevidos</b> antes do pagamento ({_mil(resumo['cobranca_indevida'])}).",
            f"<b>Emitir os {len(faltantes)} boletos que faltaram</b> ({_mil(resumo['receita_perdida'])}), conferindo o prazo contratual.",
            f"<b>Devolver ou abater {_mil(resumo['cobrado_a_maior'])}</b> dos {errados['id_cliente'].nunique()} clientes "
            "cobrados a mais, avisando antes que eles percebam.",
        ],
        "processo": [
            "<b>Ligar a trava automática</b> antes de cada emissão (já construída e testada): nenhum boleto "
            "sai se não bater com a fatura da Enel.",
            "<b>Ajustar o sistema de cobrança</b>: valor sempre calculado (nunca digitado), desconto puxado do "
            "contrato, cálculo sobre a energia compensada e cancelamento bloqueando a emissão.",
            f"<b>Acompanhar a inadimplência</b>, que subiu de {_pct(mensal['inadimplencia'].iloc[0])} para "
            f"{_pct(mensal['inadimplencia'].iloc[-1])} ao longo do período.",
        ],
    }


# =============================================================================
# PDF
# =============================================================================
def _estilos():
    base = dict(fontName="Helvetica", fontSize=9, leading=12, textColor=colors.HexColor(cfg.COR_TEXTO))
    return {
        "titulo": ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=colors.white),
        "subtitulo": ParagraphStyle("sub", fontName="Helvetica", fontSize=9.5, leading=12,
                                    textColor=colors.HexColor("#d9eeee")),
        "secao": ParagraphStyle("secao", fontName="Helvetica-Bold", fontSize=10.5, leading=14, spaceBefore=7,
                                spaceAfter=3, textColor=colors.HexColor(cfg.COR_MARCA)),
        "texto": ParagraphStyle("texto", **base),
        "frase": ParagraphStyle("frase", **{**base, "fontSize": 10.5, "leading": 14.5}),
        "item": ParagraphStyle("item", **{**base, "leftIndent": 10, "bulletIndent": 0, "spaceAfter": 2}),
        "kpi_titulo": ParagraphStyle("kt", fontName="Helvetica", fontSize=7.5, leading=9, alignment=TA_CENTER,
                                     textColor=colors.HexColor(cfg.COR_TEXTO_SECUNDARIO)),
        "kpi_valor": ParagraphStyle("kv", fontName="Helvetica-Bold", fontSize=15, leading=19, alignment=TA_CENTER,
                                    textColor=colors.HexColor(cfg.COR_TEXTO)),
        "kpi_detalhe": ParagraphStyle("kd", fontName="Helvetica", fontSize=7.5, leading=9, alignment=TA_CENTER,
                                      textColor=colors.HexColor(cfg.COR_TEXTO_SECUNDARIO)),
        "rodape": ParagraphStyle("rodape", fontName="Helvetica", fontSize=7, leading=9,
                                 textColor=colors.HexColor(cfg.COR_TEXTO_SECUNDARIO)),
    }


def _lista(itens, estilo, marcador="•"):
    return [Paragraph(item, estilo, bulletText=marcador) for item in itens]


def gerar_pdf(conteudo, caminho, grafico=None):
    """Monta o PDF de uma página. `grafico` é o PNG do impacto mensal (opcional)."""
    e = _estilos()
    largura = A4[0] - 3.2 * cm
    doc = SimpleDocTemplate(str(caminho), pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm,
                            topMargin=1.2 * cm, bottomMargin=1.0 * cm, title=conteudo["titulo"],
                            author="Viviane Pereira")

    cabecalho = Table([[Paragraph(conteudo["titulo"], e["titulo"])],
                       [Paragraph(f"Período analisado: {conteudo['periodo']} · Data de corte: "
                                  f"{cfg.DATA_CORTE:%d/%m/%Y}", e["subtitulo"])]], colWidths=[largura])
    cabecalho.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(cfg.COR_MARCA)),
        ("LINEBELOW", (0, -1), (-1, -1), 4, colors.HexColor(cfg.COR_DESTAQUE)),
        ("LEFTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 10)]))

    cartoes = Table([[[Paragraph(t.upper(), e["kpi_titulo"]), Paragraph(v, e["kpi_valor"]),
                       Paragraph(d, e["kpi_detalhe"])] for t, v, d in conteudo["indicadores"]]],
                    colWidths=[largura / 4] * 4)
    cartoes.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(cfg.COR_GRADE)),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.HexColor(cfg.COR_GRADE)),
        ("LINEABOVE", (0, 0), (-1, 0), 3, colors.HexColor(cfg.COR_MARCA)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))

    imagem = []
    if grafico is not None:
        largura_grafico = largura * 0.82
        imagem = [Spacer(1, 6), Image(str(grafico), width=largura_grafico, height=largura_grafico * 0.47)]

    historia = [
        cabecalho, Spacer(1, 10),
        Paragraph(conteudo["frase"], e["frase"]), Spacer(1, 8),
        cartoes, Spacer(1, 6),
        Paragraph(conteudo["economia"], e["texto"]),
        *imagem,
        Paragraph("Por que acontece", e["secao"]),
        *_lista(conteudo["causas"], e["item"]),
        Paragraph("O que recomendo fazer agora", e["secao"]),
        *_lista(conteudo["agora"], e["item"], "1."),
        Paragraph("Para não voltar a acontecer", e["secao"]),
        *_lista(conteudo["processo"], e["item"], "2."),
        Spacer(1, 8),
        Paragraph("Detalhes, caso a caso, no notebook <i>case_goener.ipynb</i>, na planilha "
                  "<i>base_tratada.xlsx</i> e no documento <i>ERROS_E_LOGS.md</i>. Dados fictícios do case técnico.",
                  e["rodape"]),
    ]
    _numerar_listas(historia)
    doc.build(historia)
    return caminho


def _numerar_listas(historia):
    """Troca os marcadores '1.'/'2.' por numeração sequencial em cada lista de recomendações."""
    contador = 0
    for bloco in historia:
        if isinstance(bloco, Paragraph) and bloco.bulletText in ("1.", "2."):
            contador += 1
            bloco.bulletText = f"{contador}."


# =============================================================================
# HTML (seção final do notebook)
# =============================================================================
def gerar_html(conteudo):
    cartoes = "".join(
        f"""<div style="flex:1 1 150px;border:1px solid {cfg.COR_GRADE};border-top:4px solid {cfg.COR_MARCA};
             border-radius:8px;padding:10px;text-align:center;background:#fff">
             <div style="font-size:11px;color:{cfg.COR_TEXTO_SECUNDARIO};text-transform:uppercase">{t}</div>
             <div style="font-size:22px;font-weight:700;color:{cfg.COR_TEXTO}">{v}</div>
             <div style="font-size:11px;color:{cfg.COR_TEXTO_SECUNDARIO}">{d}</div></div>"""
        for t, v, d in conteudo["indicadores"])

    def lista(itens, tag="ul"):
        return f"<{tag}>" + "".join(f"<li style='margin-bottom:4px'>{i}</li>" for i in itens) + f"</{tag}>"

    return f"""
    <div style="max-width:900px;font-family:inherit;color:{cfg.COR_TEXTO}">
      <div style="background:{cfg.COR_MARCA};color:#fff;padding:16px 20px;border-radius:8px 8px 0 0;
                  border-bottom:5px solid {cfg.COR_DESTAQUE}">
        <div style="font-size:20px;font-weight:700">{conteudo['titulo']}</div>
        <div style="font-size:13px;opacity:.85">Período analisado: {conteudo['periodo']}</div></div>
      <p style="font-size:15px;line-height:1.5;margin:14px 0">{conteudo['frase']}</p>
      <div style="display:flex;flex-wrap:wrap;gap:10px">{cartoes}</div>
      <p style="margin-top:12px">{conteudo['economia']}</p>
      <h4 style="color:{cfg.COR_MARCA};margin-bottom:4px">Por que acontece</h4>{lista(conteudo['causas'])}
      <h4 style="color:{cfg.COR_MARCA};margin-bottom:4px">O que recomendo fazer agora</h4>{lista(conteudo['agora'], 'ol')}
      <h4 style="color:{cfg.COR_MARCA};margin-bottom:4px">Para não voltar a acontecer</h4>{lista(conteudo['processo'], 'ol')}
    </div>"""
