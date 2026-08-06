CREATE TABLE IF NOT EXISTS public.company_financial_metrics (
    cik BIGINT,
    company_name VARCHAR(250),
    sic INTEGER,
    filing_type VARCHAR(10),
    fiscal_year INTEGER,
    fiscal_period VARCHAR(10),
    period_end DATE,
    filing_date DATE,
    metric_name VARCHAR(100),
    metric_value DECIMAL(38, 4),
    unit VARCHAR(20),
    duration_quarters INTEGER,
    source_tag VARCHAR(250),
    accession_number VARCHAR(50)
)
DISTSTYLE AUTO
SORTKEY (fiscal_year, company_name, metric_name);

CREATE OR REPLACE VIEW public.bedrock_basic_financial_metrics AS
SELECT
    company_name,
    sic,
    filing_type,
    fiscal_year,
    fiscal_period,
    period_end,
    metric_name,
    metric_value,
    unit,
    duration_quarters
FROM public.company_financial_metrics;

-- Run COPY after normalized Parquet files exist. Replace placeholders if running manually:
-- COPY public.company_financial_metrics
-- FROM '${NORMALIZED_S3_URI}'
-- IAM_ROLE '${REDSHIFT_IAM_ROLE_ARN}'
-- FORMAT AS PARQUET;
