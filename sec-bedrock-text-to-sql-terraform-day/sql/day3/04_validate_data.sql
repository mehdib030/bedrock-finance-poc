SELECT
    COUNT(*) AS row_count,
    COUNT(DISTINCT cik) AS company_count,
    COUNT(DISTINCT fiscal_year) AS fiscal_year_count,
    COUNT(DISTINCT metric_name) AS metric_count,
    MIN(fiscal_year) AS first_fiscal_year,
    MAX(fiscal_year) AS last_fiscal_year
FROM analytics.company_financial_metrics;