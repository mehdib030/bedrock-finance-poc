WITH annual_metrics AS (
    SELECT
        company_name,
        fiscal_year,
        MAX(CASE WHEN metric_name = 'revenue' THEN metric_value END) AS revenue,
        MAX(CASE WHEN metric_name = 'net_income' THEN metric_value END) AS net_income,
        MAX(CASE WHEN metric_name = 'operating_cash_flow' THEN metric_value END) AS operating_cash_flow
    FROM public.company_financial_metrics
    WHERE company_name IN ({{COMPANY_PLACEHOLDERS}})
      AND filing_type = '10-K'
      AND duration_quarters = 4
      AND fiscal_year BETWEEN :start_year AND :end_year
      AND metric_name IN ('revenue', 'net_income', 'operating_cash_flow')
    GROUP BY company_name, fiscal_year
),
trends AS (
    SELECT
        company_name,
        fiscal_year,
        revenue,
        net_income,
        operating_cash_flow,
        revenue / NULLIF(LAG(revenue) OVER (PARTITION BY company_name ORDER BY fiscal_year), 0) - 1 AS revenue_growth,
        operating_cash_flow / NULLIF(LAG(operating_cash_flow) OVER (PARTITION BY company_name ORDER BY fiscal_year), 0) - 1 AS cash_flow_growth,
        net_income / NULLIF(revenue, 0) AS net_income_margin
    FROM annual_metrics
)
SELECT
    company_name,
    AVG(revenue_growth) AS avg_revenue_growth,
    AVG(cash_flow_growth) AS avg_cash_flow_growth,
    AVG(net_income_margin) AS avg_net_income_margin
FROM trends
GROUP BY company_name
ORDER BY company_name;
