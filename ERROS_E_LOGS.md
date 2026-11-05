# Erros encontrados e log de inconsistências

> Gerado automaticamente por `src/relatorio_erros.py` em 04/11/2026 17:19. Não edite à mão: rode o notebook de novo para atualizar.

## 1. Visão geral

| Aba | Linhas originais | Linhas tratadas | Tipos de problema | 🟢 Corrigido | 🔴 Descartado | 🟡 Revisão humana |
|---|---|---|---|---|---|---|
| `clientes` | 124 | 120 | 9 | 372 | 4 | 2 |
| `faturas_enel` | 729 | 723 | 8 | 819 | 6 | 12 |
| `cobrancas_goener` | 709 | 709 | 6 | 1282 | 0 | 7 |
| **Total** | 1562 | 1552 | 23 | 2473 | 10 | 21 |

### O que cada ação significa

| Ação | Quando usamos |
|---|---|
| 🟢 Corrigido | O valor certo pode ser recuperado sem dúvida (formato, zeros, sinal). |
| 🔴 Descartado | Cópia exata de outro registro; mantê-la contaria o mesmo fato duas vezes. |
| 🟡 Revisão humana | Falta informação ou há contradição; uma pessoa precisa decidir. O registro fica na base. |

## 2. Premissas adotadas

1. Datas com barra (`04/10/2025`) seguem o padrão brasileiro **DD/MM/AAAA**. Nenhuma data da base tem valor maior que 12 na posição do mês, o que confirma a leitura.
2. Desconto maior que 1 é percentual (`15` = 15%); menor ou igual a 1 já é fração (`0.15`).
3. Valor com vírgula é formato brasileiro (`R$ 9.666,09`: ponto = milhar, vírgula = decimal).
4. CPF/CNPJ são fictícios (o enunciado avisa) e quase nenhum tem dígito verificador válido, por isso validamos só a quantidade de dígitos (11 ou 14).
5. Consumo e boleto negativos são **sinal invertido** na exportação: usamos o valor absoluto e a conciliação confirma se o número bate com o esperado.
6. Nenhum valor ausente foi inventado ou estimado: registros sem dado essencial ficam na base, marcados para revisão, e a conciliação classifica o caso como **Inconclusivo**.
7. Boletos duplicados **não são apagados** (são documentos financeiros): ficam marcados e viram **Cobrança indevida** na conciliação.
8. Na data de corte (15/10/2026), boleto **pago no próprio dia 15/10 conta como pago** (a data de corte entra no período). A inadimplência usa o `status_pagamento` da base; isso equivale à situação na data de corte porque nenhum pagamento é posterior a 15/10. Só um boleto foi pago exatamente no dia 15/10 (GB50385, C1066, ref. ago/2026, R$ 562,51, vencido em 10/09).

## 3. Problemas por aba

### Aba `clientes`

| Problema | Qtd | Ação | Por quê | Exemplos (original → tratado) |
|---|---|---|---|---|
| Nome com espaços extras ou caixa despadronizada | 33 | 🟢 Corrigido | Removidos espaços nas pontas; nome em formato Título para evitar falsos duplicados. | `DIEGO NOGUEIRA CAVALCANTE` → `Diego Nogueira Cavalcante`<br>`  Hotel Beira Mar ` → `Hotel Beira Mar`<br>`YASMIN BARBOSA ROCHA` → `Yasmin Barbosa Rocha` |
| Cidade com espaços extras ou caixa despadronizada | 75 | 🟢 Corrigido | Mesma cidade escrita de formas diferentes ('FORTALEZA', ' fortaleza ') quebraria agrupamentos por cidade. | `AQUIRAZ` → `Aquiraz`<br>`CAUCAIA` → `Caucaia`<br>` Fortaleza` → `Fortaleza` |
| UC sem os 10 dígitos (zeros à esquerda perdidos ou pontuação) | 40 | 🟢 Corrigido | A UC é a chave de ligação com as faturas; o Excel removeu os zeros à esquerda. Recolocados até completar 10 dígitos. | `82029073` → `0082029073`<br>`22139996` → `0022139996`<br>`49563745` → `0049563745` |
| CPF/CNPJ com pontuação | 72 | 🟢 Corrigido | Guardado só com dígitos para permitir comparação. | `468.071.545-16` → `46807154516`<br>`873.395.004-79` → `87339500479`<br>`618.324.210-24` → `61832421024` |
| CPF/CNPJ com zeros à esquerda perdidos | 3 | 🟢 Corrigido | O Excel trata documento como número e apaga zeros iniciais. Completado com zeros até 11 dígitos (CPF) ou 14 (CNPJ). | `947055169409` → `00947055169409`<br>`323705895` → `00323705895`<br>`962309130` → `00962309130` |
| Desconto em formato misto (15%, 15, 15,0, 0.15) | 73 | 🟢 Corrigido | Convertido para fração (0.15). Valores > 1 interpretados como percentual. | `18` → `0.18`<br>`10,0` → `0.1`<br>`15%` → `0.15` |
| Data em formato DD/MM/AAAA misturado com AAAA-MM-DD | 76 | 🟢 Corrigido | Convertida para AAAA-MM-DD. Premissa: barras = padrão brasileiro (nenhuma data tem mês > 12 na 2ª posição, o que confirma). | `16/07/2025` → `2025-07-16`<br>`16/11/2025` → `2025-11-16`<br>`27/12/2025` → `2025-12-27` |
| Desconto contratado vazio | 2 | 🟡 Revisão humana | Sem desconto não é possível calcular a cobrança. Não inventamos um valor: o cliente segue na base e a conciliação fica 'Inconclusiva' até o comercial informar o contrato. | `(vazio)` → `(vazio)`<br>`(vazio)` → `(vazio)` |
| Cliente duplicado | 4 | 🔴 Descartado | Depois de padronizar, os dados são idênticos à outra linha (só mudava caixa/pontuação). Manter os dois dobraria as faturas na conciliação. | `C1037` → `mantida linha 48`<br>`C1057` → `mantida linha 46`<br>`C1098` → `mantida linha 17` |

### Aba `faturas_enel`

| Problema | Qtd | Ação | Por quê | Exemplos (original → tratado) |
|---|---|---|---|---|
| UC sem os 10 dígitos (zeros perdidos, espaço ou hífen) | 286 | 🟢 Corrigido | Removidos espaços/hífens e recolocados zeros à esquerda para casar com o cadastro. | `57207740` → `0057207740`<br>`60476001` → `0060476001`<br>`0048 623800` → `0048623800` |
| Mês de referência em 3 formatos (2026-04, 04/2026, abr/26) | 368 | 🟢 Corrigido | Convertido para AAAA-MM. | `09/2026` → `2026-09`<br>`05/2026` → `2026-05`<br>`07/2026` → `2026-07` |
| Número com vírgula decimal | 159 | 🟢 Corrigido | Convertido para número com ponto decimal. | `0,9231` → `0.9231`<br>`0,9603` → `0.9603`<br>`0,9532` → `0.9532` |
| Consumo negativo | 6 | 🟢 Corrigido | Consumo não pode ser negativo. A energia compensada é positiva e cabe no valor absoluto, indicando sinal invertido na exportação. Usado o valor absoluto. | `-475` → `475`<br>`-7189` → `7189`<br>`-397` → `397` |
| Energia compensada vazia | 5 | 🟡 Revisão humana | É a base do cálculo da cobrança. Não estimamos: a conciliação desse mês fica 'Inconclusiva' até a fatura ser consultada na Enel. | `(vazio)` → `(vazio)`<br>`(vazio)` → `(vazio)`<br>`(vazio)` → `(vazio)` |
| Energia compensada maior que o consumo | 4 | 🟡 Revisão humana | Impossível pela regra (compensada nunca supera o consumo). Não sabemos qual dos dois está errado, então o caso fica 'Inconclusivo'. | `204` → `204`<br>`472` → `472`<br>`609` → `609` |
| Fatura duplicada (mesma UC, mês e valores) | 6 | 🔴 Descartado | Linha repetida na exportação. Mantê-la faria a fatura contar duas vezes nos indicadores. | `0009620650` → `0009620650`<br>`0012003626` → `0012003626`<br>`0082029073` → `0082029073` |
| Fatura de UC que não existe no cadastro | 3 | 🟡 Revisão humana | Sem cliente não há desconto nem a quem cobrar. A fatura é mantida e aparece na conciliação como 'Fatura sem cliente' para o comercial investigar (cliente não cadastrado ou UC digitada errada). | `0025965358` → `0025965358`<br>`0077224438` → `0077224438`<br>`0075600071` → `0075600071` |

### Aba `cobrancas_goener`

| Problema | Qtd | Ação | Por quê | Exemplos (original → tratado) |
|---|---|---|---|---|
| Valor em texto no formato brasileiro (R$ 1.234,56) | 113 | 🟢 Corrigido | Convertido para número. Vírgula = decimal, ponto = milhar. | `R$ 247,48` → `247.48`<br>`R$ 266,44` → `266.44`<br>`R$ 6.466,34` → `6466.34` |
| Data em formato DD/MM/AAAA misturado com AAAA-MM-DD | 889 | 🟢 Corrigido | Convertida para AAAA-MM-DD (premissa: padrão brasileiro). | `10/05/2026` → `2026-05-10`<br>`10/10/2026` → `2026-10-10`<br>`10/09/2026` → `2026-09-10` |
| Status com caixa despadronizada (PAGO, Pago, Em Aberto) | 278 | 🟢 Corrigido | Padronizado em minúsculas. | `EM ABERTO` → `em aberto`<br>`Pago` → `pago`<br>`PAGO` → `pago` |
| Valor do boleto negativo | 2 | 🟢 Corrigido | Boleto não tem valor negativo; tratado como sinal invertido (valor absoluto). A conciliação confirma se o valor absoluto bate com o esperado. | `-9315.83` → `9315.83`<br>`-380.69` → `380.69` |
| Status 'pago' sem data de pagamento | 3 | 🟡 Revisão humana | Mantido como pago (o status vem do sistema de cobrança), mas o financeiro precisa confirmar a baixa no banco. | `(vazio)` → `(vazio)`<br>`(vazio)` → `(vazio)`<br>`(vazio)` → `(vazio)` |
| Cobrança duplicada (mesmo cliente e mês) | 4 | 🟡 Revisão humana | Boleto é documento financeiro: não apagamos. Mantido o boleto pago (ou o mais antigo) como principal; este será classificado como 'Cobrança indevida' e o financeiro decide se cancela ou estorna. | `GB50710` → `principal: GB50130`<br>`GB50711` → `principal: GB50402`<br>`GB50709` → `principal: GB50516` |

## 4. Registros que precisam de revisão humana

Total: **21**

| aba | registro | problema | valor_original | valor_tratado |
|---|---|---|---|---|
| clientes | C1084 (linha 11) | Desconto contratado vazio | (vazio) | (vazio) |
| clientes | C1117 (linha 60) | Desconto contratado vazio | (vazio) | (vazio) |
| faturas_enel | UC 0091 377459 \| 05/2026 (linha 100) | Energia compensada vazia | (vazio) | (vazio) |
| faturas_enel | UC 0052632653 \| 2026-05 (linha 346) | Energia compensada vazia | (vazio) | (vazio) |
| faturas_enel | UC 0015 879094 \| 07/2026 (linha 398) | Energia compensada vazia | (vazio) | (vazio) |
| faturas_enel | UC 0028542226 \| 2026-04 (linha 474) | Energia compensada vazia | (vazio) | (vazio) |
| faturas_enel | UC 0074994695 \| 2026-08 (linha 626) | Energia compensada vazia | (vazio) | (vazio) |
| faturas_enel | UC 0087 911784 \| 2026-06 (linha 113) | Energia compensada maior que o consumo | 204 | 204 |
| faturas_enel | UC 0091908075 \| 2026-07 (linha 412) | Energia compensada maior que o consumo | 472 | 472 |
| faturas_enel | UC 002230655-5 \| 04/2026 (linha 445) | Energia compensada maior que o consumo | 609 | 609 |
| faturas_enel | UC 0036859307 \| ago/26 (linha 462) | Energia compensada maior que o consumo | 640 | 640 |
| cobrancas_goener | GB50484 (linha 206) | Status 'pago' sem data de pagamento | (vazio) | (vazio) |
| cobrancas_goener | GB50128 (linha 475) | Status 'pago' sem data de pagamento | (vazio) | (vazio) |
| cobrancas_goener | GB50295 (linha 496) | Status 'pago' sem data de pagamento | (vazio) | (vazio) |
| cobrancas_goener | GB50710 (linha 216) | Cobrança duplicada (mesmo cliente e mês) | GB50710 | principal: GB50130 |
| cobrancas_goener | GB50711 (linha 411) | Cobrança duplicada (mesmo cliente e mês) | GB50711 | principal: GB50402 |
| cobrancas_goener | GB50709 (linha 420) | Cobrança duplicada (mesmo cliente e mês) | GB50709 | principal: GB50516 |
| cobrancas_goener | GB50708 (linha 105) | Cobrança duplicada (mesmo cliente e mês) | GB50708 | principal: GB50683 |
| faturas_enel | UC 0025965358 \| 2026-07 (linha 315) | Fatura de UC que não existe no cadastro | 0025965358 | 0025965358 |
| faturas_enel | UC 0077224438 \| 2026-05 (linha 357) | Fatura de UC que não existe no cadastro | 0077224438 | 0077224438 |
| faturas_enel | UC 0075600071 \| 2026-07 (linha 682) | Fatura de UC que não existe no cadastro | 0075600071 | 0075600071 |

## 5. Registros descartados

Total: **10**

| aba | registro | problema | valor_original | valor_tratado |
|---|---|---|---|---|
| clientes | C1037 (linha 80) | Cliente duplicado | C1037 | mantida linha 48 |
| clientes | C1057 (linha 49) | Cliente duplicado | C1057 | mantida linha 46 |
| clientes | C1098 (linha 71) | Cliente duplicado | C1098 | mantida linha 17 |
| clientes | C1119 (linha 100) | Cliente duplicado | C1119 | mantida linha 72 |
| faturas_enel | UC 9620650 \| 2026-09 (linha 440) | Fatura duplicada (mesma UC, mês e valores) | 0009620650 | 0009620650 |
| faturas_enel | UC 0012003626 \| 2026-04 (linha 466) | Fatura duplicada (mesma UC, mês e valores) | 0012003626 | 0012003626 |
| faturas_enel | UC 0082029073 \| 2026-07 (linha 581) | Fatura duplicada (mesma UC, mês e valores) | 0082029073 | 0082029073 |
| faturas_enel | UC 0046 176955 \| 2026-04 (linha 624) | Fatura duplicada (mesma UC, mês e valores) | 0046176955 | 0046176955 |
| faturas_enel | UC 0046 147280 \| 04/2026 (linha 647) | Fatura duplicada (mesma UC, mês e valores) | 0046147280 | 0046147280 |
| faturas_enel | UC 0012457410 \| set/26 (linha 657) | Fatura duplicada (mesma UC, mês e valores) | 0012457410 | 0012457410 |

## 6. Erros de cobrança encontrados na conciliação (Etapa 2)

Cada par (cliente, mês) foi conferido pela regra **energia compensada × tarifa × (1 − desconto)**, com tolerância de R$ 0,05.

### Resumo por classificação

| Classificação | Casos | Impacto (R$) |
|---|---|---|
| OK | 666 | — |
| Cobrado a maior | 15 | R$ 6.058,61 |
| Cobrado a menor | 0 | R$ 0,00 |
| Fatura sem cobrança | 6 | R$ 10.978,82 |
| Cobrança indevida | 8 | R$ 12.217,97 |
| Inconclusivo | 20 | — |
| Fatura sem cliente cadastrado | 3 | — |
| Não cobrável (cliente cancelado) | 9 | — |

### Causas prováveis das divergências

A causa é encontrada recalculando o boleto com erros comuns (sem desconto, sobre o consumo total, vírgula deslocada) e vendo qual deles reproduz exatamente o valor cobrado.

| Causa provável | Casos | Diferença total |
|---|---|---|
| Vírgula deslocada: cobrado 10× o valor correto (erro de digitação) | 2 | R$ 4.453,56 |
| Cobrança calculada sobre o consumo total, não sobre a energia compensada | 5 | R$ 1.179,37 |
| Desconto contratado não aplicado (cobrado o valor cheio da energia) | 8 | R$ 425,68 |

### Todos os casos que não estão OK (61)

| classificacao | id_cliente | uc | mes_referencia | id_cobranca | valor_esperado | valor_cobrado | diferenca | motivo | causa_provavel |
|---|---|---|---|---|---|---|---|---|---|
| Cobrado a maior | C1001 | 0030345092 | 2026-06 | GB50003 | R$ 2.721,89 | R$ 3.285,40 | R$ 563,51 | Cobrado R$ 563.51 acima do esperado. | Cobrança calculada sobre o consumo total, não sobre a energia compensada |
| Cobrado a maior | C1005 | 0097356822 | 2026-07 | GB50028 | R$ 600,29 | R$ 647,97 | R$ 47,68 | Cobrado R$ 47.68 acima do esperado. | Cobrança calculada sobre o consumo total, não sobre a energia compensada |
| Cobrado a maior | C1008 | 0021513739 | 2026-05 | GB50044 | R$ 70,16 | R$ 87,69 | R$ 17,53 | Cobrado R$ 17.53 acima do esperado. | Desconto contratado não aplicado (cobrado o valor cheio da energia) |
| Cobrado a maior | C1027 | 0062124923 | 2026-07 | GB50158 | R$ 342,35 | R$ 435,36 | R$ 93,01 | Cobrado R$ 93.01 acima do esperado. | Cobrança calculada sobre o consumo total, não sobre a energia compensada |
| Cobrado a maior | C1039 | 0061152969 | 2026-07 | GB50230 | R$ 636,24 | R$ 727,69 | R$ 91,45 | Cobrado R$ 91.45 acima do esperado. | Cobrança calculada sobre o consumo total, não sobre a energia compensada |
| Cobrado a maior | C1046 | 0080865458 | 2026-06 | GB50269 | R$ 400,22 | R$ 4.002,20 | R$ 3.601,98 | Cobrado R$ 3601.98 acima do esperado. | Vírgula deslocada: cobrado 10× o valor correto (erro de digitação) |
| Cobrado a maior | C1053 | 0094616654 | 2026-05 | GB50308 | R$ 94,62 | R$ 946,20 | R$ 851,58 | Cobrado R$ 851.58 acima do esperado. | Vírgula deslocada: cobrado 10× o valor correto (erro de digitação) |
| Cobrado a maior | C1053 | 0094616654 | 2026-07 | GB50310 | R$ 114,12 | R$ 139,17 | R$ 25,05 | Cobrado R$ 25.05 acima do esperado. | Desconto contratado não aplicado (cobrado o valor cheio da energia) |
| Cobrado a maior | C1053 | 0094616654 | 2026-09 | GB50312 | R$ 74,02 | R$ 90,27 | R$ 16,25 | Cobrado R$ 16.25 acima do esperado. | Desconto contratado não aplicado (cobrado o valor cheio da energia) |
| Cobrado a maior | C1081 | 0088488142 | 2026-08 | GB50475 | R$ 2.947,42 | R$ 3.331,14 | R$ 383,72 | Cobrado R$ 383.72 acima do esperado. | Cobrança calculada sobre o consumo total, não sobre a energia compensada |
| Cobrado a maior | C1086 | 0042536077 | 2026-06 | GB50503 | R$ 439,96 | R$ 549,95 | R$ 109,99 | Cobrado R$ 109.99 acima do esperado. | Desconto contratado não aplicado (cobrado o valor cheio da energia) |
| Cobrado a maior | C1086 | 0042536077 | 2026-09 | GB50506 | R$ 306,53 | R$ 383,16 | R$ 76,63 | Cobrado R$ 76.63 acima do esperado. | Desconto contratado não aplicado (cobrado o valor cheio da energia) |
| Cobrado a maior | C1097 | 0011319387 | 2026-08 | GB50568 | R$ 309,20 | R$ 377,07 | R$ 67,87 | Cobrado R$ 67.87 acima do esperado. | Desconto contratado não aplicado (cobrado o valor cheio da energia) |
| Cobrado a maior | C1098 | 0029799154 | 2026-07 | GB50573 | R$ 240,74 | R$ 293,59 | R$ 52,85 | Cobrado R$ 52.85 acima do esperado. | Desconto contratado não aplicado (cobrado o valor cheio da energia) |
| Cobrado a maior | C1103 | 0006529005 | 2026-04 | GB50600 | R$ 238,05 | R$ 297,56 | R$ 59,51 | Cobrado R$ 59.51 acima do esperado. | Desconto contratado não aplicado (cobrado o valor cheio da energia) |
| Fatura sem cobrança | C1005 | 0097356822 | 2026-09 | — | R$ 415,77 | — | — | Enel registrou energia compensada, mas a Goener não emitiu boleto. | — |
| Fatura sem cobrança | C1021 | 0022810617 | 2026-06 | — | R$ 9.231,53 | — | — | Enel registrou energia compensada, mas a Goener não emitiu boleto. | — |
| Fatura sem cobrança | C1043 | 0075903294 | 2026-06 | — | R$ 276,48 | — | — | Enel registrou energia compensada, mas a Goener não emitiu boleto. | — |
| Fatura sem cobrança | C1048 | 0047702542 | 2026-09 | — | R$ 254,96 | — | — | Enel registrou energia compensada, mas a Goener não emitiu boleto. | — |
| Fatura sem cobrança | C1113 | 0072555103 | 2026-05 | — | R$ 462,93 | — | — | Enel registrou energia compensada, mas a Goener não emitiu boleto. | — |
| Fatura sem cobrança | C1120 | 0088735896 | 2026-07 | — | R$ 337,15 | — | — | Enel registrou energia compensada, mas a Goener não emitiu boleto. | — |
| Cobrança indevida | C1021 | 0022810617 | 2026-09 | GB50713 | R$ 0,00 | R$ 9.666,09 | R$ 9.666,09 | Cliente cancelado em 08/07/2026; mês começa depois do cancelamento. | — |
| Cobrança indevida | C1022 | 0031547349 | 2026-09 | GB50710 | R$ 0,00 | R$ 256,71 | R$ 256,71 | Boleto duplicado: já existe outro boleto para o mesmo cliente e mês. | — |
| Cobrança indevida | C1040 | 0034742830 | 2026-09 | GB50712 | R$ 0,00 | R$ 194,27 | R$ 194,27 | Cliente cancelado em 14/07/2026; mês começa depois do cancelamento. | — |
| Cobrança indevida | C1052 | 0036859307 | 2026-09 | GB50714 | R$ 0,00 | R$ 449,42 | R$ 449,42 | Cliente cancelado em 14/07/2026; mês começa depois do cancelamento. | — |
| Cobrança indevida | C1069 | 0097749495 | 2026-07 | GB50711 | R$ 0,00 | R$ 354,82 | R$ 354,82 | Boleto duplicado: já existe outro boleto para o mesmo cliente e mês. | — |
| Cobrança indevida | C1088 | 0054211150 | 2026-09 | GB50715 | R$ 0,00 | R$ 439,91 | R$ 439,91 | Cliente cancelado em 24/06/2026; mês começa depois do cancelamento. | — |
| Cobrança indevida | C1089 | 0001704803 | 2026-04 | GB50709 | R$ 0,00 | R$ 522,09 | R$ 522,09 | Boleto duplicado: já existe outro boleto para o mesmo cliente e mês. | — |
| Cobrança indevida | C1116 | 0001695441 | 2026-09 | GB50708 | R$ 0,00 | R$ 334,66 | R$ 334,66 | Boleto duplicado: já existe outro boleto para o mesmo cliente e mês. | — |
| Inconclusivo | C1012 | 0091377459 | 2026-05 | GB50068 | — | R$ 658,54 | — | Dados insuficientes ou contraditórios: energia compensada vazia. | — |
| Inconclusivo | C1025 | 0091908075 | 2026-07 | GB50146 | R$ 382,42 | R$ 311,93 | R$ -70,49 | Dados insuficientes ou contraditórios: compensada > consumo. | Pista: cobrança calculada sobre o consumo total, não sobre a energia compensada |
| Inconclusivo | C1036 | 0087911784 | 2026-06 | GB50211 | R$ 157,53 | R$ 108,88 | R$ -48,65 | Dados insuficientes ou contraditórios: compensada > consumo. | Pista: cobrança calculada sobre o consumo total, não sobre a energia compensada |
| Inconclusivo | C1058 | 0052632653 | 2026-05 | GB50338 | — | R$ 302,04 | — | Dados insuficientes ou contraditórios: energia compensada vazia. | — |
| Inconclusivo | C1065 | 0028542226 | 2026-04 | GB50379 | — | R$ 502,70 | — | Dados insuficientes ou contraditórios: energia compensada vazia. | — |
| Inconclusivo | C1082 | 0022306555 | 2026-04 | GB50477 | R$ 458,63 | R$ 361,48 | R$ -97,15 | Dados insuficientes ou contraditórios: compensada > consumo. | Pista: cobrança calculada sobre o consumo total, não sobre a energia compensada |
| Inconclusivo | C1084 | 0049563745 | 2026-04 | GB50489 | — | R$ 354,80 | — | Dados insuficientes ou contraditórios: desconto vazio. | — |
| Inconclusivo | C1084 | 0049563745 | 2026-05 | GB50490 | — | R$ 385,04 | — | Dados insuficientes ou contraditórios: desconto vazio. | — |
| Inconclusivo | C1084 | 0049563745 | 2026-06 | GB50491 | — | R$ 285,90 | — | Dados insuficientes ou contraditórios: desconto vazio. | — |
| Inconclusivo | C1084 | 0049563745 | 2026-07 | GB50492 | — | R$ 407,66 | — | Dados insuficientes ou contraditórios: desconto vazio. | — |
| Inconclusivo | C1084 | 0049563745 | 2026-08 | GB50493 | — | R$ 390,33 | — | Dados insuficientes ou contraditórios: desconto vazio. | — |
| Inconclusivo | C1084 | 0049563745 | 2026-09 | GB50494 | — | R$ 391,26 | — | Dados insuficientes ou contraditórios: desconto vazio. | — |
| Inconclusivo | C1090 | 0015879094 | 2026-07 | GB50525 | — | R$ 560,48 | — | Dados insuficientes ou contraditórios: energia compensada vazia. | — |
| Inconclusivo | C1101 | 0074994695 | 2026-08 | GB50592 | — | R$ 6.668,20 | — | Dados insuficientes ou contraditórios: energia compensada vazia. | — |
| Inconclusivo | C1117 | 0005877451 | 2026-04 | GB50684 | — | R$ 74,16 | — | Dados insuficientes ou contraditórios: desconto vazio. | — |
| Inconclusivo | C1117 | 0005877451 | 2026-05 | GB50685 | — | R$ 87,88 | — | Dados insuficientes ou contraditórios: desconto vazio. | — |
| Inconclusivo | C1117 | 0005877451 | 2026-06 | GB50686 | — | R$ 84,85 | — | Dados insuficientes ou contraditórios: desconto vazio. | — |
| Inconclusivo | C1117 | 0005877451 | 2026-07 | GB50687 | — | R$ 103,71 | — | Dados insuficientes ou contraditórios: desconto vazio. | — |
| Inconclusivo | C1117 | 0005877451 | 2026-08 | GB50688 | — | R$ 71,05 | — | Dados insuficientes ou contraditórios: desconto vazio. | — |
| Inconclusivo | C1117 | 0005877451 | 2026-09 | GB50689 | — | R$ 73,46 | — | Dados insuficientes ou contraditórios: desconto vazio. | — |
| Fatura sem cliente cadastrado | — | 0077224438 | 2026-05 | — | — | — | — | UC da fatura não existe no cadastro de clientes. | — |
| Fatura sem cliente cadastrado | — | 0025965358 | 2026-07 | — | — | — | — | UC da fatura não existe no cadastro de clientes. | — |
| Fatura sem cliente cadastrado | — | 0075600071 | 2026-07 | — | — | — | — | UC da fatura não existe no cadastro de clientes. | — |
| Não cobrável (cliente cancelado) | C1021 | 0022810617 | 2026-08 | — | R$ 0,00 | — | — | Correto não cobrar: mês posterior ao cancelamento. | — |
| Não cobrável (cliente cancelado) | C1040 | 0034742830 | 2026-08 | — | R$ 0,00 | — | — | Correto não cobrar: mês posterior ao cancelamento. | — |
| Não cobrável (cliente cancelado) | C1052 | 0036859307 | 2026-08 | — | R$ 0,00 | — | — | Correto não cobrar: mês posterior ao cancelamento. | — |
| Não cobrável (cliente cancelado) | C1065 | 0028542226 | 2026-06 | — | R$ 0,00 | — | — | Correto não cobrar: mês posterior ao cancelamento. | — |
| Não cobrável (cliente cancelado) | C1065 | 0028542226 | 2026-07 | — | R$ 0,00 | — | — | Correto não cobrar: mês posterior ao cancelamento. | — |
| Não cobrável (cliente cancelado) | C1065 | 0028542226 | 2026-08 | — | R$ 0,00 | — | — | Correto não cobrar: mês posterior ao cancelamento. | — |
| Não cobrável (cliente cancelado) | C1065 | 0028542226 | 2026-09 | — | R$ 0,00 | — | — | Correto não cobrar: mês posterior ao cancelamento. | — |
| Não cobrável (cliente cancelado) | C1088 | 0054211150 | 2026-07 | — | R$ 0,00 | — | — | Correto não cobrar: mês posterior ao cancelamento. | — |
| Não cobrável (cliente cancelado) | C1088 | 0054211150 | 2026-08 | — | R$ 0,00 | — | — | Correto não cobrar: mês posterior ao cancelamento. | — |

## 7. Log completo

As 2504 linhas do log (uma por valor tratado) estão em:

- `output/base_tratada.xlsx`, aba `log_inconsistencias`
- `output/powerbi/log_inconsistencias.csv`
