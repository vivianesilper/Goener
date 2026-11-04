"""Cada formato encontrado na base original precisa ser convertido para o padrão."""
import pandas as pd
import pytest

from src import limpeza


@pytest.mark.parametrize("bruto, esperado", [
    ("34742830", "0034742830"),      # zeros à esquerda perdidos pelo Excel
    ("0046 147280", "0046147280"),   # espaço no meio
    ("009082600-0", "0090826000"),   # hífen
    ("0037023439", "0037023439"),    # já no padrão
    ("12345678901", None),           # mais de 10 dígitos: irrecuperável
    (None, None),
])
def test_normalizar_uc(bruto, esperado):
    assert limpeza.normalizar_uc(bruto) == esperado


@pytest.mark.parametrize("bruto, esperado", [
    ("262.849.877-69", "26284987769"),
    ("323705895", "00323705895"),        # CPF que perdeu 2 zeros
    ("947055169409", "00947055169409"),  # CNPJ que perdeu 2 zeros
    ("04505331586923", "04505331586923"),
])
def test_normalizar_documento(bruto, esperado):
    assert limpeza.normalizar_documento(bruto) == esperado


@pytest.mark.parametrize("bruto, esperado", [
    ("15%", 0.15), ("15", 0.15), ("15,0", 0.15), ("0.15", 0.15), ("0.2", 0.2), (None, None),
])
def test_normalizar_percentual(bruto, esperado):
    assert limpeza.normalizar_percentual(bruto) == esperado


@pytest.mark.parametrize("bruto, esperado", [
    ("R$ 9.666,09", 9666.09), ("R$ 302,04", 302.04), ("256.71", 256.71),
    ("361", 361.0), ("-380.69", -380.69), ("0,9184", 0.9184), ("abc", None),
])
def test_normalizar_numero(bruto, esperado):
    assert limpeza.normalizar_numero(bruto) == esperado


@pytest.mark.parametrize("bruto, esperado", [
    ("2025-04-04", "2025-04-04"), ("04/10/2025", "2025-10-04"), ("31/02/2025", None),
])
def test_normalizar_data_le_padrao_brasileiro(bruto, esperado):
    resultado = limpeza.normalizar_data(bruto)
    assert (resultado.strftime("%Y-%m-%d") if resultado is not None else None) == esperado


@pytest.mark.parametrize("bruto", ["2026-07", "07/2026", "jul/26", "JUL/26"])
def test_normalizar_mes_tres_formatos(bruto):
    assert limpeza.normalizar_mes(bruto) == pd.Timestamp("2026-07-01")


def test_normalizar_nome_mantem_acentos_e_preposicoes():
    assert limpeza.normalizar_nome("  RESTAURANTE SABOR DO MAR ") == "Restaurante Sabor do Mar"
    assert limpeza.normalizar_nome("OTÁVIO BEZERRA") == "Otávio Bezerra"
