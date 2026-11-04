"""Gravação das bases tratadas: Excel único (entregável) e CSVs para o Power BI."""
import pandas as pd

from src import config as cfg

COLUNAS_INTERNAS = ["registro"]  # usadas só para montar o log


def _limpar_para_saida(df):
    return df.drop(columns=[c for c in COLUNAS_INTERNAS if c in df.columns])


def salvar_excel(abas, caminho):
    """Salva um dicionário {nome_aba: DataFrame} em um único .xlsx com colunas ajustadas."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(caminho, engine="openpyxl", datetime_format="YYYY-MM-DD",
                        date_format="YYYY-MM-DD") as escritor:
        for nome, df in abas.items():
            _limpar_para_saida(df).to_excel(escritor, sheet_name=nome[:31], index=False)
            planilha = escritor.sheets[nome[:31]]
            planilha.freeze_panes = "A2"
            for coluna in planilha.columns:
                largura = max(len(str(c.value or "")) for c in coluna[:200])
                planilha.column_dimensions[coluna[0].column_letter].width = min(largura + 2, 60)
    return caminho


MESES_PT_NOME = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def criar_calendario(datas):
    """Dimensão de meses (dim_calendario) cobrindo o período das bases, para filtros no Power BI."""
    meses = pd.date_range(datas.min(), datas.max(), freq="MS")
    return pd.DataFrame({
        "mes_referencia": meses,
        "ano": meses.year,
        "mes": meses.month,
        "mes_nome": [MESES_PT_NOME[m - 1] for m in meses.month],
        "mes_ano": [f"{MESES_PT_NOME[m.month - 1]}/{m:%y}" for m in meses],
        "trimestre": "T" + meses.quarter.astype(str),
    })


def salvar_csv_powerbi(tabelas, pasta=cfg.PASTA_POWERBI):
    """CSV em UTF-8 com BOM (acentos corretos no Power BI/Excel), ponto decimal e datas ISO."""
    pasta.mkdir(parents=True, exist_ok=True)
    caminhos = []
    for nome, df in tabelas.items():
        caminho = pasta / f"{nome}.csv"
        _limpar_para_saida(df).to_csv(caminho, index=False, encoding="utf-8-sig",
                                      date_format="%Y-%m-%d")
        caminhos.append(caminho)
    return caminhos
