"""Dados de exemplo pequenos e controlados, usados por vários testes."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def clientes_validos():
    """Base bruta 100% dentro do contrato."""
    return pd.DataFrame({
        "id_cliente": ["C1", "C2"],
        "nome": ["Ana Lima", "Padaria Pão Dourado"],
        "cpf_cnpj": ["12345678901", "12345678000199"],
        "uc": ["0000000001", "0000000002"],
        "cidade": ["Fortaleza", "Caucaia"],
        "desconto_contratado": ["0.15", "0.2"],
        "data_adesao": ["2025-01-10", "2025-02-01"],
        "status": ["ativo", "cancelado"],
        "data_cancelamento": [None, "2026-05-10"],
    })


@pytest.fixture
def faturas_validas():
    return pd.DataFrame({
        "uc": ["0000000001", "0000000001", "0000000002"],
        "mes_referencia": ["2026-04", "2026-05", "2026-04"],
        "consumo_kwh": ["600", "650", "300"],
        "energia_compensada_kwh": ["500", "520", "200"],
        "tarifa_kwh": ["0.95", "0.95", "0.95"],
    })


@pytest.fixture
def cobrancas_validas():
    return pd.DataFrame({
        "id_cobranca": ["GB1", "GB2", "GB3"],
        "id_cliente": ["C1", "C1", "C2"],
        "mes_referencia": ["2026-04", "2026-05", "2026-04"],
        "valor_cobrado": ["403.75", "419.9", "152"],
        "data_vencimento": ["2026-05-10", "2026-06-10", "2026-05-10"],
        "data_pagamento": ["2026-05-08", None, "2026-05-09"],
        "status_pagamento": ["pago", "em aberto", "pago"],
    })
