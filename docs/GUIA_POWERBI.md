# Guia: dashboard no Power BI

Passo a passo para montar o dashboard a partir da **base tratada** gerada pelo notebook: `output/base_tratada.xlsx`.
Tempo estimado: **30 a 40 minutos**.

## 1. Tabelas (modelo estrela)

```
                    dim_calendario  (criada em DAX, passo 2.4)
                   (mes_referencia)
                          │ 1
                          │
                          │ *
   clientes 1 ─── * conciliacao ──── (classificação, valores, impacto)
 (id_cliente)       (id_cliente, mes_referencia)

faturas_enel, cobrancas_goener → ligadas da mesma forma (id_cliente e mes_referencia)
indicadores_mensais            → ligada só ao calendário (mes_referencia)
log_inconsistencias            → tabela solta (página de qualidade de dados)
```

| Aba do `base_tratada.xlsx` | Papel no modelo | Uma linha por |
|---|---|---|
| `conciliacao` | **Fato principal** | caso conciliado (cliente × mês, ou boleto duplicado) |
| `clientes` | Dimensão | cliente |
| `faturas_enel` | Fato | fatura Enel tratada |
| `cobrancas_goener` | Fato | boleto Goener tratado |
| `indicadores_mensais` | Agregada | mês (já calculada no Python) |
| `log_inconsistencias` | Qualidade | valor tratado na Etapa 1 |
| `dim_calendario` | Dimensão | mês (não existe no Excel: é criada no Power BI) |

As abas `resumo_log` e `validacao_base_original` não são necessárias no dashboard (são um resumo do log e o diagnóstico da base original).

## 2. Importar a base tratada

1. **Obter dados → Pasta de trabalho do Excel** e escolha `output/base_tratada.xlsx`.
2. No **Navegador**, marque as 6 abas: `conciliacao`, `clientes`, `faturas_enel`, `cobrancas_goener`, `indicadores_mensais` e `log_inconsistencias`. Clique em **Transformar dados**.
3. Confira os tipos em cada consulta (o Excel já guarda números, datas e Verdadeiro/Falso, então quase tudo vem certo):
   - `uc`, `cpf_cnpj`, `id_cliente`, `id_cobranca` → **Texto** (para não perder os zeros à esquerda)
   - `vencida`, `vencida_nao_paga`, `flag_revisao`, `cobranca_duplicada` → **Verdadeiro/Falso**
   - `mes_referencia`, `data_*` → **Data** (o Power BI costuma trazer como *Data/Hora*; troque para **Data**, senão os relacionamentos com o calendário falham)
   - se a primeira linha vier como dados (`Column1`, `Column2`...), use **Usar a primeira linha como cabeçalho**
4. Clique em **Fechar e aplicar**.

### 2.4 Criar o calendário

O Excel não tem tabela de meses. Crie em **Modelagem → Nova tabela**:

```dax
dim_calendario =
VAR Meses =
    FILTER (
        CALENDAR ( MIN ( conciliacao[mes_referencia] ), MAX ( conciliacao[mes_referencia] ) ),
        DAY ( [Date] ) = 1
    )
RETURN
    SELECTCOLUMNS (
        Meses,
        "mes_referencia", [Date],
        "ano", YEAR ( [Date] ),
        "mes", MONTH ( [Date] ),
        "mes_nome", MID ( "janfevmarabrmaijunjulagosetoutnovdez", ( MONTH ( [Date] ) - 1 ) * 3 + 1, 3 ),
        "mes_ano", MID ( "janfevmarabrmaijunjulagosetoutnovdez", ( MONTH ( [Date] ) - 1 ) * 3 + 1, 3 )
                   & "/" & FORMAT ( [Date], "yy" ),
        "trimestre", "T" & QUARTER ( [Date] )
    )
```

Ela gera os 6 meses da base (abr/26 a set/26). A `conciliacao` reúne todas as faturas e cobranças, então cobre o período das outras tabelas também. Deixe `mes_referencia` de `dim_calendario` como **Data** (**Ferramentas de coluna → Tipo de dados**).

## 3. Relacionamentos (Exibição de modelo)

**Antes de começar:** o Power BI cria relacionamentos automáticos ao importar, e alguns ficam errados (por exemplo, ligações pela coluna `uc` ou entre duas tabelas fato). Em **Página Inicial → Gerenciar relações**, exclua todos e crie os 7 abaixo, arrastando a coluna da tabela "muitos" até a tabela "um" no modo de exibição de **Modelo** (ou em **Gerenciar relações → Nova**).

| De (muitos) | Para (um) | Coluna |
|---|---|---|
| `conciliacao` | `clientes` | `id_cliente` |
| `conciliacao` | `dim_calendario` | `mes_referencia` |
| `faturas_enel` | `clientes` | `id_cliente` |
| `faturas_enel` | `dim_calendario` | `mes_referencia` |
| `cobrancas_goener` | `clientes` | `id_cliente` |
| `cobrancas_goener` | `dim_calendario` | `mes_referencia` |
| `indicadores_mensais` | `dim_calendario` | `mes_referencia` |

`log_inconsistencias` fica **sem relacionamento**: é usado só na página de qualidade dos dados.

**Confira cada relação** (clique duas vezes na linha da relação):
- Cardinalidade **Muitos para um (\*:1)**, direção do filtro cruzado **Única** (da dimensão para o fato) e **Ativa** marcada.
- Se o Power BI sugerir *Muitos para muitos* ou *Um para um*, os tipos das colunas estão diferentes entre as tabelas. Deixe `mes_referencia` como **Data** e `id_cliente` como **Texto** nas duas pontas.

**Ordem dos meses:** em `dim_calendario`, clique em `mes_ano` → **Ferramentas de coluna → Classificar por coluna → `mes_referencia`** (faça o mesmo com `mes_nome`). Sem isso, os meses ficam em ordem alfabética (abr, ago, jul...).

**Boas práticas nos visuais:**
- Use `mes_ano` de `dim_calendario` e `nome`, `cidade` e `status` de `clientes`, e não as colunas repetidas dentro das tabelas fato (`nome`, `cidade`, `status_cliente` da `conciliacao`). Assim um filtro vale para todas as tabelas ao mesmo tempo.
- As 3 *Faturas sem cliente cadastrado* têm `id_cliente` vazio e aparecem como **(Em branco)** quando o visual é por cliente. Está certo: são UCs que não existem no cadastro.

## 4. Medidas DAX

Crie uma tabela vazia chamada `_Medidas` (**Inserir dados → OK**) e adicione:

```dax
Cobrado a Maior = SUM ( conciliacao[valor_a_maior] )

Cobrado a Menor = SUM ( conciliacao[valor_a_menor] )

Receita Perdida = SUM ( conciliacao[receita_perdida] )

Cobrança Indevida = SUM ( conciliacao[valor_indevido] )

Impacto Total = [Cobrado a Maior] + [Cobrado a Menor] + [Receita Perdida] + [Cobrança Indevida]

Valor Faturado =
CALCULATE (
    SUM ( conciliacao[valor_cobrado] ),
    NOT ISBLANK ( conciliacao[id_cobranca] ),
    conciliacao[classificacao] <> "Cobrança indevida"
)

% Impacto sobre Faturado = DIVIDE ( [Impacto Total], [Valor Faturado] )

Economia Recebida = SUM ( conciliacao[economia_real] )

Economia Prometida = SUM ( conciliacao[economia_contratada] )

Total Vencido =
CALCULATE (
    SUM ( conciliacao[valor_cobrado] ),
    conciliacao[vencida] = TRUE (),
    NOT ISBLANK ( conciliacao[id_cobranca] ),
    conciliacao[classificacao] <> "Cobrança indevida"
)

Vencido Não Pago =
CALCULATE (
    SUM ( conciliacao[valor_cobrado] ),
    conciliacao[vencida_nao_paga] = TRUE (),
    NOT ISBLANK ( conciliacao[id_cobranca] ),
    conciliacao[classificacao] <> "Cobrança indevida"
)

Inadimplência % = DIVIDE ( [Vencido Não Pago], [Total Vencido] )

Casos = COUNTROWS ( conciliacao )

Casos com Erro =
CALCULATE (
    [Casos],
    conciliacao[classificacao] IN { "Cobrado a maior", "Cobrado a menor",
                                         "Fatura sem cobrança", "Cobrança indevida" }
)

% Casos OK = DIVIDE ( CALCULATE ( [Casos], conciliacao[classificacao] = "OK" ), [Casos] )
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

> A base tratada já sai arredondada (R$ e kWh com 2 casas; tarifa, desconto e taxas com 4). O formato acima é só a exibição: com **Moeda R$ Português (Brasil)**, os valores aparecem como `R$ 3.424,53`.

## 5. Layout sugerido (4 páginas)

Cores: verde-petróleo Goener `#0f6e73` para títulos e séries únicas. Para os tipos de erro use a mesma paleta do notebook: **Cobrado a maior** `#2a78d6`, **Receita perdida** `#eb6834`, **Cobrança indevida** `#1baf7a`.

### Página 1: Visão geral
```
┌──────────────────────────────────────────────────────────────────┐
│ [Segmentação: mes_ano]   [Segmentação: cidade]   [Segm.: status] │
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
Para atualizar o dashboard, rode o notebook de novo (o `base_tratada.xlsx` é sobrescrito; feche-o no Excel antes) e clique em **Atualizar** no Power BI. O `dim_calendario` se recalcula sozinho. Em produção, o Fabric faz isso automaticamente (ver `docs/PROPOSTA_FABRIC.md`).

> **Alternativa em CSV:** o notebook também grava as mesmas tabelas em `output/powerbi/` (`fato_conciliacao`, `dim_clientes`, `dim_calendario`...), no padrão brasileiro (`;` e vírgula decimal). O conteúdo é idêntico ao do Excel; muda só o nome das tabelas e o calendário já vem pronto.
