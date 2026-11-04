"""Diferencial: SQL. Carrega as tabelas tratadas num banco SQLite em memória e roda as
consultas de `sql/consultas.sql`, que conferem de forma independente os resultados do Python.
"""
import re
import sqlite3

import pandas as pd

from src import config as cfg

ARQUIVO_CONSULTAS = cfg.RAIZ / "sql" / "consultas.sql"


def _para_sql(df):
    """Datas viram texto ISO (comparáveis em SQL) e categorias viram texto."""
    saida = df.copy()
    for coluna in saida.columns:
        if pd.api.types.is_datetime64_any_dtype(saida[coluna]):
            saida[coluna] = saida[coluna].dt.strftime("%Y-%m-%d")
        elif isinstance(saida[coluna].dtype, pd.CategoricalDtype):
            saida[coluna] = saida[coluna].astype(str)
    return saida


def criar_banco(tabelas):
    """Cria um banco SQLite em memória com {nome_tabela: DataFrame}."""
    conexao = sqlite3.connect(":memory:")
    for nome, df in tabelas.items():
        _para_sql(df).to_sql(nome, conexao, index=False)
    return conexao


def carregar_consultas(caminho=ARQUIVO_CONSULTAS):
    """Lê o arquivo .sql e separa cada consulta pelo marcador '-- name: <nome>'."""
    texto = caminho.read_text(encoding="utf-8")
    partes = re.split(r"^-- name:\s*(\w+)\s*$", texto, flags=re.MULTILINE)
    return {nome: sql.strip() for nome, sql in zip(partes[1::2], partes[2::2])}


def executar(conexao, consulta, **parametros):
    """Roda uma consulta pelo nome, passando os parâmetros de config (ex.: tolerância)."""
    padrao = {"tolerancia": cfg.TOLERANCIA_ARREDONDAMENTO, "data_corte": cfg.DATA_CORTE.strftime("%Y-%m-%d")}
    return pd.read_sql_query(carregar_consultas()[consulta], conexao, params={**padrao, **parametros})
