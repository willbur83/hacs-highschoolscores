"""Parse MaxPreps school search pageProps into School models."""

from __future__ import annotations

from typing import Any

from custom_components.maxpreps.exceptions import SearchSchemaError
from custom_components.maxpreps.models import School

_REQUIRED_STRING_FIELDS = ("schoolId", "canonicalUrl", "name")


def parse_search_page_props(page_props: dict[str, Any]) -> list[School]:
    """Return schools from ``pageProps.initialSchoolResults``."""
    raw_results = page_props.get("initialSchoolResults")
    if raw_results is None:
        return []
    if not isinstance(raw_results, list):
        raise SearchSchemaError("initialSchoolResults must be a list")

    return [_parse_school_row(row, index) for index, row in enumerate(raw_results)]


def _parse_school_row(row: Any, index: int) -> School:
    if not isinstance(row, dict):
        raise SearchSchemaError(f"initialSchoolResults[{index}] must be an object")

    values: dict[str, str] = {}
    for field in _REQUIRED_STRING_FIELDS:
        raw_value = row.get(field)
        if not isinstance(raw_value, str) or not raw_value.strip():
            raise SearchSchemaError(
                f"initialSchoolResults[{index}] missing required field {field!r}"
            )
        values[field] = raw_value.strip()

    city = _optional_string(row.get("city"))
    state = _optional_string(row.get("state"))
    zip_code = _optional_string(row.get("zip"))
    mascot = _optional_string(row.get("mascot"))
    mascot_url = _optional_string(row.get("mascotUrl"))

    return School(
        school_id=values["schoolId"],
        canonical_url=values["canonicalUrl"],
        name=values["name"],
        city=city,
        state=state,
        zip=zip_code,
        mascot=mascot,
        mascot_url=mascot_url,
    )


def _optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
