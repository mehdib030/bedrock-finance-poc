from __future__ import annotations

import argparse
import json
from pathlib import Path

import boto3
import duckdb

QUARTERS = [
    "2024q1", "2024q2", "2024q3", "2024q4",
    "2025q1", "2025q2", "2025q3", "2025q4", "2026q1",
]


def sql_list(values: list[str]) -> str:
    return ",".join("'" + v.replace("'", "''") + "'" for v in values)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--bucket", required=True)
    p.add_argument("--work-dir", default="work")
    p.add_argument("--output-dir", default="output")
    p.add_argument("--companies", default="config/companies.csv")
    p.add_argument("--metric-map", default="config/metric_map.csv")
    p.add_argument("--start-year", type=int, default=2022)
    p.add_argument("--end-year", type=int, default=2025)
    args = p.parse_args()

    work = Path(args.work_dir).resolve()
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    db_path = output / "normalize.duckdb"
    parquet_path = output / "company_financial_metrics.parquet"
    csv_path = output / "company_financial_metrics.csv"
    report_path = output / "quality_report.json"

    con = duckdb.connect(str(db_path))
    con.execute("PRAGMA threads=4")
    con.execute("CREATE OR REPLACE TABLE companies AS SELECT CAST(cik AS BIGINT) cik, company_alias FROM read_csv_auto(?, header=true)", [str(Path(args.companies).resolve())])
    con.execute("CREATE OR REPLACE TABLE metric_map AS SELECT metric_name, tag, CAST(priority AS INTEGER) priority, metric_type FROM read_csv_auto(?, header=true)", [str(Path(args.metric_map).resolve())])
    con.execute("""
    CREATE OR REPLACE TABLE submissions (
        adsh VARCHAR,
        cik BIGINT,
        "name" VARCHAR,
        sic INTEGER,
        form VARCHAR,
        period DATE,
        fy INTEGER,
        fp VARCHAR,
        filed DATE,
        prevrpt INTEGER
    )
    """)
    con.execute("""
    CREATE OR REPLACE TABLE facts (
        adsh VARCHAR,
        tag VARCHAR,
        ddate DATE,
        qtrs INTEGER,
        uom VARCHAR,
        segments VARCHAR,
        coreg VARCHAR,
        "value" DECIMAL(38,4)
    )
    """)
    for quarter in QUARTERS:
        sub = work / quarter / "sub.txt"
        num = work / quarter / "num.txt"
        if not sub.exists() or not num.exists():
            raise FileNotFoundError(f"Missing extracted files for {quarter}; run download_extract_upload.py first")

        con.execute("""
            INSERT INTO submissions
            SELECT
                s.adsh,
                TRY_CAST(s.cik AS BIGINT),
                s.name,
                TRY_CAST(s.sic AS INTEGER),
                s.form,
                TRY_STRPTIME(s.period, '%Y%m%d')::DATE,
                TRY_CAST(s.fy AS INTEGER),
                s.fp,
                TRY_STRPTIME(s.filed, '%Y%m%d')::DATE,
                TRY_CAST(s.prevrpt AS INTEGER)
            FROM read_csv_auto(?, delim='\t', header=true, all_varchar=true, quote='', ignore_errors=true) s
            JOIN companies c ON TRY_CAST(s.cik AS BIGINT) = c.cik
            WHERE s.form IN ('10-K', '10-K/A')
              AND TRY_CAST(s.fy AS INTEGER) BETWEEN ? AND ?
        """, [str(sub), args.start_year, args.end_year])

        con.execute("""
            INSERT INTO facts
            SELECT
                n.adsh,
                n.tag,
                TRY_STRPTIME(n.ddate, '%Y%m%d')::DATE,
                TRY_CAST(n.qtrs AS INTEGER),
                n.uom,
                n.segments,
                n.coreg,
                TRY_CAST(n.value AS DECIMAL(38,4))
            FROM read_csv_auto(?, delim='\t', header=true, all_varchar=true, quote='', ignore_errors=true) n
            JOIN metric_map m ON n.tag = m.tag
            JOIN submissions s ON n.adsh = s.adsh
            WHERE n.uom = 'USD'
              AND (n.coreg IS NULL OR TRIM(n.coreg) = '')
              AND (n.segments IS NULL OR TRIM(n.segments) = '')
              AND TRY_CAST(n.value AS DECIMAL(38,4)) IS NOT NULL
        """, [str(num)])

    con.execute("""
        CREATE OR REPLACE TABLE selected_filings AS
        SELECT * EXCLUDE(rn)
        FROM (
            SELECT *, ROW_NUMBER() OVER (
                PARTITION BY cik, fy
                ORDER BY CASE WHEN form = '10-K' THEN 0 ELSE 1 END, filed DESC, adsh DESC
            ) rn
            FROM submissions
        )
        WHERE rn = 1
    """)

    con.execute("""
        CREATE OR REPLACE TABLE normalized AS
        WITH candidates AS (
            SELECT
                s.cik,
                s.name AS company_name,
                s.sic,
                s.form AS filing_type,
                s.fy AS fiscal_year,
                s.fp AS fiscal_period,
                s.period AS period_end,
                s.filed AS filing_date,
                m.metric_name,
                f.value AS metric_value,
                f.uom AS unit,
                f.qtrs AS duration_quarters,
                f.tag AS source_tag,
                s.adsh AS accession_number,
                m.priority,
                ROW_NUMBER() OVER (
                    PARTITION BY s.adsh, m.metric_name
                    ORDER BY
                        CASE
                            WHEN m.metric_type = 'duration' AND f.qtrs = 4 THEN 0
                            WHEN m.metric_type = 'instant' AND f.qtrs = 0 THEN 0
                            ELSE 1
                        END,
                        CASE WHEN f.ddate = s.period THEN 0 ELSE 1 END,
                        m.priority,
                        ABS(DATE_DIFF('day', f.ddate, s.period))
                ) AS rn
            FROM selected_filings s
            JOIN facts f ON s.adsh = f.adsh
            JOIN metric_map m ON f.tag = m.tag
            WHERE f.ddate = s.period
              AND (
                (m.metric_type = 'duration' AND f.qtrs = 4)
                OR (m.metric_type = 'instant' AND f.qtrs = 0)
              )
        )
        SELECT
            cik, company_name, sic, filing_type, fiscal_year, fiscal_period,
            period_end, filing_date, metric_name, metric_value, unit,
            duration_quarters, source_tag, accession_number
        FROM candidates
        WHERE rn = 1
        ORDER BY company_name, fiscal_year, metric_name
    """)

    con.execute("COPY normalized TO ? (FORMAT PARQUET, COMPRESSION ZSTD)", [str(parquet_path)])
    con.execute("COPY normalized TO ? (FORMAT CSV, HEADER)", [str(csv_path)])

    summary_rows = con.execute("""
        SELECT company_name, fiscal_year, COUNT(*) metric_count
        FROM normalized GROUP BY company_name, fiscal_year
        ORDER BY company_name, fiscal_year
    """).fetchall()
    missing = con.execute("""
        SELECT c.company_alias, y.fiscal_year, m.metric_name
        FROM companies c
        CROSS JOIN range(?, ? + 1) y(fiscal_year)
        CROSS JOIN (SELECT DISTINCT metric_name FROM metric_map) m
        LEFT JOIN normalized n
          ON n.cik = c.cik AND n.fiscal_year = y.fiscal_year AND n.metric_name = m.metric_name
        WHERE n.cik IS NULL
        ORDER BY c.company_alias, y.fiscal_year, m.metric_name
    """, [args.start_year, args.end_year]).fetchall()

    report = {
        "row_count": con.execute("SELECT COUNT(*) FROM normalized").fetchone()[0],
        "company_count": con.execute("SELECT COUNT(DISTINCT cik) FROM normalized").fetchone()[0],
        "fiscal_year_min": con.execute("SELECT MIN(fiscal_year) FROM normalized").fetchone()[0],
        "fiscal_year_max": con.execute("SELECT MAX(fiscal_year) FROM normalized").fetchone()[0],
        "rows_by_company_year": [
            {"company_name": r[0], "fiscal_year": r[1], "metric_count": r[2]} for r in summary_rows
        ],
        "missing_company_year_metrics": [
            {"company": r[0], "fiscal_year": r[1], "metric_name": r[2]} for r in missing
        ],
    }
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    s3 = boto3.client("s3")
    prefix = "normalized/company_financial_metrics"
    s3.upload_file(str(parquet_path), args.bucket, f"{prefix}/company_financial_metrics.parquet")
    s3.upload_file(str(csv_path), args.bucket, f"{prefix}/company_financial_metrics.csv")
    s3.upload_file(str(report_path), args.bucket, f"{prefix}/quality_report.json")

    print(json.dumps(report, indent=2, default=str))
    print(f"Uploaded to s3://{args.bucket}/{prefix}/")


if __name__ == "__main__":
    main()
