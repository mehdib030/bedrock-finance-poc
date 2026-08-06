SELECT
    fiscal_year,
    MAX(CASE WHEN metric_name = 'revenue' THEN metric_value END) AS revenue,
    MAX(CASE WHEN metric_name = 'net_income' THEN metric_value END) AS net_income,
    MAX(CASE WHEN metric_name = 'operating_cash_flow' THEN metric_value END) AS operating_cash_flow,
    MAX(CASE WHEN metric_name = 'total_assets' THEN metric_value END) AS total_assets,
    MAX(CASE WHEN metric_name = 'total_liabilities' THEN metric_value END) AS total_liabilities
FROM public.company_financial_metrics
WHERE company_name = :company_name
  AND fiscal_year BETWEEN :start_year AND :end_year
  AND filing_type = '10-K'
GROUP BY fiscal_year
ORDER BY fiscal_year;
