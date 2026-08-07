import re
from collections.abc import Iterable

from sqlglot import exp, parse


class SqlValidationError(ValueError):
    """Raised when generated SQL violates a POC safety rule."""


FORBIDDEN_KEYWORDS = {
    "alter",
    "analyze",
    "call",
    "comment",
    "copy",
    "create",
    "delete",
    "drop",
    "execute",
    "grant",
    "insert",
    "merge",
    "prepare",
    "revoke",
    "truncate",
    "unload",
    "update",
    "vacuum",
}

FORBIDDEN_SCHEMA_PREFIXES = {
    "information_schema",
    "pg_catalog",
}

FORBIDDEN_RELATION_PREFIXES = (
    "pg_",
    "stl_",
    "stv_",
    "svl_",
    "svv_",
)


def _normalize_name(value: str | None) -> str:
    return (value or "").strip().strip('"').lower()


def _table_relation(table: exp.Table) -> str:
    parts = [
        _normalize_name(table.catalog),
        _normalize_name(table.db),
        _normalize_name(table.name),
    ]
    return ".".join(part for part in parts if part)


def validate_sql(
    sql: str,
    allowed_relations: Iterable[str],
    max_rows: int = 100,
) -> str:
    """
    Validate Bedrock-generated SQL and return sanitized executable SQL.

    POC rules:
    - One statement only.
    - SELECT/CTE query only.
    - No comments.
    - No mutation, DDL or administrative commands.
    - Only allowlisted database objects.
    - Maximum result row limit.
    """
    if not isinstance(sql, str) or not sql.strip():
        raise SqlValidationError("Generated SQL is empty.")

    if len(sql) > 20_000:
        raise SqlValidationError("Generated SQL exceeds the maximum length.")

    raw_sql = sql.strip()

    if "--" in raw_sql or "/*" in raw_sql or "*/" in raw_sql:
        raise SqlValidationError("SQL comments are not permitted.")

    # Permit one optional trailing semicolon, but no internal semicolons.
    sql_without_trailing_semicolon = raw_sql.rstrip(";").strip()

    if ";" in sql_without_trailing_semicolon:
        raise SqlValidationError("Multiple SQL statements are not permitted.")

    lowered_sql = sql_without_trailing_semicolon.lower()

    if re.search(r"\bwith\s+recursive\b", lowered_sql):
        raise SqlValidationError("Recursive CTEs are not permitted.")

    if re.search(r"\bselect\s+.+?\s+into\s+", lowered_sql, re.DOTALL):
        raise SqlValidationError("SELECT INTO is not permitted.")

    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", lowered_sql):
            raise SqlValidationError(
                f"Forbidden SQL keyword detected: {keyword.upper()}."
            )

    try:
        statements = parse(sql_without_trailing_semicolon, read="redshift")
    except Exception as exc:
        raise SqlValidationError(f"SQL could not be parsed: {exc}") from exc

    if len(statements) != 1:
        raise SqlValidationError("Exactly one SQL statement is required.")

    statement = statements[0]

    if statement.key not in {"select", "union", "intersect", "except"}:
        raise SqlValidationError(
            f"Only SELECT queries are permitted; found {statement.key}."
        )

    allowed = {
        relation.strip().strip('"').lower()
        for relation in allowed_relations
        if relation.strip()
    }

    if not allowed:
        raise SqlValidationError("No allowed Redshift relations are configured.")

    allowed_bare_names = {
        relation.split(".")[-1]
        for relation in allowed
    }

    cte_names = {
        _normalize_name(cte.alias_or_name)
        for cte in statement.find_all(exp.CTE)
    }

    physical_tables_found = 0

    for table in statement.find_all(exp.Table):
        relation = _table_relation(table)
        bare_name = _normalize_name(table.name)
        schema_name = _normalize_name(table.db)

        # A CTE reference is not a physical database table.
        if not schema_name and bare_name in cte_names:
            continue

        physical_tables_found += 1

        if schema_name in FORBIDDEN_SCHEMA_PREFIXES:
            raise SqlValidationError(
                f"System schema is not permitted: {schema_name}."
            )

        if bare_name.startswith(FORBIDDEN_RELATION_PREFIXES):
            raise SqlValidationError(
                f"System relation is not permitted: {bare_name}."
            )

        is_allowed = (
            relation in allowed
            or (not schema_name and bare_name in allowed_bare_names)
        )

        if not is_allowed:
            raise SqlValidationError(
                f"Relation is not allowlisted: {relation or bare_name}."
            )

    if physical_tables_found == 0:
        raise SqlValidationError(
            "The SQL must query at least one approved database relation."
        )

    numeric_limit = re.search(
        r"\blimit\s+(\d+)\b",
        sql_without_trailing_semicolon,
        re.IGNORECASE,
    )

    any_limit = re.search(
        r"\blimit\b",
        sql_without_trailing_semicolon,
        re.IGNORECASE,
    )

    if any_limit and not numeric_limit:
        raise SqlValidationError("LIMIT must contain a numeric value.")

    if numeric_limit and int(numeric_limit.group(1)) > max_rows:
        raise SqlValidationError(
            f"LIMIT cannot exceed {max_rows} rows."
        )

    sanitized_sql = sql_without_trailing_semicolon

    if not numeric_limit:
        sanitized_sql = f"{sanitized_sql}\nLIMIT {max_rows}"

    return sanitized_sql