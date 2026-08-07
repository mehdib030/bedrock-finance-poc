import json
import logging
import os
import uuid

import boto3

from redshift_executor import execute_sql
from sql_validator import SqlValidationError, validate_sql


logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock_agent_runtime = boto3.client(
    "bedrock-agent-runtime"
)

KNOWLEDGE_BASE_ARN = os.environ["BEDROCK_KB_ARN"]

ALLOWED_RELATIONS = {
    relation.strip().lower()
    for relation in os.environ[
        "ALLOWED_RELATIONS"
    ].split(",")
    if relation.strip()
}

MAX_RESULT_ROWS = int(
    os.getenv("MAX_RESULT_ROWS", "100")
)


def generate_sql(question: str) -> str:
    response = bedrock_agent_runtime.generate_query(
        queryGenerationInput={
            "type": "TEXT",
            "text": question,
        },
        transformationConfiguration={
            "mode": "TEXT_TO_SQL",
            "textToSqlConfiguration": {
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": {
                    "knowledgeBaseArn": KNOWLEDGE_BASE_ARN,
                },
            },
        },
    )

    queries = response.get("queries", [])

    if not queries:
        raise RuntimeError(
            "Bedrock did not return a generated SQL query."
        )

    sql = queries[0].get("sql", "").strip()

    if not sql:
        raise RuntimeError(
            "Bedrock returned an empty SQL query."
        )

    return sql


def lambda_handler(event, context):
    request_id = getattr(
        context,
        "aws_request_id",
        str(uuid.uuid4()),
    )

    question = str(event.get("question", "")).strip()

    if not question:
        return {
            "ok": False,
            "route": "BASIC",
            "request_id": request_id,
            "error": "The question is required.",
        }

    try:
        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "stage": "question_received",
                    "question": question,
                }
            )
        )

        generated_sql = generate_sql(question)

        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "stage": "sql_generated",
                    "sql": generated_sql,
                }
            )
        )

        validated_sql = validate_sql(
            generated_sql,
            ALLOWED_RELATIONS,
            max_rows=MAX_RESULT_ROWS,
        )

        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "stage": "sql_validated",
                    "validated": True,
                    "sql": validated_sql,
                }
            )
        )

        result = execute_sql(
            validated_sql,
            statement_name="sec-bedrock-basic-query",
        )

        return {
            "ok": True,
            "route": "BASIC",
            "request_id": request_id,
            "question": question,
            "generated_sql": generated_sql,
            "validated_sql": validated_sql,
            "statement_id": result["statement_id"],
            "row_count": result["row_count"],
            "rows": result["rows"],
        }

    except SqlValidationError as exc:
        logger.warning(
            json.dumps(
                {
                    "request_id": request_id,
                    "stage": "sql_rejected",
                    "validated": False,
                    "error": str(exc),
                }
            )
        )

        return {
            "ok": False,
            "route": "BASIC",
            "request_id": request_id,
            "error_type": "SQL_VALIDATION_ERROR",
            "error": str(exc),
        }

    except Exception as exc:
        logger.exception(
            "Basic query processing failed."
        )

        return {
            "ok": False,
            "route": "BASIC",
            "request_id": request_id,
            "error_type": "BASIC_QUERY_ERROR",
            "error": str(exc),
        }