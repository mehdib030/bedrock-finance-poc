from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError


LOGGER = logging.getLogger("generate_sql")


class SqlGenerationError(RuntimeError):
    """Raised when Amazon Bedrock does not return generated SQL."""


def create_client(region_name: str):
    """Create the Amazon Bedrock Agent Runtime client."""
    return boto3.client(
        "bedrock-agent-runtime",
        region_name=region_name,
    )


def generate_sql(
    question: str,
    knowledge_base_arn: str,
    region_name: str,
) -> str:
    """
    Convert an English natural-language question into Redshift SQL.

    This function generates SQL only. It does not execute the SQL.
    """
    clean_question = question.strip()

    if not clean_question:
        raise ValueError("The question cannot be empty.")

    if not knowledge_base_arn.startswith("arn:aws:bedrock:"):
        raise ValueError("BEDROCK_KNOWLEDGE_BASE_ARN is invalid.")

    client = create_client(region_name)

    try:
        response: dict[str, Any] = client.generate_query(
            queryGenerationInput={
                "text": clean_question,
                "type": "TEXT",
            },
            transformationConfiguration={
                "mode": "TEXT_TO_SQL",
                "textToSqlConfiguration": {
                    "knowledgeBaseConfiguration": {
                        "knowledgeBaseArn": knowledge_base_arn,
                    },
                    "type": "KNOWLEDGE_BASE",
                },
            },
        )
    except ClientError as exc:
        error = exc.response.get("Error", {})
        code = error.get("Code", "UnknownClientError")
        message = error.get("Message", str(exc))
        raise SqlGenerationError(
            f"Bedrock GenerateQuery failed: {code}: {message}"
        ) from exc
    except BotoCoreError as exc:
        raise SqlGenerationError(
            f"AWS SDK error while calling Bedrock: {exc}"
        ) from exc

    queries = response.get("queries", [])

    if not queries:
        raise SqlGenerationError(
            "Amazon Bedrock returned no generated queries."
        )

    sql = queries[0].get("sql")

    if not sql or not isinstance(sql, str):
        raise SqlGenerationError(
            "Amazon Bedrock response did not contain valid SQL."
        )

    return sql.strip()


def write_result(
    question: str,
    sql: str,
    output_directory: Path,
) -> Path:
    """Save the question and generated SQL for evaluation."""
    output_directory.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_directory / f"generated_sql_{timestamp}.json"

    result = {
        "generated_at": timestamp,
        "question": question,
        "generated_sql": sql,
        "executed": False,
    }

    output_path.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    return output_path


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Redshift SQL using Amazon Bedrock."
    )

    parser.add_argument(
        "question",
        help="English financial question to transform into SQL.",
    )

    parser.add_argument(
        "--region",
        default=os.getenv("AWS_REGION", "us-east-1"),
        help="AWS Region containing the Knowledge Base.",
    )

    parser.add_argument(
        "--knowledge-base-arn",
        default=os.getenv("BEDROCK_KNOWLEDGE_BASE_ARN"),
        help="Amazon Bedrock Knowledge Base ARN.",
    )

    parser.add_argument(
        "--output-directory",
        default="output",
        help="Directory in which to save generated SQL.",
    )

    return parser.parse_args()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )

    args = parse_arguments()

    if not args.knowledge_base_arn:
        LOGGER.error(
            "Set BEDROCK_KNOWLEDGE_BASE_ARN or provide "
            "--knowledge-base-arn."
        )
        return 2

    try:
        sql = generate_sql(
            question=args.question,
            knowledge_base_arn=args.knowledge_base_arn,
            region_name=args.region,
        )

        output_path = write_result(
            question=args.question,
            sql=sql,
            output_directory=Path(args.output_directory),
        )
    except (ValueError, SqlGenerationError) as exc:
        LOGGER.error("%s", exc)
        return 1

    print("\nQuestion:")
    print(args.question)

    print("\nGenerated SQL:")
    print(sql)

    print("\nExecution status:")
    print("NOT EXECUTED")

    print(f"\nSaved to: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())