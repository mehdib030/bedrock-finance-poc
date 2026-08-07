import json
import logging
import os
import re
import uuid

import boto3


logger = logging.getLogger()
logger.setLevel(logging.INFO)

lambda_client = boto3.client("lambda")

BASIC_FUNCTION_NAME = os.environ[
    "BASIC_FUNCTION_NAME"
]
COMPLEX_FUNCTION_NAME = os.environ[
    "COMPLEX_FUNCTION_NAME"
]


def _extract_question(event: dict) -> str:
    if "body" in event:
        body = event["body"]

        if isinstance(body, str):
            body = json.loads(body)

        if isinstance(body, dict):
            return str(
                body.get("question", "")
            ).strip()

    return str(
        event.get("question", "")
    ).strip()


def classify_question(question: str) -> dict:
    lowered = question.lower()

    unsupported_patterns = [
        r"\bforecast\b",
        r"\bpredict\b",
        r"\bprediction\b",
        r"\bproject\b.+\b2026\b",
        r"\bcorrelation\b",
        r"\bwhat will\b",
    ]

    for pattern in unsupported_patterns:
        if re.search(pattern, lowered):
            return {
                "route": "UNSUPPORTED",
                "reason": (
                    "Forecasting and predictive analytics "
                    "are outside the POC scope."
                ),
            }

    complex_patterns = [
        r"\bcagr\b",
        r"\bcompound annual growth rate\b",
    ]

    for pattern in complex_patterns:
        if re.search(pattern, lowered):
            return {
                "route": "COMPLEX",
                "template_id": "revenue_cagr",
            }

    return {
        "route": "BASIC",
    }


def _invoke_function(
    function_name: str,
    payload: dict,
) -> dict:
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode("utf-8"),
    )

    response_payload = json.loads(
        response["Payload"].read()
    )

    if response.get("FunctionError"):
        raise RuntimeError(
            response_payload.get(
                "errorMessage",
                "Downstream Lambda invocation failed.",
            )
        )

    return response_payload


def lambda_handler(event, context):
    request_id = getattr(
        context,
        "aws_request_id",
        str(uuid.uuid4()),
    )

    try:
        question = _extract_question(event)

        if not question:
            return {
                "ok": False,
                "request_id": request_id,
                "error": "The question is required.",
            }

        decision = classify_question(question)

        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "stage": "route_selected",
                    "question": question,
                    **decision,
                }
            )
        )

        if decision["route"] == "UNSUPPORTED":
            return {
                "ok": False,
                "route": "UNSUPPORTED",
                "request_id": request_id,
                "question": question,
                "error": decision["reason"],
            }

        if decision["route"] == "COMPLEX":
            function_name = COMPLEX_FUNCTION_NAME
            downstream_payload = {
                "question": question,
                "template_id": decision["template_id"],
            }
        else:
            function_name = BASIC_FUNCTION_NAME
            downstream_payload = {
                "question": question,
            }

        downstream_response = _invoke_function(
            function_name,
            downstream_payload,
        )

        return {
            "router_request_id": request_id,
            "router_decision": decision,
            **downstream_response,
        }

    except Exception as exc:
        logger.exception("Router processing failed.")

        return {
            "ok": False,
            "request_id": request_id,
            "error_type": "ROUTER_ERROR",
            "error": str(exc),
        }