"""Adapt MaxPreps schedule pageProps into a Schedule model."""

from __future__ import annotations

from typing import Any

from custom_components.maxpreps.exceptions import ContestSchemaError
from custom_components.maxpreps.models import GameStatus, Schedule, TeamSeason
from custom_components.maxpreps.parsing.contests import (
    check_featured_game_consistency,
    decode_contest_row,
    validate_contests_shape,
)

_REQUIRED_TEAM_SEASON_FIELDS = (
    "teamId",
    "sportSeasonId",
    "canonicalUrl",
    "sport",
    "gender",
    "level",
    "year",
    "season",
)


def parse_schedule_page_props(page_props: dict[str, Any]) -> Schedule:
    """Return a Schedule from already-unwrapped schedule ``pageProps``."""
    team_context = page_props.get("teamContext")
    if not isinstance(team_context, dict):
        raise ContestSchemaError("teamContext must be an object")

    data = team_context.get("data")
    if not isinstance(data, dict):
        raise ContestSchemaError("teamContext.data must be an object")

    team_season = _parse_team_season(data)
    school_id = team_season.school_id

    contests = page_props.get("contests")
    validate_contests_shape(contests)

    featured = page_props.get("featuredGameData")
    if featured is not None:
        check_featured_game_consistency(contests, featured)

    games = [
        game
        for row in contests
        if (game := decode_contest_row(row, school_id)).status is not GameStatus.DELETED
    ]

    return Schedule(
        team_season=team_season,
        games=games,
        team_logo=_team_logo_from_data(data),
        team_record=_team_record_from_context(team_context),
    )


def _parse_team_season(data: dict[str, Any]) -> TeamSeason:
    values: dict[str, str] = {}
    for field in _REQUIRED_TEAM_SEASON_FIELDS:
        raw_value = data.get(field)
        if not isinstance(raw_value, str) or not raw_value.strip():
            raise ContestSchemaError(
                f"teamContext.data missing required field {field!r}"
            )
        values[field] = raw_value.strip()

    return TeamSeason(
        school_id=values["teamId"],
        sport_season_id=values["sportSeasonId"],
        canonical_url=values["canonicalUrl"],
        sport=values["sport"],
        gender=values["gender"],
        level=values["level"],
        year=values["year"],
        season=values["season"],
        all_season_id=_optional_string(data.get("allSeasonId")),
        is_published=_optional_bool(data.get("isPublished")),
    )


def _team_logo_from_data(data: dict[str, Any]) -> str | None:
    return _optional_string(data.get("schoolMascotUrl"))


def _team_record_from_context(team_context: dict[str, Any]) -> str | None:
    standings_data = team_context.get("standingsData")
    if not isinstance(standings_data, dict):
        return None

    overall = standings_data.get("overallStanding")
    if not isinstance(overall, dict):
        return None

    return _optional_string(overall.get("overallWinLossTies"))


def _optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ContestSchemaError("teamContext.data field 'isPublished' must be a boolean")
    return value
