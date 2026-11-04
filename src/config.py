"""Parâmetros do processo em um só lugar (nada de valores fixos escondidos no código)."""
from pathlib import Path

import pandas as pd

# --- Caminhos ---------------------------------------------------------------
RAIZ = Path(__file__).resolve().parents[1]
ARQUIVO_BASE = RAIZ / "data" / "base_case_goener.xlsx"
PASTA_SAIDA = RAIZ / "output"
PASTA_POWERBI = PASTA_SAIDA / "powerbi"
ARQUIVO_MARKDOWN_ERROS = RAIZ / "ERROS_E_LOGS.md"

ABA_CLIENTES = "clientes"
ABA_FATURAS = "faturas_enel"
ABA_COBRANCAS = "cobrancas_goener"

# --- Regras de negócio (enunciado do case) ----------------------------------
DATA_CORTE = pd.Timestamp("2026-10-15")   # cobranças vencidas antes disso e sem pagamento = vencidas
TOLERANCIA_ARREDONDAMENTO = 0.05          # divergência de até R$ 0,05 é tratada como correta
CASAS_DECIMAIS = 2

# --- Formatos esperados -----------------------------------------------------
DIGITOS_UC = 10
DIGITOS_CPF = 11
DIGITOS_CNPJ = 14
DESCONTO_MIN, DESCONTO_MAX = 0.0, 1.0     # desconto em fração (0.15 = 15%)
STATUS_CLIENTE_VALIDOS = {"ativo", "cancelado"}
STATUS_PAGAMENTO_VALIDOS = {"pago", "em aberto"}

MESES_PT = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
            "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}

# --- Conciliação (Etapa 2) --------------------------------------------------
OK = "OK"
COBRADO_A_MAIOR = "Cobrado a maior"
COBRADO_A_MENOR = "Cobrado a menor"
FATURA_SEM_COBRANCA = "Fatura sem cobrança"
COBRANCA_INDEVIDA = "Cobrança indevida"
INCONCLUSIVO = "Inconclusivo"
FATURA_SEM_CLIENTE = "Fatura sem cliente cadastrado"
NAO_COBRAVEL = "Não cobrável (cliente cancelado)"
ORDEM_CLASSIFICACAO = [OK, COBRADO_A_MAIOR, COBRADO_A_MENOR, FATURA_SEM_COBRANCA,
                       COBRANCA_INDEVIDA, INCONCLUSIVO, FATURA_SEM_CLIENTE, NAO_COBRAVEL]

# Fatores testados para detectar vírgula/casa decimal deslocada no valor cobrado
FATORES_ESCALA = (10, 100, 0.1, 0.01)

# --- Indicadores (Etapa 3) --------------------------------------------------
QTD_MAIORES_DIVERGENCIAS = 10

# --- Identidade visual dos gráficos ------------------------------------------
COR_MARCA = "#0f6e73"        # verde-petróleo Goener: títulos e séries únicas
COR_DESTAQUE = "#8cc63f"     # verde-limão Goener: faixas e detalhes
COR_TEXTO = "#0b0b0b"
COR_TEXTO_SECUNDARIO = "#52514e"
COR_GRADE = "#e6e5e0"
COR_NEUTRA = "#b9b8b2"
# Paleta categórica de referência (3 primeiras posições validadas para daltonismo)
CORES_IMPACTO = {"Cobrado a maior": "#2a78d6", "Receita perdida": "#eb6834",
                 "Cobrança indevida": "#1baf7a"}

# --- Ações do log de inconsistências ----------------------------------------
CORRIGIDO = "corrigido"
DESCARTADO = "descartado"
REVISAO = "sinalizado p/ revisão humana"
