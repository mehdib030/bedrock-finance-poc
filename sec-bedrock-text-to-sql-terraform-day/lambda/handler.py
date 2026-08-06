from __future__ import annotations

import json
import os
from typing import Any

import boto3

bedrock_agent_runtime = boto3.client("bedrock-agent-runtime")
redshift_data = boto3.client("redshift-data")

KB_ARN = os.getenv("BEDROCK_KNOWLEDGE_BASE_ARN", "")
WORKGROUP = os.environ["REDSHIFT_WORKGROUP_NAME"]
DATABASE = os.environ["REDSHIFT_DATABASE_NAME"]
BASIC_VIEW = os.environ["BASIC_VIEW_NAME"].lower()
MAX_ROWS = int(os.getenv("MAX_RESULT_ROWS", "500"))

FORBIDDEN = (
    " insert ", " update ", " delete ", " merge ", " drop ", " alter ",
    " create ", " truncate ", " grant ", " revoke ", " join ", " with ",
    " union ", " intersect ", " except ", " over ("
)


def response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body, default=str),
    }


def validate_basic_sql(sql: str) -> str:
    cleaned = sql.strip().rstrip(";")
    padded = f" {cleaned.lower()} "

    if not cleaned:
        raise ValueError("Generated SQL is empty")
    if ";" in cleaned:
        raise ValueError("Multiple statements are not allowed")
    if not cleaned.lower().startswith("select"):
        raise ValueError("Only SELECT is allowed for generated SQL")
    if BASIC_VIEW not in cleaned.lower():
        raise ValueError("Generated SQL must use the restricted basic view")
    if any(token in padded for token in FORBIDDEN):
        raise ValueError("Generated SQL exceeds the allowed basic-query policy")

    if " limit " not in padded:
        cleaned = f"{cleaned}\nLIMIT {MAX_ROWS}"

    return cleaned


def generate_basic_sql(question: str) -> str:
    if not KB_ARN:
        raise RuntimeError("BEDROCK_KNOWLEDGE_BASE_ARN is not configured")

    result = bedrock_agent_runtime.generate_query(
        queryGenerationInput={"type": "TEXT", "text": question},
        transformationConfiguration={
            "mode": "TEXT_TO_SQL",
            "textToSqlConfiguration": {
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    "knowledgeBaseArn": KB_ARN
                },
            },
        },
    )
    queries = result.get("queries", [])
    if not queries:
        raise RuntimeError("Bedrock returned no SQL")
    return queries[0]["sql"]


def submit_sql(sql: str) -> str:
    result = redshift_data.execute_statement(
        WorkgroupName=WORKGROUP,
        Database=DATABASE,
        Sql=sql,
    )
    return result["Id"]


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        payload = json.loads(event.get("body") or "{}")
        mode = payload.get("mode", "basic")

        if mode != "basic":
            return response(
                501,
                {
                    "status": "ADVANCED_PATH_NOT_IMPLEMENTED",
                    "message": "Terraform deployed the template registry. Add structured parameter extraction and renderer code next.",
                },
            )

        question = str(payload.get("question", "")).strip()
        if not question:
            return response(400, {"message": "question is required"})

        generated_sql = generate_basic_sql(question)
        approved_sql = validate_basic_sql(generated_sql)
        statement_id = submit_sql(approved_sql)

        return response(
            202,
            {
                "status": "SUBMITTED",
                "route": "BASIC_GENERATED_SQL",
                "generated_sql": generated_sql,
                "executed_sql": approved_sql,
                "statement_id": statement_id,
            },
        )
    except ValueError as exc:
        return response(422, {"status": "SQL_REJECTED", "message": str(exc)})
    except Exception as exc:
        return response(500, {"status": "ERROR", "message": str(exc)})
