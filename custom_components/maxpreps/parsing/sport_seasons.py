"""Parse MaxPreps school-home sportSeasons rows into TeamSeason models."""

from __future__ import annotations

from typing import Any

from custom_components.maxpreps.exceptions import SportSeasonsSchemaError
from custom_components.maxpreps.models import TeamSeason

_REQUIRED_STRING_FIELDS = (
    "schoolId",
    "sportSeasonId",
    "canonicalUrl",
    "sport",
    "gender",
    "level",
    "year",
    "season",
)


def parse_sport_seasons(rows: list[dict[str, Any]]) -> list[TeamSeason]:
    """Return every team season from an already-extracted ``sportSeasons`` list."""
    return [_parse_row(row, index) for index, row in enumerate(rows)]


def _parse_row(row: Any, index: int) -> TeamSeason:
    if not isinstance(row, dict):
        raise SportSeasonsSchemaError(f"sportSeasons[{index}] must be an object")

    values: dict[str, str] = {}
    for field in _REQUIRED_STRING_FIELDS:
        raw_value = row.get(field)
        if not isinstance(raw_value, str) or not raw_value.strip():
            raise SportSeasonsSchemaError(
                f"sportSeasons[{index}] missing required field {field!r}"
            )
        values[field] = raw_value.strip()

    all_season_id = _optional_string(row.get("allSeasonId"))
    is_published = _optional_bool(row.get("isPublished"), index)

    return TeamSeason(
        school_id=values["schoolId"],
        sport_season_id=values["sportSeasonId"],
        canonical_url=values["canonicalUrl"],
        sport=values["sport"],
        gender=values["gender"],
        level=values["level"],
        year=values["year"],
        season=values["season"],
        all_season_id=all_season_id,
        is_published=is_published,
    )


def _optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _optional_bool(value: Any, index: int) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise SportSeasonsSchemaError(
            f"sportSeasons[{index}] field 'isPublished' must be a boolean"
        )
    return value
