"""Registro central de tudo que foi encontrado e feito com os dados."""
import pandas as pd

COLUNAS_LOG = ["aba", "registro", "coluna", "problema", "valor_original",
               "valor_tratado", "acao", "justificativa"]


class LogInconsistencias:
    """Acumula inconsistências encontradas durante o tratamento.

    Cada chamada de `registrar` vira uma linha do log entregue no Excel e no Markdown.
    """

    def __init__(self):
        self._linhas = []

    def registrar(self, aba, registro, coluna, problema, valor_original,
                  valor_tratado, acao, justificativa):
        self._linhas.append(dict(zip(COLUNAS_LOG, [
            aba, registro, coluna, problema, _texto(valor_original),
            _texto(valor_tratado), acao, justificativa])))

    def como_dataframe(self):
        return pd.DataFrame(self._linhas, columns=COLUNAS_LOG)

    def resumo(self):
        """Uma linha por tipo de problema: quantas ocorrências e o que foi feito."""
        df = self.como_dataframe()
        return (df.groupby(["aba", "problema", "acao", "justificativa"], sort=False)
                  .size().reset_index(name="ocorrencias"))


def _texto(valor):
    if valor is None or (pd.api.types.is_scalar(valor) and pd.isna(valor)):
        return "(vazio)"
    if isinstance(valor, pd.Timestamp):
        return valor.strftime("%Y-%m-%d")
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor)
