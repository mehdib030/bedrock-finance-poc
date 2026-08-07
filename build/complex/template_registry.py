TEMPLATES = {
    "revenue_cagr": {
        "description": (
            "Calculate revenue compound annual growth rate "
            "for one company between two fiscal years."
        ),
        "required_parameters": [
            "company_name",
            "start_year",
            "end_year",
        ],
        "sql": """
WITH revenue_endpoints AS (
    SELECT
        MAX(
            CASE
                WHEN fiscal_year = CAST(:start_year AS INTEGER)
                THEN metric_value
            END
        ) AS start_value,
        MAX(
            CASE
                WHEN fiscal_year = CAST(:end_year AS INTEGER)
                THEN metric_value
            END
        ) AS end_value
    FROM analytics.company_financial_metrics
    WHERE UPPER(company_name) = UPPER(:company_name)
      AND LOWER(metric_name) = 'revenue'
      AND fiscal_year IN (
          CAST(:start_year AS INTEGER),
          CAST(:end_year AS INTEGER)
      )
)
SELECT
    UPPER(:company_name) AS company_name,
    CAST(:start_year AS INTEGER) AS start_year,
    CAST(:end_year AS INTEGER) AS end_year,
    start_value,
    end_value,
    CASE
        WHEN start_value > 0
         AND end_value IS NOT NULL
         AND CAST(:end_year AS INTEGER)
             > CAST(:start_year AS INTEGER)
        THEN
            POWER(
                end_value / start_value,
                1.0 / (
                    CAST(:end_year AS INTEGER)
                    - CAST(:start_year AS INTEGER)
                )
            ) - 1
        ELSE NULL
    END AS revenue_cagr
FROM revenue_endpoints
""".strip(),
    },
}


def get_template(template_id: str) -> dict:
    template = TEMPLATES.get(template_id)

    if not template:
        raise ValueError(
            f"Unsupported complex-query template: {template_id}"
        )

    return template 