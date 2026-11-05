-- =============================================================================
-- Case Goener · SQL Server (T-SQL) · 1/2: cria as tabelas e carrega os CSVs tratados
--
-- Testado no SQL Server 2025 Express. Os CSVs vêm de output/powerbi/ (gerados pelo notebook).
--
-- Como rodar (PowerShell, na raiz do projeto; ajuste o servidor, ex.: localhost\SQLEXPRESS):
--   sqlcmd -S localhost -E -C -Q "IF DB_ID('CaseGoener') IS NULL CREATE DATABASE CaseGoener"
--   $env:PASTA_CSV = "C:\caminho\Case_Goener\output\powerbi"
--   sqlcmd -S localhost -E -C -d CaseGoener -i sql\sqlserver\01_carga.sql
--   sqlcmd -S localhost -E -C -d CaseGoener -i sql\sqlserver\02_consultas.sql
-- (o sqlcmd lê variáveis de ambiente; isso evita o problema do -v com espaços no caminho)
--
-- No SSMS: ative Consulta > Modo SQLCMD e descomente/ajuste a linha :setvar abaixo.
-- Os arquivos estão em UTF-8 com BOM: sem isso o sqlcmd lê "Cobrança" errado e os filtros falham.
-- Atenção: BULK INSERT é executado pelo serviço do SQL Server, então a conta do serviço
-- (ex.: NT Service\MSSQL$SQLEXPRESS) precisa ter permissão de leitura na pasta dos CSVs.
-- =============================================================================
-- :setvar PASTA_CSV "C:\caminho\Case_Goener\output\powerbi"

SET NOCOUNT ON;

DROP TABLE IF EXISTS dbo.conciliacao, dbo.cobrancas, dbo.faturas, dbo.clientes;

-- UC, CPF/CNPJ e ids são TEXTO: preservam os zeros à esquerda.
-- Números com casas fixas (DECIMAL), para todos aparecerem no mesmo formato:
--   desconto com 2 casas (0.15, 0.20), tarifa com 4 (0.9184), kWh e valores em R$ com 2.
CREATE TABLE dbo.clientes (
    linha_origem        INT,
    id_cliente          VARCHAR(10)   NOT NULL PRIMARY KEY,
    nome                NVARCHAR(120),
    cpf_cnpj            VARCHAR(14),
    tipo_documento      VARCHAR(4),
    uc                  CHAR(10),
    cidade              NVARCHAR(60),
    desconto_contratado DECIMAL(4, 2),
    data_adesao         DATE,
    status              VARCHAR(10),
    data_cancelamento   DATE,
    flag_revisao        VARCHAR(6),  -- True/False no CSV; vira BIT após a carga
    motivo_revisao      NVARCHAR(400)
);

CREATE TABLE dbo.faturas (
    linha_origem           INT,
    uc                     CHAR(10),
    id_cliente             VARCHAR(10),
    mes_referencia         DATE,
    consumo_kwh            DECIMAL(12, 2),
    energia_compensada_kwh DECIMAL(12, 2),
    tarifa_kwh             DECIMAL(8, 4),
    flag_revisao           VARCHAR(6),  -- True/False no CSV; vira BIT após a carga
    motivo_revisao         NVARCHAR(400)
);

CREATE TABLE dbo.cobrancas (
    linha_origem       INT,
    id_cobranca        VARCHAR(10),
    id_cliente         VARCHAR(10),
    mes_referencia     DATE,
    valor_cobrado      DECIMAL(12, 2),
    data_vencimento    DATE,
    data_pagamento     DATE,
    status_pagamento   VARCHAR(12),
    flag_revisao       VARCHAR(6),  -- True/False no CSV; vira BIT após a carga
    motivo_revisao     NVARCHAR(400),
    cobranca_duplicada VARCHAR(6)  -- True/False no CSV; vira BIT após a carga
);

CREATE TABLE dbo.conciliacao (
    classificacao          NVARCHAR(40),
    motivo                 NVARCHAR(400),
    causa_provavel         NVARCHAR(200),
    id_cliente             VARCHAR(10),
    nome                   NVARCHAR(120),
    cidade                 NVARCHAR(60),
    status_cliente         VARCHAR(10),
    data_cancelamento      DATE,
    uc                     CHAR(10),
    mes_referencia         DATE,
    consumo_kwh            DECIMAL(12, 2),
    energia_compensada_kwh DECIMAL(12, 2),
    tarifa_kwh             DECIMAL(8, 4),
    desconto_contratado    DECIMAL(4, 2),
    valor_esperado         DECIMAL(12, 2),
    id_cobranca            VARCHAR(10),
    valor_cobrado          DECIMAL(12, 2),
    diferenca              DECIMAL(12, 2),
    valor_a_maior          DECIMAL(12, 2),
    valor_a_menor          DECIMAL(12, 2),
    receita_perdida        DECIMAL(12, 2),
    valor_indevido         DECIMAL(12, 2),
    economia_contratada    DECIMAL(12, 2),
    economia_real          DECIMAL(12, 2),
    data_vencimento        DATE,
    data_pagamento         DATE,
    status_pagamento       VARCHAR(12),
    vencida                VARCHAR(6),  -- True/False no CSV; vira BIT após a carga
    vencida_nao_paga       VARCHAR(6),  -- True/False no CSV; vira BIT após a carga
    origem                 NVARCHAR(30)
);

-- CSV em UTF-8, com cabeçalho e textos entre aspas quando têm vírgula.
BULK INSERT dbo.clientes    FROM '$(PASTA_CSV)\dim_clientes.csv'
    WITH (FORMAT = 'CSV', CODEPAGE = '65001', FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '0x0a');
BULK INSERT dbo.faturas     FROM '$(PASTA_CSV)\fato_faturas.csv'
    WITH (FORMAT = 'CSV', CODEPAGE = '65001', FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '0x0a');
BULK INSERT dbo.cobrancas   FROM '$(PASTA_CSV)\fato_cobrancas.csv'
    WITH (FORMAT = 'CSV', CODEPAGE = '65001', FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '0x0a');
BULK INSERT dbo.conciliacao FROM '$(PASTA_CSV)\fato_conciliacao.csv'
    WITH (FORMAT = 'CSV', CODEPAGE = '65001', FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '0x0a');

-- O CSV traz booleanos como True/False, que o BULK INSERT não converte para BIT.
-- Converte aqui (e remove um eventual CR, CHAR(13), de fim de linha do Windows).
DECLARE @colunas TABLE (tabela SYSNAME, coluna SYSNAME);
INSERT INTO @colunas VALUES ('clientes', 'flag_revisao'), ('faturas', 'flag_revisao'),
    ('cobrancas', 'flag_revisao'), ('cobrancas', 'cobranca_duplicada'),
    ('conciliacao', 'vencida'), ('conciliacao', 'vencida_nao_paga');
DECLARE @sql NVARCHAR(MAX) = N'';
SELECT @sql += N'UPDATE dbo.' + QUOTENAME(tabela) + N' SET ' + QUOTENAME(coluna)
             + N' = CASE WHEN ' + QUOTENAME(coluna) + N' LIKE ''True%'' THEN ''1'' WHEN '
             + QUOTENAME(coluna) + N' LIKE ''False%'' THEN ''0'' END; '
             + N'ALTER TABLE dbo.' + QUOTENAME(tabela) + N' ALTER COLUMN ' + QUOTENAME(coluna) + N' BIT; '
FROM @colunas;
EXEC sys.sp_executesql @sql;

-- Remove o CR, CHAR(13), que sobra na última coluna quando o CSV tem quebra de linha do Windows (CRLF).
UPDATE dbo.clientes    SET motivo_revisao = NULLIF(REPLACE(motivo_revisao, CHAR(13), ''), '');
UPDATE dbo.faturas     SET motivo_revisao = NULLIF(REPLACE(motivo_revisao, CHAR(13), ''), '');
UPDATE dbo.conciliacao SET origem         = REPLACE(origem, CHAR(13), '');

-- Conferência da carga: 120 clientes, 723 faturas, 709 cobranças, 727 casos conciliados.
SELECT 'clientes' AS tabela, COUNT(*) AS linhas FROM dbo.clientes
UNION ALL SELECT 'faturas',     COUNT(*) FROM dbo.faturas
UNION ALL SELECT 'cobrancas',   COUNT(*) FROM dbo.cobrancas
UNION ALL SELECT 'conciliacao', COUNT(*) FROM dbo.conciliacao;
