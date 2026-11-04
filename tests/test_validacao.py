"""O contrato de dados aceita uma base correta e aponta cada tipo de erro encontrado no case."""
import pytest

from src import config as cfg
from src import validacao


def regras_violadas(df, aba):
    return set(validacao.validar_base(df, aba)["regra"])


def test_bases_validas_nao_tem_violacoes(clientes_validos, faturas_validas, cobrancas_validas):
    assert validacao.validar_base(clientes_validos, cfg.ABA_CLIENTES).empty
    assert validacao.validar_base(faturas_validas, cfg.ABA_FATURAS).empty
    assert validacao.validar_base(cobrancas_validas, cfg.ABA_COBRANCAS).empty
    assert validacao.validar_relacionamentos(clientes_validos, faturas_validas, cobrancas_validas).empty


# --- clientes -----------------------------------------------------------------
@pytest.mark.parametrize("coluna, valor_errado, regra", [
    ("uc", "34742830", "10 dígitos com zeros à esquerda"),
    ("cpf_cnpj", "262.849.877-69", "11 (CPF) ou 14 (CNPJ) dígitos, sem pontuação"),
    ("desconto_contratado", "15%", "fração com ponto decimal (ex.: 0.15)"),
    ("desconto_contratado", None, "obrigatório"),
    ("data_adesao", "04/10/2025", "data AAAA-MM-DD"),
    ("status", "ATIVO", "ativo ou cancelado"),
    ("nome", "  Ana Lima ", "sem espaços nas pontas"),
])
def test_cliente_fora_do_padrao(clientes_validos, coluna, valor_errado, regra):
    clientes_validos.loc[0, coluna] = valor_errado
    assert regra in regras_violadas(clientes_validos, cfg.ABA_CLIENTES)


def test_cliente_duplicado(clientes_validos):
    clientes_validos.loc[1, "id_cliente"] = "C1"
    assert "único na base" in regras_violadas(clientes_validos, cfg.ABA_CLIENTES)


def test_cancelado_sem_data(clientes_validos):
    clientes_validos.loc[1, "data_cancelamento"] = None
    assert "obrigatória para cliente cancelado" in regras_violadas(clientes_validos, cfg.ABA_CLIENTES)


# --- faturas ------------------------------------------------------------------
@pytest.mark.parametrize("coluna, valor_errado, regra", [
    ("mes_referencia", "abr/26", "mês AAAA-MM"),
    ("consumo_kwh", "-600", "não pode ser negativo"),
    ("energia_compensada_kwh", None, "obrigatória"),
    ("energia_compensada_kwh", "700", "não pode ser maior que o consumo"),
    ("tarifa_kwh", "0,95", "número positivo com ponto decimal"),
])
def test_fatura_fora_do_padrao(faturas_validas, coluna, valor_errado, regra):
    faturas_validas.loc[0, coluna] = valor_errado
    assert regra in regras_violadas(faturas_validas, cfg.ABA_FATURAS)


def test_fatura_duplicada(faturas_validas):
    faturas_validas.loc[1, "mes_referencia"] = "2026-04"
    assert "uma fatura por UC e mês" in regras_violadas(faturas_validas, cfg.ABA_FATURAS)


def test_fatura_de_uc_sem_cadastro(clientes_validos, faturas_validas, cobrancas_validas):
    faturas_validas.loc[0, "uc"] = "0099999999"
    violacoes = validacao.validar_relacionamentos(clientes_validos, faturas_validas, cobrancas_validas)
    assert list(violacoes["regra"]) == ["UC precisa existir no cadastro de clientes"]


# --- cobranças ----------------------------------------------------------------
@pytest.mark.parametrize("coluna, valor_errado, regra", [
    ("valor_cobrado", "R$ 403,75", "número com ponto decimal (sem R$)"),
    ("valor_cobrado", "-403.75", "maior que zero"),
    ("status_pagamento", "PAGO", "pago ou em aberto"),
    ("data_pagamento", None, "obrigatória quando status é pago"),
])
def test_cobranca_fora_do_padrao(cobrancas_validas, coluna, valor_errado, regra):
    cobrancas_validas.loc[0, coluna] = valor_errado
    assert regra in regras_violadas(cobrancas_validas, cfg.ABA_COBRANCAS)


def test_boleto_duplicado(cobrancas_validas):
    cobrancas_validas.loc[1, "mes_referencia"] = "2026-04"
    assert "um boleto por cliente e mês" in regras_violadas(cobrancas_validas, cfg.ABA_COBRANCAS)


def test_resultado_aponta_linha_do_excel(cobrancas_validas):
    cobrancas_validas.loc[2, "valor_cobrado"] = "R$ 152,00"
    violacao = validacao.validar_base(cobrancas_validas, cfg.ABA_COBRANCAS).iloc[0]
    assert violacao["linha"] == 4  # índice 2 + cabeçalho + base 1
    assert violacao["valor"] == "R$ 152,00"
