import os
import time
from typing import Any

import boto3


redshift_data = boto3.client("redshift-data")

WORKGROUP_NAME = os.environ["REDSHIFT_WORKGROUP"]
DATABASE_NAME = os.environ["REDSHIFT_DATABASE"]
SECRET_ARN = os.getenv("REDSHIFT_SECRET_ARN", "").strip()

QUERY_TIMEOUT_SECONDS = int(
    os.getenv("QUERY_TIMEOUT_SECONDS", "45")
)
MAX_RESULT_ROWS = int(
    os.getenv("MAX_RESULT_ROWS", "100")
)


class RedshiftExecutionError(RuntimeError):
    """Raised when Redshift rejects, fails or times out a query."""


def _field_value(field: dict[str, Any]) -> Any:
    if field.get("isNull"):
        return None

    for key in (
        "stringValue",
        "longValue",
        "doubleValue",
        "booleanValue",
        "blobValue",
    ):
        if key in field:
            return field[key]

    return None


def _connection_arguments() -> dict[str, str]:
    arguments = {
        "WorkgroupName": WORKGROUP_NAME,
        "Database": DATABASE_NAME,
    }

    if SECRET_ARN:
        arguments["SecretArn"] = SECRET_ARN

    return arguments


def execute_sql(
    sql: str,
    parameters: list[dict[str, str]] | None = None,
    statement_name: str = "sec-bedrock-poc-query",
) -> dict[str, Any]:
    execute_arguments: dict[str, Any] = {
        **_connection_arguments(),
        "Sql": sql,
        "StatementName": statement_name,
        "ResultFormat": "JSON",
    }

    if parameters:
        execute_arguments["Parameters"] = parameters

    response = redshift_data.execute_statement(**execute_arguments)
    statement_id = response["Id"]

    deadline = time.monotonic() + QUERY_TIMEOUT_SECONDS

    while True:
        description = redshift_data.describe_statement(
            Id=statement_id
        )

        status = description["Status"]

        if status == "FINISHED":
            break

        if status in {"FAILED", "ABORTED"}:
            error_message = description.get(
                "Error",
                f"Redshift statement ended with status {status}.",
            )
            raise RedshiftExecutionError(error_message)

        if time.monotonic() >= deadline:
            redshift_data.cancel_statement(Id=statement_id)
            raise RedshiftExecutionError(
                f"Query exceeded {QUERY_TIMEOUT_SECONDS} seconds "
                "and was cancelled."
            )

        time.sleep(0.5)

    if not description.get("HasResultSet", False):
        return {
            "statement_id": statement_id,
            "row_count": 0,
            "rows": [],
        }

    rows: list[dict[str, Any]] = []
    next_token: str | None = None
    column_names: list[str] = []

    while len(rows) < MAX_RESULT_ROWS:
        result_arguments: dict[str, str] = {
            "Id": statement_id,
        }

        if next_token:
            result_arguments["NextToken"] = next_token

        result = redshift_data.get_statement_result(
            **result_arguments
        )

        if not column_names:
            column_names = [
                column.get("name", f"column_{index}")
                for index, column in enumerate(
                    result.get("ColumnMetadata", [])
                )
            ]

        for record in result.get("Records", []):
            row = {
                column_names[index]: _field_value(field)
                for index, field in enumerate(record)
            }
            rows.append(row)

            if len(rows) >= MAX_RESULT_ROWS:
                break

        next_token = result.get("NextToken")

        if not next_token:
            break

    return {
        "statement_id": statement_id,
        "row_count": len(rows),
        "rows": rows,
    }