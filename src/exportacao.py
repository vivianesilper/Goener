"""Gravação das bases tratadas: Excel único (entregável) e CSVs para o Power BI."""
import pandas as pd

from src import config as cfg

COLUNAS_INTERNAS = ["registro"]  # auxiliar das bases tratadas, usada só para montar o log

# Casas decimais na saída. Os cálculos usam a precisão completa; aqui só se evita gravar
# resíduos de ponto flutuante como 114576.48000000001 ou 0.09947600065912304.
CASAS_POR_COLUNA = {"tarifa_kwh": 4, "desconto_contratado": 4, "inadimplencia": 4}
CASAS_PADRAO = cfg.CASAS_DECIMAIS  # R$ e kWh


def _arredondar(df):
    """Arredonda as colunas decimais: 4 casas para tarifa, desconto e taxas; 2 para o resto."""
    decimais = df.select_dtypes(include="float").columns
    return df.round({c: CASAS_POR_COLUNA.get(c, CASAS_PADRAO) for c in decimais})


def _limpar_para_saida(df):
    """Arredonda os decimais e tira as colunas auxiliares das bases tratadas.

    As bases tratadas têm `linha_origem` para rastreio e `registro` é só auxiliar. O log de
    inconsistências não tem `linha_origem`: nele, `registro` é justamente o que identifica o
    cliente, fatura ou boleto com problema, então é mantido.
    """
    df = _arredondar(df)
    if "linha_origem" not in df.columns:
        return df
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
    """CSV no padrão brasileiro, pronto para o Power BI em português sem configurar localidade.

    UTF-8 com BOM (acentos corretos), separador `;`, vírgula decimal (`341,15`) e datas ISO.
    """
    pasta.mkdir(parents=True, exist_ok=True)
    caminhos = []
    for nome, df in tabelas.items():
        caminho = pasta / f"{nome}.csv"
        _limpar_para_saida(df).to_csv(caminho, index=False, encoding="utf-8-sig", sep=";",
                                      decimal=",", date_format="%Y-%m-%d")
        caminhos.append(caminho)
    return caminhos
