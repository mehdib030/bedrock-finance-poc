import json
import logging
import os
import re
import uuid

import boto3

from parameter_validator import (
    ParameterValidationError,
    to_redshift_parameters,
    validate_parameters,
)
from redshift_executor import execute_sql
from template_registry import get_template


logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock_runtime = boto3.client("bedrock-runtime")

MODEL_ID = os.environ["BEDROCK_MODEL_ID"]


def _extract_text(response: dict) -> str:
    content = (
        response.get("output", {})
        .get("message", {})
        .get("content", [])
    )

    text_parts = [
        block["text"]
        for block in content
        if "text" in block
    ]

    return "".join(text_parts).strip()


def _parse_json_response(text: str) -> dict:
    cleaned = text.strip()

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s*```$", "", cleaned)

    parsed = json.loads(cleaned)

    if not isinstance(parsed, dict):
        raise ValueError(
            "Bedrock parameter output must be a JSON object."
        )

    return parsed


def extract_parameters(
    question: str,
    template_id: str,
) -> dict:
    if template_id != "revenue_cagr":
        raise ValueError(
            f"Unsupported template: {template_id}"
        )

    system_prompt = """
You extract parameters for an approved financial SQL template.

The only supported template is revenue_cagr.

Return only one JSON object with these fields:
{
  "company": "company name or ticker",
  "start_year": 2022,
  "end_year": 2025
}

Supported companies:
- Apple / AAPL
- Microsoft / MSFT
- Amazon / AMZN
- Alphabet / Google / GOOGL
- Meta / META

Supported years are 2022 through 2025.

Do not generate SQL.
Do not add explanations.
Do not add Markdown.
Do not infer a missing company or year.
Use null when a required value is missing.
""".strip()

    response = bedrock_runtime.converse(
        modelId=MODEL_ID,
        system=[
            {
                "text": system_prompt,
            }
        ],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "text": question,
                    }
                ],
            }
        ],
        inferenceConfig={
            "temperature": 0,
            "maxTokens": 300,
        },
    )

    return _parse_json_response(
        _extract_text(response)
    )


def lambda_handler(event, context):
    request_id = getattr(
        context,
        "aws_request_id",
        str(uuid.uuid4()),
    )

    question = str(event.get("question", "")).strip()
    template_id = str(
        event.get("template_id", "")
    ).strip()

    if not question:
        return {
            "ok": False,
            "route": "COMPLEX",
            "request_id": request_id,
            "error": "The question is required.",
        }

    try:
        template = get_template(template_id)

        extracted = extract_parameters(
            question,
            template_id,
        )

        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "stage": "parameters_extracted",
                    "template_id": template_id,
                    "parameters": extracted,
                }
            )
        )

        validated = validate_parameters(
            template_id,
            extracted,
        )

        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "stage": "parameters_validated",
                    "template_id": template_id,
                    "parameters": validated,
                }
            )
        )

        redshift_parameters = to_redshift_parameters(
            validated
        )

        result = execute_sql(
            template["sql"],
            parameters=redshift_parameters,
            statement_name=(
                f"sec-bedrock-complex-{template_id}"
            ),
        )

        return {
            "ok": True,
            "route": "COMPLEX",
            "request_id": request_id,
            "question": question,
            "template_id": template_id,
            "validated_parameters": validated,
            "statement_id": result["statement_id"],
            "row_count": result["row_count"],
            "rows": result["rows"],
        }

    except ParameterValidationError as exc:
        return {
            "ok": False,
            "route": "COMPLEX",
            "request_id": request_id,
            "error_type": "PARAMETER_VALIDATION_ERROR",
            "error": str(exc),
        }

    except Exception as exc:
        logger.exception(
            "Complex query processing failed."
        )

        return {
            "ok": False,
            "route": "COMPLEX",
            "request_id": request_id,
            "error_type": "COMPLEX_QUERY_ERROR",
            "error": str(exc),
        }