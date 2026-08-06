"""Conservative validator for Bedrock-generated basic SQL."""

from __future__ import annotations

import re
from collections.abc import Sequence


DEFAULT_LIMIT = 100
MAX_LIMIT = 100
MAX_SQL_LENGTH = 10_000


FORBIDDEN_KEYWORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "MERGE",
    "COPY",
    "UNLOAD",
    "CALL",
    "EXECUTE",
    "GRANT",
    "REVOKE",
    "VACUUM",
    "ANALYZE",
    "BEGIN",
    "COMMIT",
    "ROLLBACK",
)


COMPLEX_FEATURES = {
    r"\bWITH\b": "CTEs are not allowed for basic queries",
    r"\bJOIN\b": "joins are not allowed for basic queries",
    r"\bUNION\b": "UNION is not allowed for basic queries",
    r"\bINTERSECT\b": "INTERSECT is not allowed",
    r"\bEXCEPT\b": "EXCEPT is not allowed",
    r"\bOVER\s*\(": "window functions are not allowed",
    r"\bLAG\s*\(": "LAG is not allowed",
    r"\bLEAD\s*\(": "LEAD is not allowed",
    r"\bROW_NUMBER\s*\(": "ROW_NUMBER is not allowed",
    r"\bRANK\s*\(": "RANK is not allowed",
    r"\bDENSE_RANK\s*\(": "DENSE_RANK is not allowed",
    r"\bOFFSET\b": "OFFSET is not allowed",
}


def _remove_code_fence(sql: str) -> str:
    """Remove a Markdown SQL fence if Bedrock returned one."""

    value = sql.strip()

    match = re.fullmatch(
        r"```(?:sql)?\s*(.*?)\s*```",
        value,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if match:
        return match.group(1).strip()

    return value


def _remove_trailing_semicolon(sql: str) -> str:
    sql = sql.strip()

    if sql.endswith(";"):
        return sql[:-1].rstrip()

    return sql


def _mask_string_literals(sql: str) -> str:
    """Hide quoted values before checking SQL keywords."""

    result: list[str] = []
    index = 0
    inside_string = False

    while index < len(sql):
        character = sql[index]

        if inside_string:
            if character == "'":
                # SQL escapes a quote using two single quotes.
                if index + 1 < len(sql) and sql[index + 1] == "'":
                    result.extend((" ", " "))
                    index += 2
                    continue

                inside_string = False

            result.append(" ")
            index += 1
            continue

        if character == "'":
            inside_string = True
            result.append(" ")
            index += 1
            continue

        result.append(character)
        index += 1

    if inside_string:
        raise ValueError(
            "SQL contains an unterminated string literal."
        )

    return "".join(result)


def _normalize_table_name(table_name: str) -> str:
    """Normalize quoted and unquoted schema/table identifiers."""

    return re.sub(
        r'[\s"]',
        "",
        table_name,
    ).lower()


def _validate_statement(masked_sql: str) -> None:
    if not re.match(
        r"^\s*SELECT\b",
        masked_sql,
        flags=re.IGNORECASE,
    ):
        raise ValueError(
            "Only SELECT statements are permitted."
        )

    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(
            rf"\b{re.escape(keyword)}\b",
            masked_sql,
            flags=re.IGNORECASE,
        ):
            raise ValueError(
                f"Forbidden SQL keyword detected: {keyword}."
            )


def _validate_single_statement(masked_sql: str) -> None:
    if ";" in masked_sql:
        raise ValueError(
            "Multiple SQL statements are not permitted."
        )

    if (
        "--" in masked_sql
        or "/*" in masked_sql
        or "*/" in masked_sql
    ):
        raise ValueError(
            "SQL comments are not permitted."
        )


def _validate_basic_features(masked_sql: str) -> None:
    for pattern, reason in COMPLEX_FEATURES.items():
        if re.search(
            pattern,
            masked_sql,
            flags=re.IGNORECASE,
        ):
            raise ValueError(
                f"SQL rejected: {reason}. "
                "Use the approved complex-query path."
            )

    select_count = len(
        re.findall(
            r"\bSELECT\b",
            masked_sql,
            flags=re.IGNORECASE,
        )
    )

    if select_count != 1:
        raise ValueError(
            "Subqueries and multiple SELECT clauses are not "
            "permitted for basic queries."
        )


def _validate_table(
    masked_sql: str,
    allowed_tables: Sequence[str],
) -> None:
    normalized_allowed_tables = {
        _normalize_table_name(table)
        for table in allowed_tables
        if table and table.strip()
    }

    if not normalized_allowed_tables:
        raise ValueError(
            "The basic SQL table allowlist is empty."
        )

    # Supports:
    # schema.table
    # database.schema.table
    # "schema"."table"
    table_matches = re.findall(
        r'\bFROM\s+'
        r'((?:"[^"]+"|[A-Za-z_][A-Za-z0-9_$]*)'
        r'(?:\s*\.\s*'
        r'(?:"[^"]+"|[A-Za-z_][A-Za-z0-9_$]*)){1,2})',
        masked_sql,
        flags=re.IGNORECASE,
    )

    if len(table_matches) != 1:
        raise ValueError(
            "A basic query must contain exactly one FROM table."
        )

    generated_table = _normalize_table_name(
        table_matches[0]
    )

    if generated_table not in normalized_allowed_tables:
        raise ValueError(
            f"Unapproved table: {generated_table}. "
            f"Allowed tables: {sorted(normalized_allowed_tables)}"
        )

    # Prevent:
    # FROM approved_table a, another_table b
    from_section = re.search(
        r"\bFROM\b(.*?)(?="
        r"\bWHERE\b|"
        r"\bGROUP\s+BY\b|"
        r"\bHAVING\b|"
        r"\bORDER\s+BY\b|"
        r"\bLIMIT\b|"
        r"$"
        r")",
        masked_sql,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if from_section and "," in from_section.group(1):
        raise ValueError(
            "Multiple table references are not permitted."
        )


def _enforce_limit(
    sql: str,
    masked_sql: str,
    max_limit: int,
) -> str:
    limit_keywords = re.findall(
        r"\bLIMIT\b",
        masked_sql,
        flags=re.IGNORECASE,
    )

    if len(limit_keywords) > 1:
        raise ValueError(
            "Multiple LIMIT clauses are not permitted."
        )

    if not limit_keywords:
        return f"{sql}\nLIMIT {max_limit}"

    limit_match = re.search(
        r"\bLIMIT\s+(\d+)\b",
        masked_sql,
        flags=re.IGNORECASE,
    )

    if limit_match is None:
        raise ValueError(
            "LIMIT must use a numeric value."
        )

    requested_limit = int(limit_match.group(1))

    if requested_limit < 1:
        raise ValueError(
            "LIMIT must be greater than zero."
        )

    if requested_limit <= max_limit:
        return sql

    start, end = limit_match.span(1)

    return (
        sql[:start]
        + str(max_limit)
        + sql[end:]
    )


def validate_basic_sql(
    sql: str,
    allowed_tables: Sequence[str],
    max_limit: int = DEFAULT_LIMIT,
) -> str:
    """Validate SQL generated for the basic-query path."""

    if not isinstance(sql, str):
        raise ValueError(
            "Generated SQL must be a string."
        )

    cleaned_sql = _remove_code_fence(sql)
    cleaned_sql = _remove_trailing_semicolon(cleaned_sql)

    if not cleaned_sql:
        raise ValueError(
            "Bedrock returned empty SQL."
        )

    if len(cleaned_sql) > MAX_SQL_LENGTH:
        raise ValueError(
            "Generated SQL is too long."
        )

    if not 1 <= max_limit <= MAX_LIMIT:
        raise ValueError(
            f"max_limit must be between 1 and {MAX_LIMIT}."
        )

    masked_sql = _mask_string_literals(cleaned_sql)

    _validate_single_statement(masked_sql)
    _validate_statement(masked_sql)
    _validate_basic_features(masked_sql)
    _validate_table(masked_sql, allowed_tables)

    return _enforce_limit(
        cleaned_sql,
        masked_sql,
        max_limit,
    )