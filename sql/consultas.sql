-- =============================================================================
-- Consultas SQL do case Goener, no dialeto do SQLite (usado pelo Python em src/consultas_sql.py).
-- Versão para SQL Server (T-SQL), testada e com os mesmos resultados: sql/sqlserver/.
--
-- Servem como CONFERÊNCIA INDEPENDENTE: recalculam com SQL o que o Python calculou.
-- Se os resultados batem, a lógica está certa nas duas linguagens.
--
-- Parâmetros (nada fixo no código): :tolerancia, :data_corte
-- Cada consulta começa com "-- name: <nome>" para ser carregada pelo Python.
-- =============================================================================


-- name: divergencias_de_valor
-- Recalcula a regra de negócio direto das tabelas tratadas e lista os boletos com valor
-- diferente do esperado (fora da tolerância). Ignora boletos duplicados, meses após o
-- cancelamento e faturas marcadas para revisão (essas são tratadas como outras classificações).
SELECT
    b.id_cobranca,
    b.id_cliente,
    b.mes_referencia,
    ROUND(f.energia_compensada_kwh * f.tarifa_kwh * (1 - c.desconto_contratado), 2) AS valor_esperado,
    b.valor_cobrado,
    ROUND(b.valor_cobrado - f.energia_compensada_kwh * f.tarifa_kwh * (1 - c.desconto_contratado), 2) AS diferenca
FROM cobrancas AS b
JOIN clientes  AS c ON c.id_cliente = b.id_cliente
JOIN faturas   AS f ON f.id_cliente = b.id_cliente AND f.mes_referencia = b.mes_referencia
WHERE b.cobranca_duplicada = 0
  AND f.flag_revisao = 0
  AND c.desconto_contratado IS NOT NULL
  AND (c.data_cancelamento IS NULL OR b.mes_referencia <= c.data_cancelamento)
  AND ABS(b.valor_cobrado - ROUND(f.energia_compensada_kwh * f.tarifa_kwh * (1 - c.desconto_contratado), 2)) > :tolerancia
ORDER BY diferenca DESC;


-- name: cobrancas_apos_cancelamento
-- Regra: cliente cancelado não pode ser cobrado por mês que começa depois do cancelamento.
SELECT b.id_cobranca, b.id_cliente, c.nome, c.data_cancelamento, b.mes_referencia, b.valor_cobrado,
       b.status_pagamento
FROM cobrancas AS b
JOIN clientes  AS c ON c.id_cliente = b.id_cliente
WHERE c.status = 'cancelado'
  AND b.mes_referencia > c.data_cancelamento
ORDER BY b.valor_cobrado DESC;


-- name: faturas_sem_cobranca
-- Faturas de clientes cadastrados, em meses cobráveis, sem nenhum boleto (receita perdida).
SELECT f.id_cliente, f.uc, f.mes_referencia,
       ROUND(f.energia_compensada_kwh * f.tarifa_kwh * (1 - c.desconto_contratado), 2) AS receita_perdida
FROM faturas  AS f
JOIN clientes AS c ON c.id_cliente = f.id_cliente
LEFT JOIN cobrancas AS b ON b.id_cliente = f.id_cliente AND b.mes_referencia = f.mes_referencia
WHERE b.id_cobranca IS NULL
  AND (c.data_cancelamento IS NULL OR f.mes_referencia <= c.data_cancelamento)
ORDER BY receita_perdida DESC;


-- name: indicadores_mensais
-- Indicadores da Etapa 3, mês a mês, a partir da tabela de conciliação.
SELECT
    mes_referencia,
    ROUND(SUM(valor_a_maior), 2)   AS valor_a_maior,
    ROUND(SUM(receita_perdida), 2) AS receita_perdida,
    ROUND(SUM(valor_indevido), 2)  AS valor_indevido,
    ROUND(SUM(economia_real), 2)   AS economia_real,
    ROUND(
        SUM(CASE WHEN vencida_nao_paga = 1 AND id_cobranca IS NOT NULL
                  AND classificacao <> 'Cobrança indevida' THEN valor_cobrado ELSE 0 END)
      / NULLIF(SUM(CASE WHEN vencida = 1 AND id_cobranca IS NOT NULL
                  AND classificacao <> 'Cobrança indevida' THEN valor_cobrado ELSE 0 END), 0)
    , 4) AS inadimplencia
FROM conciliacao
GROUP BY mes_referencia
ORDER BY mes_referencia;


-- name: inadimplencia_total
-- Valor vencido e não pago / total vencido, na data de corte (sem cobranças indevidas).
SELECT
    ROUND(SUM(CASE WHEN data_vencimento < :data_corte THEN valor_cobrado ELSE 0 END), 2) AS total_vencido,
    ROUND(SUM(CASE WHEN data_vencimento < :data_corte AND status_pagamento <> 'pago'
                   THEN valor_cobrado ELSE 0 END), 2) AS vencido_nao_pago,
    ROUND(SUM(CASE WHEN data_vencimento < :data_corte AND status_pagamento <> 'pago'
                   THEN valor_cobrado ELSE 0 END)
        / SUM(CASE WHEN data_vencimento < :data_corte THEN valor_cobrado ELSE 0 END), 4) AS inadimplencia
FROM conciliacao
WHERE id_cobranca IS NOT NULL
  AND classificacao <> 'Cobrança indevida';


-- name: resumo_por_classificacao
SELECT classificacao,
       COUNT(*) AS casos,
       ROUND(SUM(valor_a_maior + valor_a_menor + receita_perdida + valor_indevido), 2) AS impacto
FROM conciliacao
GROUP BY classificacao
ORDER BY casos DESC;
