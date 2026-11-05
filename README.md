# Conciliação de faturas: Enel × cobranças Goener

Case técnico · **Analista de Tecnologias e Operações** · Viviane Pereira

A Goener cobra os clientes pela energia solar que aparece como **energia compensada** na conta da Enel. Alguns boletos não batiam com a fatura. Este projeto, em Python, **trata as bases, concilia o que a Enel registrou com o que a Goener cobrou, mede o impacto financeiro e impede que os erros voltem**.

> **valor da cobrança = energia compensada (kWh) × tarifa (R$/kWh) × (1 − desconto contratado)**, arredondado em 2 casas

---

## Resultado em números

| | |
|---|---|
| Faturado no período (abr–set/2026) | **R$ 656,5 mil** |
| Impacto dos erros | **R$ 29,3 mil (4,5%)** |
| Cobrado a mais (15 boletos, 12 clientes) | **R$ 6.058,61** |
| Cobrado a menos | **R$ 0,00**: todo erro foi contra o cliente |
| Deixou de ser faturado (6 faturas sem boleto) | **R$ 10.978,82** |
| Cobranças indevidas (8 boletos, nenhum pago) | **R$ 12.217,97** |
| Economia recebida pelos clientes | **R$ 111.209,15** (o contrato prometia R$ 117.267,76; a diferença foi cobrada a mais) |
| Inadimplência na data de corte (15/10/2026) | **12,78%** |
| Problemas de dados encontrados e tratados | **23 tipos**, 2.825 violações de formato na base original |

**Causas:** desconto não aplicado, cálculo sobre o consumo total em vez da energia compensada, valor digitado com a vírgula deslocada e cancelamento que não bloqueia a cobrança.

---

## Entregáveis

| # | Entregável pedido | Onde está |
|---|---|---|
| 1 | Notebook que roda do início ao fim lendo o arquivo original | [`notebooks/case_goener.ipynb`](notebooks/case_goener.ipynb) |
| 2 | Base tratada + conciliação + log de inconsistências | [`output/base_tratada.xlsx`](output/base_tratada.xlsx) |
| 3 | Resumo executivo (1 página) | [`output/resumo_executivo.pdf`](output/resumo_executivo.pdf) e seção final do notebook |
| + | Todos os erros documentados, com decisão e justificativa | [`ERROS_E_LOGS.md`](ERROS_E_LOGS.md) |
| + | Diferencial: SQL | [`sql/consultas.sql`](sql/consultas.sql) (SQLite, roda no notebook) e [`sql/sqlserver/`](sql/sqlserver/) (versão T-SQL para SQL Server, testada com os mesmos resultados) |
| + | Diferencial: Power BI | [`docs/GUIA_POWERBI.md`](docs/GUIA_POWERBI.md), dashboard montado sobre o [`output/base_tratada.xlsx`](output/base_tratada.xlsx) |
| + | Diferencial: Microsoft Fabric / API | [`docs/PROPOSTA_FABRIC.md`](docs/PROPOSTA_FABRIC.md) |

**Abas do `base_tratada.xlsx`:** `conciliacao` · `indicadores_mensais` · `clientes` · `faturas_enel` · `cobrancas_goener` · `log_inconsistencias` · `resumo_log` · `validacao_base_original`

---

## Como rodar

Desenvolvido e testado com **Python 3.14.6**. Deve funcionar a partir do 3.10, mas essas versões não foram testadas.

```bash
# 1. Instalar as dependências
pip install -r requirements.txt

# 2. Rodar o notebook inteiro (gera todos os arquivos de output/)
jupyter nbconvert --to notebook --execute --inplace notebooks/case_goener.ipynb
#    ou abra no Jupyter e use "Kernel > Restart & Run All"

# 3. Rodar os testes (75 testes)
python -m pytest
```

O notebook encontra a raiz do projeto sozinho, então pode ser aberto de qualquer pasta. O arquivo original fica em `data/` e **nunca é alterado**.

---

## Bibliotecas utilizadas

Ambiente de desenvolvimento: **Python 3.14.6**, Windows 11. As versões exatas estão fixadas em [`requirements.txt`](requirements.txt).

### Bibliotecas externas (instaladas com `pip`)

| Biblioteca | Versão | Para que serve no projeto | Onde é usada |
|---|---|---|---|
| **pandas** | 2.3.3 | Leitura do Excel, tratamento das tabelas, cruzamento (merge) entre as abas, agrupamentos dos indicadores, exportação para Excel/CSV e tabelas formatadas no notebook (`Styler`) | Todos os módulos de `src/`, testes e notebook |
| **numpy** | 2.3.4 | Arredondamento da regra de negócio (`np.round`) e cálculo vetorizado das colunas de impacto (`np.where`) | `src/conciliacao.py` |
| **openpyxl** | 3.1.5 | "Motor" que o pandas usa para **ler** o `.xlsx` original e **gravar** o `base_tratada.xlsx` (congela o cabeçalho e ajusta a largura das colunas) | `src/limpeza.py` (leitura), `src/exportacao.py` (gravação) |
| **matplotlib** | 3.10.8 | Gráficos da Etapa 3 (barras, barras empilhadas e linhas) nas cores da Goener, salvos em PNG | `src/graficos.py` |
| **jinja2** | 3.1.6 | Exigida pelo pandas para gerar as tabelas coloridas do notebook (`DataFrame.style`) | Notebook (indiretamente, via pandas) |
| **reportlab** | 5.1.0 | Geração do **resumo executivo em PDF** de 1 página (cabeçalho, cartões, gráfico e listas) | `src/resumo_executivo.py` |
| **pytest** | 9.2.0 | Os 75 testes automáticos da Etapa 4 | `tests/` e seção 4.4 do notebook |
| **notebook** | 7.4.7 | Interface Jupyter para abrir e rodar o `case_goener.ipynb` | Execução do notebook |
| **ipython** | 9.6.0 | Exibição de HTML e Markdown dentro do notebook (`display`, `HTML`, `Markdown`): cartões de indicadores e resumo executivo | Notebook |
| **ipykernel** | 7.0.1 | Kernel Python que executa as células do notebook | Execução do notebook |
| **nbconvert** | 7.16.6 | Executa o notebook inteiro pela linha de comando (`jupyter nbconvert --execute`), garantindo que ele roda do início ao fim | Comando de execução (seção "Como rodar") |
| **nbformat** | 5.10.4 | Leitura e escrita do arquivo `.ipynb` (dependência do nbconvert) | Execução do notebook |

### Bibliotecas padrão do Python (já vêm com o Python, não precisam de instalação)

| Módulo | Para que serve no projeto | Onde é usado |
|---|---|---|
| **pathlib** | Caminhos de arquivos que funcionam em Windows, Linux e Mac; localização da raiz do projeto | `src/config.py`, notebook, `tests/conftest.py` |
| **re** (expressões regulares) | Reconhecer formatos (UC com 10 dígitos, datas, meses `abr/26`, valores `R$ 1.234,56`) e separar as consultas do arquivo `.sql` | `src/limpeza.py`, `src/consultas_sql.py` |
| **unicodedata** | Remover acentos para comparar textos ("Maracanaú" = "MARACANAU") | `src/limpeza.py` |
| **datetime** | Data e hora de geração do `ERROS_E_LOGS.md` | `src/relatorio_erros.py` |
| **dataclasses** | Estrutura `Regra` do contrato de dados (coluna, descrição, função de checagem) | `src/validacao.py` |
| **typing** | Indicação de tipo da função de cada regra (`Callable`), para legibilidade | `src/validacao.py` |
| **sqlite3** | Banco SQL em memória onde rodam as consultas de conferência (diferencial SQL) | `src/consultas_sql.py` |
| **subprocess** | Rodar o `pytest` de dentro do notebook e mostrar o resultado | Notebook (seção 4.4) |
| **sys** | Incluir a raiz do projeto no caminho de importação (para `from src import ...` funcionar) e chamar o Python atual | Notebook, `tests/conftest.py` |

> **Por que essas e não outras:** o case pede Python e permite bibliotecas livres. Fiquei no ecossistema mais conhecido (pandas, numpy, matplotlib e pytest), que qualquer avaliador consegue ler e rodar. Usei a biblioteca padrão sempre que bastava, por exemplo **sqlite3** para o SQL, que não exige instalar um servidor de banco de dados.

---

## Estrutura

```
Case_Goener/
├── README.md
├── ERROS_E_LOGS.md            ← erros de dados e de cobrança (gerado pelo código)
├── requirements.txt
├── data/
│   ├── base_case_goener.xlsx  ← base original (somente leitura)
│   └── enunciado_case_goener.pdf
├── notebooks/
│   └── case_goener.ipynb      ← apresentação: Etapas 1 a 4, diferenciais e resumo
├── src/                       ← toda a lógica, em funções reutilizáveis
│   ├── config.py              ← parâmetros e regras (tolerância, data de corte, cores...)
│   ├── limpeza.py             ← Etapa 1: normalização, regras de qualidade, relacionamentos
│   ├── log_inconsistencias.py ← registro de cada problema e da ação tomada
│   ├── conciliacao.py         ← Etapa 2: regra de negócio, classificação, causa provável
│   ├── indicadores.py         ← Etapa 3: totais, top 10, economia, inadimplência, mensal
│   ├── graficos.py            ← Etapa 3: cartões e gráficos
│   ├── validacao.py           ← Etapa 4: contrato de dados + trava de emissão
│   ├── consultas_sql.py       ← diferencial: roda as consultas SQL
│   ├── exportacao.py          ← Excel, CSVs do Power BI e calendário
│   ├── relatorio_erros.py     ← gera o ERROS_E_LOGS.md
│   └── resumo_executivo.py    ← gera o resumo em PDF e HTML
├── sql/
│   ├── consultas.sql          ← conferência independente em SQL (SQLite)
│   └── sqlserver/             ← mesma conferência em T-SQL: 01_carga.sql e 02_consultas.sql
├── tests/                     ← 75 testes (pytest)
│   ├── test_normalizacao.py
│   ├── test_validacao.py
│   ├── test_conciliacao.py
│   ├── test_sql.py
│   └── test_pipeline.py
├── docs/
│   ├── GUIA_POWERBI.md
│   └── PROPOSTA_FABRIC.md
└── output/                    ← tudo aqui é gerado pelo notebook
    ├── base_tratada.xlsx
    ├── resumo_executivo.pdf
    ├── graficos/*.png
    └── powerbi/*.csv          ← mesmas tabelas em CSV (carga do SQL Server)
```

---

## Como o processo funciona

```
 base original ──► Etapa 1: Tratamento ──► Etapa 2: Conciliação ──► Etapa 3: Indicadores
 (3 abas)          padroniza, corrige,       regra de negócio,        R$, top 10, economia,
                   descarta ou sinaliza      8 classificações,        inadimplência, mês a mês
                   + log de inconsistências  causa provável
                                    ▲                      │
                                    └── Etapa 4: Prevenção ┘
                                        contrato de dados na entrada
                                        trava antes da emissão dos boletos
```

### Etapa 1: Tratamento e qualidade dos dados
Para cada problema há uma de três ações, todas registradas no log:

| Ação | Quando |
|---|---|
| 🟢 **Corrigir** | O valor certo pode ser recuperado sem dúvida (zeros à esquerda, formatos de data/número, sinal invertido) |
| 🔴 **Descartar** | Cópia exata de outro registro (4 clientes, 6 faturas) |
| 🟡 **Revisão humana** | Dado faltando ou contraditório. **Fica na base**, marcado, e a conciliação o trata como *Inconclusivo* |

### Etapa 2: Conciliação
| Classificação | Casos |
|---|---|
| OK (diferença de até R$ 0,05) | 666 |
| Cobrado a maior | 15 |
| Cobrado a menor | 0 |
| Fatura sem cobrança | 6 |
| Cobrança indevida (duplicada ou pós-cancelamento) | 8 |
| Inconclusivo | 20 |
| Fatura sem cliente cadastrado *(categoria criada)* | 3 |
| Não cobrável, cliente cancelado *(categoria criada)* | 9 |

A **causa provável** de cada divergência é encontrada recalculando o boleto com erros comuns (sem desconto, sobre o consumo, vírgula deslocada) e vendo qual deles reproduz exatamente o valor cobrado.

### Etapa 4: Prevenção
- **Contrato de dados:** recebe uma base nova e devolve cada violação (aba, linha do Excel, coluna, regra, valor). Na base original foram 2.825 violações. Na base tratada sobram 25, que são exatamente os casos de revisão humana.
- **Trava de emissão:** concilia o lote **antes** de emitir. Só sai boleto OK: 666 aprovados, 43 bloqueados e 6 faturas sem boleto apontadas.
- **Testes:** 75 testes cobrindo normalização, contrato, regra de negócio, classificação, trava, SQL e o processo de ponta a ponta.

---

## Premissas adotadas

1. Datas com barra seguem o padrão brasileiro **DD/MM/AAAA**. Nenhuma data tem mês maior que 12 na 2ª posição, o que confirma a leitura.
2. Desconto maior que 1 é percentual (`15` = 15%); até 1 já é fração (`0.15`).
3. Valor com vírgula é formato brasileiro (`R$ 9.666,09`).
4. CPF/CNPJ são fictícios (quase nenhum tem dígito verificador válido), por isso só a quantidade de dígitos é validada.
5. Consumo e boleto negativos são **sinal invertido**. A conciliação confirmou: os 2 boletos negativos ficaram OK após a correção.
6. **Nenhum dado ausente foi inventado.** Sem desconto ou sem energia compensada, o caso fica *Inconclusivo*.
7. Boletos duplicados **não são apagados** (são documentos financeiros): o boleto pago, ou o mais antigo, é o principal, e o outro é *Cobrança indevida*.
8. Cliente cancelado: o mês que **começa depois** da data de cancelamento não é cobrável (cancelou em 08/07 → julho ainda é cobrado, agosto não).
9. A inadimplência considera só boletos legítimos. Um boleto duplicado em aberto é erro da Goener, não dívida do cliente (com eles, a taxa seria 14,37%).
10. A economia do cliente é o valor da energia na tarifa Enel menos o boleto Goener efetivamente cobrado.
11. Na data de corte (15/10/2026), boleto **pago no próprio dia 15/10 conta como pago**. Nenhum pagamento da base é posterior a essa data; só um foi feito exatamente nela (GB50385, R$ 562,51).

---

## Decisões de código
- **Lógica em `src/`, apresentação no notebook:** funções pequenas, testáveis e reaproveitadas (as mesmas normalizações servem à limpeza e à validação).
- **Nenhum valor fixo escondido:** tolerância, data de corte, formatos, cores e limites ficam em `config.py`. O SQL do notebook recebe os parâmetros do mesmo lugar; na versão SQL Server eles ficam em `DECLARE` no topo do script.
- **Documentação gerada pelo código:** o `ERROS_E_LOGS.md` e o resumo executivo são montados a partir dos resultados e se atualizam a cada execução.
- **Rastreabilidade:** cada registro tratado guarda `linha_origem` (a linha no Excel original), e o log usa o mesmo identificador.
- **Leitura como texto:** o Excel é lido com `dtype=str`, para não perder zeros à esquerda nem esconder os formatos originais.

*Dados 100% fictícios, fornecidos para o processo seletivo.*
