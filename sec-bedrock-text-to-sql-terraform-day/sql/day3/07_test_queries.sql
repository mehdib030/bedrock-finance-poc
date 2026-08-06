SELECT
    company_name,
    fiscal_year,
    metric_value AS revenue,
    unit
FROM bedrock.v_company_financial_metrics
WHERE company_name ILIKE '%Apple%'
  AND metric_name = 'revenue'
ORDER BY fiscal_year;

SELECT
    company_name,
    metric_value AS net_income,
    unit
FROM bedrock.v_company_financial_metrics
WHERE fiscal_year = 2024
  AND metric_name = 'net_income'
ORDER BY net_income DESC;

SELECT
    company_name,
    metric_name,
    metric_value,
    unit
FROM bedrock.v_company_financial_metrics
WHERE fiscal_year = 2024
  AND metric_name IN ('revenue', 'net_income')
ORDER BY company_name, metric_name;

WITH revenue_by_year AS
(
    SELECT
        company_name,
        fiscal_year,
        metric_value AS revenue
    FROM bedrock.v_company_financial_metrics
    WHERE metric_name = 'revenue'
),
revenue_with_previous_year AS
(
    SELECT
        company_name,
        fiscal_year,
        revenue,
        LAG(revenue) OVER
        (
            PARTITION BY company_name
            ORDER BY fiscal_year
        ) AS previous_year_revenue
    FROM revenue_by_year
)
SELECT
    company_name,
    fiscal_year,
    revenue,
    previous_year_revenue,
    ROUND(
        100.0 * (revenue - previous_year_revenue)
        / NULLIF(previous_year_revenue, 0),
        2
    ) AS revenue_growth_percent
FROM revenue_with_previous_year
WHERE previous_year_revenue IS NOT NULL
ORDER BY fiscal_year, revenue_growth_percent DESC;