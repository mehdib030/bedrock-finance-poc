from typing import Any


class ParameterValidationError(ValueError):
    """Raised when extracted complex-query parameters are invalid."""


COMPANY_ALIASES = {
    "aapl": "APPLE INC",
    "apple": "APPLE INC",
    "apple inc": "APPLE INC",
    "apple inc.": "APPLE INC",
    "msft": "MSFT",
    "microsoft": "MSFT",
    "microsoft corporation": "MSFT",
    "amzn": "AMZN",
    "amazon": "AMZN",
    "amazon.com": "AMZN",
    "googl": "GOOGL",
    "goog": "GOOGL",
    "alphabet": "GOOGL",
    "google": "GOOGL",
    "meta": "META",
    "meta platforms": "META",
    "facebook": "META",
}

MIN_YEAR = 2022
MAX_YEAR = 2025


def _normalize_company_name(value: Any) -> str:
    normalized = str(value or "").strip().lower()

    company_name = COMPANY_ALIASES.get(normalized)

    if not company_name:
        raise ParameterValidationError(
            "Company must be Apple, Microsoft, Amazon, "
            "Alphabet or Meta."
        )

    return company_name


def _normalize_year(value: Any, field_name: str) -> int:
    try:
        year = int(value)
    except (TypeError, ValueError) as exc:
        raise ParameterValidationError(
            f"{field_name} must be a four-digit year."
        ) from exc

    if year < MIN_YEAR or year > MAX_YEAR:
        raise ParameterValidationError(
            f"{field_name} must be between "
            f"{MIN_YEAR} and {MAX_YEAR}."
        )

    return year


def validate_parameters(
    template_id: str,
    parameters: dict[str, Any],
) -> dict[str, str]:
    if template_id != "revenue_cagr":
        raise ParameterValidationError(
            f"Unsupported template: {template_id}"
        )

    permitted_keys = {
        "company_name",
        "company",
        "start_year",
        "end_year",
    }

    unexpected = set(parameters) - permitted_keys

    if unexpected:
        raise ParameterValidationError(
            "Unexpected parameters: "
            + ", ".join(sorted(unexpected))
        )

    company_name_input = (
        parameters.get("company_name")
        or parameters.get("company")
    )

    company_name = _normalize_company_name(company_name_input)
    start_year = _normalize_year(
        parameters.get("start_year"),
        "start_year",
    )
    end_year = _normalize_year(
        parameters.get("end_year"),
        "end_year",
    )

    if start_year >= end_year:
        raise ParameterValidationError(
            "start_year must be earlier than end_year."
        )

    return {
        "company_name": company_name,
        "start_year": str(start_year),
        "end_year": str(end_year),
    }


def to_redshift_parameters(
    parameters: dict[str, str],
) -> list[dict[str, str]]:
    return [
        {
            "name": name,
            "value": value,
        }
        for name, value in parameters.items()
    ]