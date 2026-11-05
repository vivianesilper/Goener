-- =============================================================================
-- Case Goener · SQL Server (T-SQL) · 2/2: consultas de conferência
--
-- Mesma lógica de sql/consultas.sql (versão SQLite usada pelo Python), adaptada ao SQL Server:
--   * parâmetros com DECLARE (@tolerancia, @data_corte) em vez de :tolerancia/:data_corte;
--   * textos com acento como N'...' (Unicode);
--   * NULLIF nas divisões (o SQL Server dá erro ao dividir por zero; o SQLite devolve NULL).
--
-- Rode depois do 01_carga.sql:
--   sqlcmd -S localhost -E -C -d CaseGoener -i sql\sqlserver\02_consultas.sql
--
-- Resultados esperados (iguais ao Python): 15 boletos com valor errado, 4 cobranças após o
-- cancelamento, R$ 10.978,82 de receita perdida e inadimplência de 12,78%.
-- =============================================================================
SET NOCOUNT ON;

DECLARE @tolerancia FLOAT = 0.05;          -- divergência de até R$ 0,05 = arredondamento
DECLARE @data_corte DATE  = '2026-10-15';  -- vencimento antes disso e sem pagamento = vencida


-- name: divergencias_de_valor
-- Recalcula a regra de negócio direto das tabelas tratadas e lista os boletos com valor
-- diferente do esperado (fora da tolerância). Ignora boletos duplicados, meses após o
-- cancelamento e faturas marcadas para revisão (essas são tratadas como outras classificações).
SELECT
    b.id_cobranca,
    b.id_cliente,
    b.mes_referencia,
    CAST(ROUND(f.energia_compensada_kwh * f.tarifa_kwh * (1 - c.desconto_contratado), 2) AS DECIMAL(12, 2)) AS valor_esperado,
    CAST(b.valor_cobrado AS DECIMAL(12, 2)) AS valor_cobrado,
    CAST(ROUND(b.valor_cobrado - f.energia_compensada_kwh * f.tarifa_kwh * (1 - c.desconto_contratado), 2) AS DECIMAL(12, 2)) AS diferenca
FROM dbo.cobrancas AS b
JOIN dbo.clientes  AS c ON c.id_cliente = b.id_cliente
JOIN dbo.faturas   AS f ON f.id_cliente = b.id_cliente AND f.mes_referencia = b.mes_referencia
WHERE b.cobranca_duplicada = 0
  AND f.flag_revisao = 0
  AND c.desconto_contratado IS NOT NULL
  AND (c.data_cancelamento IS NULL OR b.mes_referencia <= c.data_cancelamento)
  AND ABS(b.valor_cobrado - ROUND(f.energia_compensada_kwh * f.tarifa_kwh * (1 - c.desconto_contratado), 2)) > @tolerancia
ORDER BY diferenca DESC;


-- name: cobrancas_apos_cancelamento
-- Regra: cliente cancelado não pode ser cobrado por mês que começa depois do cancelamento.
SELECT b.id_cobranca, b.id_cliente, c.nome, c.data_cancelamento, b.mes_referencia,
       CAST(b.valor_cobrado AS DECIMAL(12, 2)) AS valor_cobrado,
       b.status_pagamento
FROM dbo.cobrancas AS b
JOIN dbo.clientes  AS c ON c.id_cliente = b.id_cliente
WHERE c.status = 'cancelado'
  AND b.mes_referencia > c.data_cancelamento
ORDER BY b.valor_cobrado DESC;


-- name: faturas_sem_cobranca
-- Faturas de clientes cadastrados, em meses cobráveis, sem nenhum boleto (receita perdida).
SELECT f.id_cliente, f.uc, f.mes_referencia,
       CAST(ROUND(f.energia_compensada_kwh * f.tarifa_kwh * (1 - c.desconto_contratado), 2) AS DECIMAL(12, 2)) AS receita_perdida
FROM dbo.faturas  AS f
JOIN dbo.clientes AS c ON c.id_cliente = f.id_cliente
LEFT JOIN dbo.cobrancas AS b ON b.id_cliente = f.id_cliente AND b.mes_referencia = f.mes_referencia
WHERE b.id_cobranca IS NULL
  AND (c.data_cancelamento IS NULL OR f.mes_referencia <= c.data_cancelamento)
ORDER BY receita_perdida DESC;


-- name: indicadores_mensais
-- Indicadores da Etapa 3, mês a mês, a partir da tabela de conciliação.
SELECT
    mes_referencia,
    CAST(SUM(valor_a_maior) AS DECIMAL(12, 2))   AS valor_a_maior,
    CAST(SUM(receita_perdida) AS DECIMAL(12, 2)) AS receita_perdida,
    CAST(SUM(valor_indevido) AS DECIMAL(12, 2))  AS valor_indevido,
    CAST(SUM(economia_real) AS DECIMAL(12, 2))   AS economia_real,
    CAST(ROUND(
        SUM(CASE WHEN vencida_nao_paga = 1 AND id_cobranca IS NOT NULL
                  AND classificacao <> N'Cobrança indevida' THEN valor_cobrado ELSE 0 END)
      / NULLIF(SUM(CASE WHEN vencida = 1 AND id_cobranca IS NOT NULL
                  AND classificacao <> N'Cobrança indevida' THEN valor_cobrado ELSE 0 END), 0)
    , 4) AS DECIMAL(6, 4)) AS inadimplencia
FROM dbo.conciliacao
GROUP BY mes_referencia
ORDER BY mes_referencia;


-- name: inadimplencia_total
-- Valor vencido e não pago / total vencido, na data de corte (sem cobranças indevidas).
SELECT
    CAST(SUM(CASE WHEN data_vencimento < @data_corte THEN valor_cobrado ELSE 0 END) AS DECIMAL(12, 2)) AS total_vencido,
    CAST(SUM(CASE WHEN data_vencimento < @data_corte AND status_pagamento <> 'pago'
                   THEN valor_cobrado ELSE 0 END) AS DECIMAL(12, 2)) AS vencido_nao_pago,
    CAST(ROUND(SUM(CASE WHEN data_vencimento < @data_corte AND status_pagamento <> 'pago'
                   THEN valor_cobrado ELSE 0 END)
        / NULLIF(SUM(CASE WHEN data_vencimento < @data_corte THEN valor_cobrado ELSE 0 END), 0), 4) AS DECIMAL(6, 4)) AS inadimplencia
FROM dbo.conciliacao
WHERE id_cobranca IS NOT NULL
  AND classificacao <> N'Cobrança indevida';


-- name: resumo_por_classificacao
SELECT classificacao,
       COUNT(*) AS casos,
       CAST(SUM(valor_a_maior + valor_a_menor + receita_perdida + valor_indevido) AS DECIMAL(12, 2)) AS impacto
FROM dbo.conciliacao
GROUP BY classificacao
ORDER BY casos DESC;
