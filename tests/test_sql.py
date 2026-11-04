"""SQL e Python precisam chegar aos mesmos resultados (conferência independente)."""
import pytest

from src import config as cfg
from src import consultas_sql, indicadores
from src.conciliacao import executar_conciliacao
from src.limpeza import executar_tratamento


@pytest.fixture(scope="module")
def dados():
    r = executar_tratamento()
    conc = executar_conciliacao(r["clientes"], r["faturas"], r["cobrancas"])
    banco = consultas_sql.criar_banco({"clientes": r["clientes"], "faturas": r["faturas"],
                                       "cobrancas": r["cobrancas"], "conciliacao": conc})
    return conc, banco


def ids(conc, classe):
    return set(conc.loc[conc["classificacao"] == classe, "id_cobranca"])


def test_divergencias_de_valor_batem(dados):
    conc, banco = dados
    sql = consultas_sql.executar(banco, "divergencias_de_valor")
    assert set(sql["id_cobranca"]) == ids(conc, cfg.COBRADO_A_MAIOR) | ids(conc, cfg.COBRADO_A_MENOR)


def test_cobrancas_apos_cancelamento_batem(dados):
    conc, banco = dados
    sql = consultas_sql.executar(banco, "cobrancas_apos_cancelamento")
    pandas = conc[conc["motivo"].str.contains("mês começa depois do cancelamento")]
    assert set(sql["id_cobranca"]) == set(pandas["id_cobranca"])


def test_receita_perdida_bate(dados):
    conc, banco = dados
    sql = consultas_sql.executar(banco, "faturas_sem_cobranca")
    assert sql["receita_perdida"].sum() == pytest.approx(conc["receita_perdida"].sum())


def test_inadimplencia_bate(dados):
    conc, banco = dados
    sql = consultas_sql.executar(banco, "inadimplencia_total").iloc[0]
    assert sql["inadimplencia"] == pytest.approx(indicadores.resumo_financeiro(conc)["inadimplencia"], abs=1e-4)


def test_indicadores_mensais_batem(dados):
    conc, banco = dados
    sql = consultas_sql.executar(banco, "indicadores_mensais")
    pandas = indicadores.evolucao_mensal(conc)
    for coluna in ("valor_a_maior", "receita_perdida", "valor_indevido", "economia_real"):
        assert list(sql[coluna]) == pytest.approx(list(pandas[coluna].round(2)))
    assert list(sql["inadimplencia"]) == pytest.approx(list(pandas["inadimplencia"]), abs=1e-4)
