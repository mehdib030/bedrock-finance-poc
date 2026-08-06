CREATE TABLE IF NOT EXISTS analytics.company_financial_metrics
(
    cik                 VARCHAR(10)     NOT NULL,
    company_name        VARCHAR(256)    NOT NULL,
    sic                 VARCHAR(10),
    form                VARCHAR(10)     NOT NULL,
    fiscal_year         SMALLINT        NOT NULL,
    fiscal_period       VARCHAR(10)     NOT NULL,
    period_end          DATE            NOT NULL,
    filing_date         DATE            NOT NULL,
    accession_number    VARCHAR(32)     NOT NULL,
    metric_name         VARCHAR(64)     NOT NULL,
    metric_type         VARCHAR(32)     NOT NULL,
    source_tag          VARCHAR(128)    NOT NULL,
    duration_quarters   SMALLINT,
    metric_value        DECIMAL(38, 2)  NOT NULL,
    unit                VARCHAR(16)     NOT NULL
);