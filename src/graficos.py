"""Visual da Etapa 3: cartões de indicadores (HTML) e gráficos (matplotlib)."""
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from src import config as cfg

MESES_ABREV = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
CLASSE_PARA_IMPACTO = {cfg.COBRADO_A_MAIOR: "Cobrado a maior", cfg.FATURA_SEM_COBRANCA: "Receita perdida",
                       cfg.COBRANCA_INDEVIDA: "Cobrança indevida"}


def reais(valor, casas=2):
    texto = f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def _mes(data):
    return f"{MESES_ABREV[data.month - 1]}/{data:%y}"


def aplicar_estilo():
    """Estilo limpo: grade horizontal fina, sem bordas superiores/direitas, texto em cinza escuro."""
    plt.rcParams.update({
        "figure.dpi": 110, "savefig.dpi": 150, "savefig.bbox": "tight",
        "font.size": 10, "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.titlecolor": cfg.COR_TEXTO, "axes.labelcolor": cfg.COR_TEXTO_SECUNDARIO,
        "axes.edgecolor": cfg.COR_GRADE, "axes.spines.top": False, "axes.spines.right": False,
        "axes.spines.left": False, "axes.grid": True, "axes.grid.axis": "y", "axes.axisbelow": True,
        "grid.color": cfg.COR_GRADE, "grid.linewidth": 0.8,
        "xtick.color": cfg.COR_TEXTO_SECUNDARIO, "ytick.color": cfg.COR_TEXTO_SECUNDARIO,
        "xtick.major.size": 0, "ytick.major.size": 0, "legend.frameon": False,
    })


def _subtitulo(ax, texto):
    ax.text(0, 1.02, texto, transform=ax.transAxes, fontsize=9.5, color=cfg.COR_TEXTO_SECUNDARIO, va="bottom")


def _eixo_reais(ax, eixo="y"):
    formato = mticker.FuncFormatter(lambda v, _: reais(v, 0))
    (ax.yaxis if eixo == "y" else ax.xaxis).set_major_formatter(formato)


# =============================================================================
# Cartões de indicadores
# =============================================================================
def cartoes_indicadores(resumo):
    """Linha de cartões com os números principais (HTML para o notebook)."""
    cartoes = [
        ("Cobrado a mais", reais(resumo["cobrado_a_maior"]), "clientes pagaram acima do contrato"),
        ("Cobrado a menos", reais(resumo["cobrado_a_menor"]), "nenhum caso a favor do cliente"),
        ("Deixou de ser faturado", reais(resumo["receita_perdida"]), "faturas da Enel sem boleto"),
        ("Cobrança indevida", reais(resumo["cobranca_indevida"]),
         f"{reais(resumo['cobranca_indevida_ja_paga'])} já pagos: dá para cancelar"),
        ("Economia gerada", reais(resumo["economia_real"]),
         f"contratada: {reais(resumo['economia_contratada'])}"),
        ("Inadimplência", f"{resumo['inadimplencia']:.1%}".replace(".", ","),
         f"{reais(resumo['vencido_nao_pago'])} vencidos e não pagos"),
    ]
    html = "".join(
        f"""<div style="flex:1 1 200px;background:#fff;border:1px solid {cfg.COR_GRADE};
             border-top:4px solid {cfg.COR_MARCA};border-radius:8px;padding:14px 16px">
             <div style="font-size:12px;color:{cfg.COR_TEXTO_SECUNDARIO};text-transform:uppercase;
                  letter-spacing:.04em">{titulo}</div>
             <div style="font-size:24px;font-weight:700;color:{cfg.COR_TEXTO};margin:4px 0">{valor}</div>
             <div style="font-size:12px;color:{cfg.COR_TEXTO_SECUNDARIO}">{detalhe}</div></div>"""
        for titulo, valor, detalhe in cartoes)
    return f'<div style="display:flex;flex-wrap:wrap;gap:12px;margin:8px 0 16px">{html}</div>'


# =============================================================================
# Gráficos
# =============================================================================
def grafico_maiores_divergencias(top):
    """Barras horizontais das maiores divergências, coloridas pelo tipo de impacto."""
    dados = top.iloc[::-1]
    rotulos = [f"{c} · {n.split()[0]} · {_mes(m)}" for c, n, m in
               zip(dados["id_cliente"], dados["nome"], dados["mes_referencia"])]
    cores = [cfg.CORES_IMPACTO[CLASSE_PARA_IMPACTO[c]] for c in dados["classificacao"]]

    fig, ax = plt.subplots(figsize=(9, 5))
    barras = ax.barh(rotulos, dados["impacto"], color=cores, height=0.62, edgecolor="white", linewidth=2)
    for barra, valor in zip(barras, dados["impacto"]):
        ax.text(barra.get_width() + dados["impacto"].max() * 0.01, barra.get_y() + barra.get_height() / 2,
                reais(valor), va="center", fontsize=9, color=cfg.COR_TEXTO)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    _eixo_reais(ax, "x")
    ax.set_xlim(0, dados["impacto"].max() * 1.18)
    ax.set_title(f"As {len(top)} maiores divergências", pad=24)
    _subtitulo(ax, "Impacto em R$ por caso (cliente · mês)")
    _legenda_impacto(ax, set(dados["classificacao"]), loc="lower right")
    return fig


def grafico_impacto_mensal(mensal):
    """Barras empilhadas: quanto cada tipo de erro custou em cada mês."""
    series = {"Cobrado a maior": "valor_a_maior", "Receita perdida": "receita_perdida",
              "Cobrança indevida": "valor_indevido"}
    meses = [_mes(m) for m in mensal.index]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    base = 0
    for nome, coluna in series.items():
        ax.bar(meses, mensal[coluna], bottom=base, color=cfg.CORES_IMPACTO[nome], label=nome,
               width=0.6, edgecolor="white", linewidth=2)
        base = base + mensal[coluna]
    for x, total in enumerate(base):
        ax.text(x, total + base.max() * 0.02, reais(total, 0), ha="center", fontsize=9, color=cfg.COR_TEXTO)
    _eixo_reais(ax)
    ax.set_ylim(0, base.max() * 1.28)  # espaço para a legenda acima das barras
    ax.set_title("Impacto financeiro dos erros por mês", pad=24)
    _subtitulo(ax, "Soma de cobrado a maior, receita perdida e cobrança indevida (R$)")
    ax.legend(loc="upper left", ncols=3)
    return fig


def grafico_economia_mensal(mensal):
    """Economia que o cliente deveria ter (contratada) × a que teve de fato (real)."""
    meses = [_mes(m) for m in mensal.index]
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(meses, mensal["economia_contratada"], color=cfg.COR_NEUTRA, linewidth=2, marker="o",
            markersize=7, label="Economia contratada (sem erros)")
    ax.plot(meses, mensal["economia_real"], color=cfg.COR_MARCA, linewidth=2, marker="o", markersize=7,
            markeredgecolor="white", markeredgewidth=2, label="Economia real")
    ax.fill_between(meses, mensal["economia_real"], mensal["economia_contratada"], color=cfg.COR_NEUTRA, alpha=0.2)
    pior = (mensal["economia_contratada"] - mensal["economia_real"]).idxmax()
    perda = mensal.loc[pior, "economia_contratada"] - mensal.loc[pior, "economia_real"]
    x = list(mensal.index).index(pior)
    ax.annotate(f"{reais(perda)} de economia\nperdida em {_mes(pior)}", (x, mensal.loc[pior, "economia_real"]),
                xytext=(x + 0.35, mensal["economia_real"].min() - 400), fontsize=9, color=cfg.COR_TEXTO,
                arrowprops={"arrowstyle": "-", "color": cfg.COR_TEXTO_SECUNDARIO, "linewidth": 0.8})
    _eixo_reais(ax)
    ax.set_ylim(mensal["economia_real"].min() * 0.85, mensal["economia_contratada"].max() * 1.08)
    ax.set_title("Economia gerada para os clientes", pad=24)
    _subtitulo(ax, "Valor da energia na tarifa Enel menos o boleto Goener (R$)")
    ax.legend(loc="upper left", ncols=2)
    return fig


def grafico_inadimplencia_mensal(mensal):
    """Percentual do valor vencido que não foi pago, por mês de referência."""
    meses = [_mes(m) for m in mensal.index]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    barras = ax.bar(meses, mensal["inadimplencia"], color=cfg.COR_MARCA, width=0.55)
    for barra, taxa in zip(barras, mensal["inadimplencia"]):
        ax.text(barra.get_x() + barra.get_width() / 2, taxa + 0.004, f"{taxa:.1%}".replace(".", ","),
                ha="center", fontsize=9, color=cfg.COR_TEXTO)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(0.05))
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1, decimals=0))
    ax.set_ylim(0, mensal["inadimplencia"].max() * 1.25)
    ax.set_title("Inadimplência por mês de referência", pad=24)
    _subtitulo(ax, f"Valor vencido e não pago ÷ total vencido, na data de corte {cfg.DATA_CORTE:%d/%m/%Y}")
    return fig


def _legenda_impacto(ax, classes, **kwargs):
    from matplotlib.patches import Patch
    itens = [Patch(color=cfg.CORES_IMPACTO[CLASSE_PARA_IMPACTO[c]], label=CLASSE_PARA_IMPACTO[c])
             for c in CLASSE_PARA_IMPACTO if c in classes]
    ax.legend(handles=itens, **kwargs)


def salvar_figura(fig, nome, pasta=cfg.PASTA_SAIDA / "graficos"):
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{nome}.png"
    fig.savefig(caminho, facecolor="white")
    return caminho
