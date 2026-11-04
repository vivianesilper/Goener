"""Teste de ponta a ponta com o arquivo real do case."""
import pytest

from src import config as cfg
from src.conciliacao import executar_conciliacao
from src.limpeza import executar_tratamento
from src.log_inconsistencias import COLUNAS_LOG
from src.validacao import validar_arquivo


@pytest.fixture(scope="module")
def resultado():
    r = executar_tratamento()
    r["conciliacao"] = executar_conciliacao(r["clientes"], r["faturas"], r["cobrancas"])
    return r


def test_log_tem_as_colunas_pedidas(resultado):
    log = resultado["log"].como_dataframe()
    assert {"aba", "registro", "problema", "acao"} <= set(COLUNAS_LOG)
    assert set(log["acao"]) <= {cfg.CORRIGIDO, cfg.DESCARTADO, cfg.REVISAO}


def test_chaves_unicas_depois_do_tratamento(resultado):
    assert resultado["clientes"]["id_cliente"].is_unique
    assert not resultado["faturas"].duplicated(["uc", "mes_referencia"]).any()
    assert resultado["clientes"]["uc"].str.fullmatch(r"\d{10}").all()


def test_todo_caso_ok_respeita_a_tolerancia(resultado):
    ok = resultado["conciliacao"][resultado["conciliacao"]["classificacao"] == cfg.OK]
    assert (ok["diferenca"].abs() <= cfg.TOLERANCIA_ARREDONDAMENTO).all()


def test_nenhuma_fatura_ou_boleto_se_perde(resultado):
    conc = resultado["conciliacao"]
    assert conc["id_cobranca"].notna().sum() == len(resultado["cobrancas"])
    # boletos duplicados repetem a fatura do mês para comparação, por isso contamos pares únicos
    assert len(conc.dropna(subset=["uc"]).drop_duplicates(["uc", "mes_referencia"])) == len(resultado["faturas"])


def test_validacao_encontra_problemas_na_base_original():
    violacoes = validar_arquivo()
    assert not violacoes.empty
    assert {cfg.ABA_CLIENTES, cfg.ABA_FATURAS, cfg.ABA_COBRANCAS} <= set(violacoes["aba"])
