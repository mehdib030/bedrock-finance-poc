from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Add the project root to Python's import path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.generate_sql import SqlGenerationError, generate_sql  # noqa: E402


TEST_FILE = PROJECT_ROOT / "tests" / "test_questions.json"
OUTPUT_FILE = PROJECT_ROOT / "output" / "test_results.json"


FORBIDDEN_SQL_KEYWORDS = (
    "insert ",
    "update ",
    "delete ",
    "drop ",
    "alter ",
    "truncate ",
    "create ",
    "grant ",
    "revoke ",
    "copy ",
    "unload ",
)


def contains_expected_value(sql: str, value: Any) -> bool:
    """Perform a simple case-insensitive text check."""
    return str(value).lower() in sql.lower()


def evaluate_sql(test: dict[str, Any], sql: str) -> dict[str, Any]:
    """
    Perform basic Day 4 checks.

    These checks help evaluate generated SQL but are not a production
    SQL-security validator.
    """
    normalized_sql = " ".join(sql.lower().split())

    checks: dict[str, bool] = {
        "sql_generated": bool(sql.strip()),
        "uses_expected_table": (
            "analytics.company_financial_metrics" in normalized_sql
        ),
        "read_only": (
            normalized_sql.startswith("select ")
            or normalized_sql.startswith("with ")
        )
        and not any(
            keyword in normalized_sql
            for keyword in FORBIDDEN_SQL_KEYWORDS
        ),
    }

    expected_fields = {
        "expected_company": "company",
        "expected_metric": "metric",
        "expected_year": "year",
        "expected_start_year": "start_year",
        "expected_end_year": "end_year",
    }

    for json_field, check_name in expected_fields.items():
        if json_field in test:
            checks[check_name] = contains_expected_value(
                sql,
                test[json_field],
            )

    return {
        "checks": checks,
        "passed": all(checks.values()),
    }


def load_tests() -> list[dict[str, Any]]:
    if not TEST_FILE.exists():
        raise FileNotFoundError(f"Test file not found: {TEST_FILE}")

    data = json.loads(TEST_FILE.read_text(encoding="utf-8"))

    if not isinstance(data, list):
        raise ValueError("test_questions.json must contain a JSON array.")

    return data


def main() -> int:
    region = os.getenv("AWS_REGION", "us-east-1")
    knowledge_base_arn = os.getenv("BEDROCK_KNOWLEDGE_BASE_ARN")

    if not knowledge_base_arn:
        print(
            "ERROR: Set the BEDROCK_KNOWLEDGE_BASE_ARN "
            "environment variable."
        )
        return 2

    try:
        tests = load_tests()
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2

    results: list[dict[str, Any]] = []
    passed_count = 0

    for test in tests:
        test_id = test.get("id", "UNKNOWN")
        question = test.get("question", "").strip()

        print("\n" + "=" * 70)
        print(f"Test: {test_id}")
        print(f"Question: {question}")

        if not question:
            result = {
                "id": test_id,
                "question": question,
                "status": "ERROR",
                "error": "Question is empty.",
            }
            results.append(result)
            print("Result: ERROR — question is empty")
            continue

        try:
            sql = generate_sql(
                question=question,
                knowledge_base_arn=knowledge_base_arn,
                region_name=region,
            )

            evaluation = evaluate_sql(test, sql)

            if evaluation["passed"]:
                passed_count += 1
                status = "PASS"
            else:
                status = "REVIEW"

            result = {
                "id": test_id,
                "question": question,
                "generated_sql": sql,
                "status": status,
                **evaluation,
            }

            results.append(result)

            print("\nGenerated SQL:")
            print(sql)

            print("\nChecks:")
            for name, passed in evaluation["checks"].items():
                marker = "PASS" if passed else "FAIL"
                print(f"  {marker}: {name}")

            print(f"\nOverall result: {status}")
            print("Execution status: NOT EXECUTED")

        except SqlGenerationError as exc:
            results.append(
                {
                    "id": test_id,
                    "question": question,
                    "status": "ERROR",
                    "error": str(exc),
                }
            )
            print(f"\nResult: ERROR — {exc}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_tests": len(tests),
        "passed": passed_count,
        "needs_review_or_failed": len(tests) - passed_count,
        "results": results,
    }

    OUTPUT_FILE.write_text(
        json.dumps(output, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 70)
    print(f"Completed: {len(tests)} tests")
    print(f"Passed:    {passed_count}")
    print(f"Review:    {len(tests) - passed_count}")
    print(f"Results:   {OUTPUT_FILE}")

    return 0 if passed_count == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())