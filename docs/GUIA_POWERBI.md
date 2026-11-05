# Guia: dashboard no Power BI

Passo a passo para montar o dashboard com as tabelas geradas pelo notebook em `output/powerbi/`.
Tempo estimado: **30 a 40 minutos**.

## 1. Tabelas (modelo estrela)

```
                    dim_calendario
                   (mes_referencia)
                          │ 1
                          │
                          │ *
dim_clientes 1 ─── * fato_conciliacao ──── (classificação, valores, impacto)
 (id_cliente)          (id_cliente, mes_referencia)

fato_faturas, fato_cobrancas → ligadas da mesma forma (id_cliente e mes_referencia)
indicadores_mensais          → ligada só ao calendário (mes_referencia)
log_inconsistencias          → tabela solta (página de qualidade de dados)
```

| Arquivo | Tipo | Uma linha por |
|---|---|---|
| `fato_conciliacao.csv` | **Fato principal** | caso conciliado (cliente × mês, ou boleto duplicado) |
| `dim_clientes.csv` | Dimensão | cliente |
| `dim_calendario.csv` | Dimensão | mês |
| `fato_faturas.csv` | Fato | fatura Enel tratada |
| `fato_cobrancas.csv` | Fato | boleto Goener tratado |
| `indicadores_mensais.csv` | Agregada | mês (já calculada no Python) |
| `log_inconsistencias.csv` | Qualidade | valor tratado na Etapa 1 |

## 2. Importar sem erro de número (importante!)

Os CSVs estão no **padrão brasileiro**: separador `;`, vírgula decimal (`341,15`, `0,15`) e datas `AAAA-MM-DD`. O Power BI em português lê direto, **sem configurar localidade**.

> Se o seu Power BI estiver em inglês, faça o contrário: em **Arquivo → Opções → Configurações regionais (arquivo atual)**, escolha **Português (Brasil)** em *Localidade para importação*.

1. **Obter dados → Texto/CSV**, escolha o arquivo e clique em **Transformar dados**. Confira se o delimitador detectado é **Ponto e vírgula**.
2. Confira os tipos:
   - `uc`, `cpf_cnpj`, `id_cliente`, `id_cobranca` → **Texto** (para não perder os zeros à esquerda)
   - `vencida`, `vencida_nao_paga`, `flag_revisao`, `cobranca_duplicada` → **Verdadeiro/Falso**
   - `mes_referencia`, `data_*` → **Data**
3. Repita para cada arquivo e clique em **Fechar e aplicar**.

> Atenção: **não** use *Obter dados → Pasta → Combinar*. Essa opção empilha arquivos com as mesmas colunas, e aqui cada CSV tem colunas diferentes. Se quiser partir da pasta, use **Transformar dados** e clique em **Binary** na linha de cada arquivo para abri-lo como uma consulta separada (escolha **Ponto e vírgula** como delimitador).

## 3. Relacionamentos (Exibição de modelo)

| De (muitos) | Para (um) | Coluna |
|---|---|---|
| `fato_conciliacao` | `dim_clientes` | `id_cliente` |
| `fato_conciliacao` | `dim_calendario` | `mes_referencia` |
| `fato_faturas` | `dim_clientes` | `id_cliente` |
| `fato_faturas` | `dim_calendario` | `mes_referencia` |
| `fato_cobrancas` | `dim_clientes` | `id_cliente` |
| `fato_cobrancas` | `dim_calendario` | `mes_referencia` |
| `indicadores_mensais` | `dim_calendario` | `mes_referencia` |

Direção do filtro: **única** (da dimensão para o fato). Em `dim_calendario`, ordene `mes_ano` pela coluna `mes_referencia` (**Ferramentas de coluna → Classificar por coluna**), senão os meses ficam em ordem alfabética.

## 4. Medidas DAX

Crie uma tabela vazia chamada `_Medidas` (**Inserir dados → OK**) e adicione:

```dax
Cobrado a Maior = SUM ( fato_conciliacao[valor_a_maior] )

Cobrado a Menor = SUM ( fato_conciliacao[valor_a_menor] )

Receita Perdida = SUM ( fato_conciliacao[receita_perdida] )

Cobrança Indevida = SUM ( fato_conciliacao[valor_indevido] )

Impacto Total = [Cobrado a Maior] + [Cobrado a Menor] + [Receita Perdida] + [Cobrança Indevida]

Valor Faturado =
CALCULATE (
    SUM ( fato_conciliacao[valor_cobrado] ),
    NOT ISBLANK ( fato_conciliacao[id_cobranca] ),
    fato_conciliacao[classificacao] <> "Cobrança indevida"
)

% Impacto sobre Faturado = DIVIDE ( [Impacto Total], [Valor Faturado] )

Economia Recebida = SUM ( fato_conciliacao[economia_real] )

Economia Prometida = SUM ( fato_conciliacao[economia_contratada] )

Total Vencido =
CALCULATE (
    SUM ( fato_conciliacao[valor_cobrado] ),
    fato_conciliacao[vencida] = TRUE (),
    NOT ISBLANK ( fato_conciliacao[id_cobranca] ),
    fato_conciliacao[classificacao] <> "Cobrança indevida"
)

Vencido Não Pago =
CALCULATE (
    SUM ( fato_conciliacao[valor_cobrado] ),
    fato_conciliacao[vencida_nao_paga] = TRUE (),
    NOT ISBLANK ( fato_conciliacao[id_cobranca] ),
    fato_conciliacao[classificacao] <> "Cobrança indevida"
)

Inadimplência % = DIVIDE ( [Vencido Não Pago], [Total Vencido] )

Casos = COUNTROWS ( fato_conciliacao )

Casos com Erro =
CALCULATE (
    [Casos],
    fato_conciliacao[classificacao] IN { "Cobrado a maior", "Cobrado a menor",
                                         "Fatura sem cobrança", "Cobrança indevida" }
)

% Casos OK = DIVIDE ( CALCULATE ( [Casos], fato_conciliacao[classificacao] = "OK" ), [Casos] )
```

**Conferência:** sem filtros, os cartões devem mostrar Cobrado a Maior = **R$ 6.058,61**, Receita Perdida = **R$ 10.978,82**, Cobrança Indevida = **R$ 12.217,97** e Inadimplência = **12,78%**. São os mesmos números do notebook.

Formatos: medidas em R$ → *Moeda, 2 casas*; percentuais → *Porcentagem, 1 casa*.

Formate também as colunas (modo de exibição de **Tabela** → clique na coluna → **Ferramentas de coluna**). Com o formato *Geral*, o Power BI corta zeros no final (`0,2` ao lado de `0,15`):

| Coluna | Formato | Casas |
|---|---|---|
| Valores em R$ (`valor_cobrado`, `valor_esperado`, `diferenca`, `valor_a_maior`, `valor_a_menor`, `receita_perdida`, `valor_indevido`, `economia_*`, `valor_faturado`, `total_vencido`, `vencido_nao_pago`) | Moeda (R$) | 2 |
| `desconto_contratado` | Porcentagem (`15%`, `20%`) | 0 |
| `inadimplencia` | Porcentagem | 1 |
| `tarifa_kwh` | Número decimal | 4 |
| `consumo_kwh`, `energia_compensada_kwh` | Número inteiro, com separador de milhar | 0 |
| `casos_com_erro` | Número inteiro | 0 |

> Os CSVs já saem arredondados (R$ e kWh com 2 casas; tarifa, desconto e taxas com 4) e com vírgula decimal. O formato acima é só a exibição: com **Moeda R$ Português (Brasil)**, os valores aparecem como `R$ 3.424,53`.

## 5. Layout sugerido (4 páginas)

Cores: verde-petróleo Goener `#0f6e73` para títulos e séries únicas. Para os tipos de erro use a mesma paleta do notebook: **Cobrado a maior** `#2a78d6`, **Receita perdida** `#eb6834`, **Cobrança indevida** `#1baf7a`.

### Página 1: Visão geral
```
┌──────────────────────────────────────────────────────────────────┐
│ [Segmentação: mes_ano]   [Segmentação: cidade]   [status_cliente]│
├──────────┬──────────┬──────────┬──────────┬──────────┬───────────┤
│ Cobrado  │ Receita  │ Cobrança │ Impacto  │ Economia │ Inadim-   │
│ a Maior  │ Perdida  │ Indevida │ Total    │ Recebida │ plência % │
├──────────┴──────────┴──────────┴─┬────────┴──────────┴───────────┤
│ Colunas empilhadas:              │ Barras: Casos por             │
│ Impacto por mês, por tipo        │ classificacao                 │
│ (eixo: mes_ano)                  │                               │
└──────────────────────────────────┴───────────────────────────────┘
```

### Página 2: Divergências
- **Tabela** com as colunas `classificacao`, `id_cliente`, `nome`, `mes_referencia`, `valor_esperado`, `valor_cobrado`, `diferenca`, `causa_provavel` e `motivo`, com filtro de página `classificacao` ≠ OK. Formatação condicional (barras de dados) em `diferenca`.
- **Barras** com Casos e Cobrado a Maior por `causa_provavel`.
- **Top N**: barras com Impacto Total por `nome` (filtro Top 10 pela medida).

### Página 3: Inadimplência e economia
- **Colunas**: Inadimplência % por `mes_ano`.
- **Linhas**: Economia Prometida × Economia Recebida por `mes_ano` (a diferença é o que foi cobrado a mais e precisa ser devolvido).
- **Cartões**: Total Vencido e Vencido Não Pago.

### Página 4: Qualidade dos dados
- **Matriz** de `log_inconsistencias` com linhas `aba` → `problema`, colunas `acao` e valores *Contagem de registro*.
- **Tabela** filtrada em `acao` = "sinalizado p/ revisão humana" (a fila de trabalho do time).

## 6. Atualização
Para atualizar o dashboard, rode o notebook de novo (os CSVs são sobrescritos) e clique em **Atualizar** no Power BI. Em produção, o Fabric faz isso automaticamente (ver `docs/PROPOSTA_FABRIC.md`).
