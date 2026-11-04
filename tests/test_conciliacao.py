"""A regra de negócio, a classificação e a trava de emissão funcionam nos casos do case."""
import pandas as pd
import pytest

from src import config as cfg
from src.conciliacao import calcular_valor_esperado
from src.limpeza import LogInconsistencias, tratar_clientes, tratar_cobrancas, tratar_faturas, verificar_relacionamentos
from src.validacao import validar_lote_cobranca


def test_regra_do_enunciado():
    assert calcular_valor_esperado(500, 0.95, 0.15) == 403.75


def preparar(clientes, faturas, cobrancas):
    log = LogInconsistencias()
    cli = tratar_clientes(clientes, log)
    fat, cob = verificar_relacionamentos(cli, tratar_faturas(faturas, log), tratar_cobrancas(cobrancas, log), log)
    return cli, fat, cob


def classificar(clientes, faturas, cobrancas):
    from src.conciliacao import executar_conciliacao
    casos = executar_conciliacao(*preparar(clientes, faturas, cobrancas))
    return {(c, m.strftime("%Y-%m"), b if pd.notna(b) else None): str(k)
            for c, m, b, k in zip(casos.id_cliente, casos.mes_referencia, casos.id_cobranca, casos.classificacao)}


def test_tudo_certo_e_ok_ou_nao_cobravel(clientes_validos, faturas_validas, cobrancas_validas):
    resultado = classificar(clientes_validos, faturas_validas, cobrancas_validas)
    assert resultado[("C1", "2026-04", "GB1")] == cfg.OK
    assert resultado[("C1", "2026-05", "GB2")] == cfg.OK  # 520 × 0,95 × 0,85 = 419,90


@pytest.mark.parametrize("valor, classe", [
    ("403.80", cfg.OK),               # R$ 0,05 de diferença: arredondamento
    ("403.81", cfg.COBRADO_A_MAIOR),
    ("403.69", cfg.COBRADO_A_MENOR),
    ("475", cfg.COBRADO_A_MAIOR),     # desconto não aplicado: 500 × 0,95
])
def test_tolerancia_e_divergencia(clientes_validos, faturas_validas, cobrancas_validas, valor, classe):
    cobrancas_validas.loc[0, "valor_cobrado"] = valor
    assert classificar(clientes_validos, faturas_validas, cobrancas_validas)[("C1", "2026-04", "GB1")] == classe


def test_fatura_sem_cobranca(clientes_validos, faturas_validas, cobrancas_validas):
    sem_maio = cobrancas_validas.drop(index=1)
    assert classificar(clientes_validos, faturas_validas, sem_maio)[("C1", "2026-05", None)] == cfg.FATURA_SEM_COBRANCA


def test_cliente_cancelado_cobrado_depois_do_cancelamento(clientes_validos, faturas_validas, cobrancas_validas):
    # C2 cancelou em 10/05/2026: junho começa depois e não pode ser cobrado
    faturas = pd.concat([faturas_validas, pd.DataFrame([{"uc": "0000000002", "mes_referencia": "2026-06",
                         "consumo_kwh": "300", "energia_compensada_kwh": "200", "tarifa_kwh": "0.95"}])],
                        ignore_index=True)
    cobrancas = pd.concat([cobrancas_validas, pd.DataFrame([{"id_cobranca": "GB4", "id_cliente": "C2",
                           "mes_referencia": "2026-06", "valor_cobrado": "152", "data_vencimento": "2026-07-10",
                           "data_pagamento": None, "status_pagamento": "em aberto"}])], ignore_index=True)
    assert classificar(clientes_validos, faturas, cobrancas)[("C2", "2026-06", "GB4")] == cfg.COBRANCA_INDEVIDA


def test_boleto_duplicado_e_indevido(clientes_validos, faturas_validas, cobrancas_validas):
    copia = cobrancas_validas.iloc[[0]].assign(id_cobranca="GB9", status_pagamento="em aberto", data_pagamento=None)
    cobrancas = pd.concat([cobrancas_validas, copia], ignore_index=True)
    resultado = classificar(clientes_validos, faturas_validas, cobrancas)
    assert resultado[("C1", "2026-04", "GB1")] == cfg.OK              # o pago é o principal
    assert resultado[("C1", "2026-04", "GB9")] == cfg.COBRANCA_INDEVIDA


def test_desconto_vazio_e_inconclusivo(clientes_validos, faturas_validas, cobrancas_validas):
    clientes_validos.loc[0, "desconto_contratado"] = None
    assert classificar(clientes_validos, faturas_validas, cobrancas_validas)[("C1", "2026-04", "GB1")] == cfg.INCONCLUSIVO


def test_trava_de_emissao_bloqueia_valor_errado_e_aponta_faltantes(clientes_validos, faturas_validas, cobrancas_validas):
    lote = cobrancas_validas.drop(index=1)                 # maio do C1 ficou sem boleto
    lote.loc[0, "valor_cobrado"] = "4037.5"                # vírgula deslocada
    aprovados, bloqueados, faltantes = validar_lote_cobranca(*preparar(clientes_validos, faturas_validas, lote))
    assert list(bloqueados["id_cobranca"]) == ["GB1"]
    assert list(aprovados["id_cobranca"]) == ["GB3"]
    assert list(faltantes["mes_referencia"].dt.strftime("%Y-%m")) == ["2026-05"]
