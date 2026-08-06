WITH target AS (
    SELECT MAX(sic) AS sic
    FROM public.company_financial_metrics
    WHERE company_name = :company_name
),
peer_metrics AS (
    SELECT
        company_name,
        MAX(metric_value) AS revenue
    FROM public.company_financial_metrics
    WHERE sic = (SELECT sic FROM target)
      AND fiscal_year = :fiscal_year
      AND filing_type = '10-K'
      AND duration_quarters = 4
      AND metric_name = 'revenue'
    GROUP BY company_name
)
SELECT
    company_name,
    revenue,
    PERCENT_RANK() OVER (ORDER BY revenue) AS revenue_percentile
FROM peer_metrics
ORDER BY revenue DESC;
