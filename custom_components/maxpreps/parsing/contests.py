"""Validate MaxPreps schedule ``contests[]`` positional schema."""

from __future__ import annotations

from typing import Any

from custom_components.maxpreps.exceptions import ContestSchemaError

CONTEST_ROW_ARITY = 41
PARTICIPANT_WIDTH = 32

IDX_TEAMS = 0
IDX_CONTEST_ID = 1
IDX_HAS_RESULT = 4
IDX_LOCATION = 5
IDX_DATE = 11
IDX_SPORT_SEASON_ID = 14
IDX_CONTEST_STATE = 15
IDX_CANONICAL_URL = 18
IDX_STATUS_MESSAGE = 28
IDX_CURRENT_TEAM = 37
IDX_OPPONENT_TEAM = 38

PART_IDX_ROW_ID = 0
PART_IDX_TEAM_ID = 1
PART_IDX_SPORT_SEASON_ID = 2
PART_IDX_INDEX = 4
PART_IDX_HOME_AWAY_TYPE = 11

_FEATURED_FIELD_MAP: tuple[tuple[str, int], ...] = (
    ("location", IDX_LOCATION),
    ("date", IDX_DATE),
    ("contestState", IDX_CONTEST_STATE),
    ("canonicalUrl", IDX_CANONICAL_URL),
)


def validate_contests_shape(contests: Any) -> None:
    """Raise ``ContestSchemaError`` when ``contests`` is not a valid 41/32 columnar list."""
    if not isinstance(contests, list):
        raise ContestSchemaError("contests must be a list")

    for row_index, row in enumerate(contests):
        _validate_contest_row(row, row_index)


def check_featured_game_consistency(
    contests: list[Any],
    featured_game_data: dict[str, Any],
) -> None:
    """Cross-check named ``featuredGameData`` against the matching ``contests`` row."""
    if not isinstance(featured_game_data, dict):
        raise ContestSchemaError("featuredGameData must be an object")

    featured_id = featured_game_data.get("contestId")
    if not isinstance(featured_id, str) or not featured_id:
        raise ContestSchemaError("featuredGameData missing contestId")

    match_row = _find_contest_row(contests, featured_id)
    if match_row is None:
        raise ContestSchemaError(
            f"featuredGameData contestId {featured_id!r} not found in contests"
        )

    for featured_key, row_index in _FEATURED_FIELD_MAP:
        featured_value = featured_game_data.get(featured_key)
        row_value = match_row[row_index]
        if featured_value != row_value:
            raise ContestSchemaError(
                f"featuredGameData {featured_key!r} does not match "
                f"contests[][{row_index}] for contestId {featured_id!r}"
            )


def _find_contest_row(contests: list[Any], contest_id: str) -> list[Any] | None:
    for row in contests:
        if (
            isinstance(row, list)
            and len(row) > IDX_CONTEST_ID
            and row[IDX_CONTEST_ID] == contest_id
        ):
            return row
    return None


def _validate_contest_row(row: Any, row_index: int) -> None:
    if not isinstance(row, list):
        raise ContestSchemaError(f"contests[{row_index}] must be a list")
    if len(row) != CONTEST_ROW_ARITY:
        raise ContestSchemaError(
            f"contests[{row_index}] must have length {CONTEST_ROW_ARITY}, got {len(row)}"
        )

    _validate_teams(row[IDX_TEAMS], row_index)
    _require_type(row[IDX_CONTEST_ID], str, row_index, IDX_CONTEST_ID)
    _require_type(row[IDX_HAS_RESULT], bool, row_index, IDX_HAS_RESULT)
    _require_str_or_none(row[IDX_LOCATION], row_index, IDX_LOCATION)
    _require_type(row[IDX_DATE], str, row_index, IDX_DATE)
    _require_type(row[IDX_SPORT_SEASON_ID], str, row_index, IDX_SPORT_SEASON_ID)
    _require_type(row[IDX_CONTEST_STATE], int, row_index, IDX_CONTEST_STATE)
    _require_str_or_none(row[IDX_CANONICAL_URL], row_index, IDX_CANONICAL_URL)
    _require_type(row[IDX_STATUS_MESSAGE], str, row_index, IDX_STATUS_MESSAGE)
    _require_type(row[IDX_CURRENT_TEAM], list, row_index, IDX_CURRENT_TEAM)
    _require_type(row[IDX_OPPONENT_TEAM], list, row_index, IDX_OPPONENT_TEAM)


def _validate_teams(teams: Any, row_index: int) -> None:
    if not isinstance(teams, list) or len(teams) != 2:
        raise ContestSchemaError(
            f"contests[{row_index}][{IDX_TEAMS}] must be a list of two participants"
        )

    for participant_index, participant in enumerate(teams):
        _validate_participant(participant, row_index, participant_index)


def _validate_participant(participant: Any, row_index: int, participant_index: int) -> None:
    prefix = f"contests[{row_index}][{IDX_TEAMS}][{participant_index}]"
    if not isinstance(participant, list):
        raise ContestSchemaError(f"{prefix} must be a list")
    if len(participant) != PARTICIPANT_WIDTH:
        raise ContestSchemaError(
            f"{prefix} must have length {PARTICIPANT_WIDTH}, got {len(participant)}"
        )

    _require_type(
        participant[PART_IDX_ROW_ID],
        str,
        row_index,
        f"{IDX_TEAMS}][{participant_index}][{PART_IDX_ROW_ID}",
    )
    _require_str_or_none(
        participant[PART_IDX_TEAM_ID],
        row_index,
        f"{IDX_TEAMS}][{participant_index}][{PART_IDX_TEAM_ID}",
    )
    _require_type(
        participant[PART_IDX_SPORT_SEASON_ID],
        str,
        row_index,
        f"{IDX_TEAMS}][{participant_index}][{PART_IDX_SPORT_SEASON_ID}",
    )
    _require_type(
        participant[PART_IDX_INDEX],
        int,
        row_index,
        f"{IDX_TEAMS}][{participant_index}][{PART_IDX_INDEX}",
    )
    _require_type(
        participant[PART_IDX_HOME_AWAY_TYPE],
        int,
        row_index,
        f"{IDX_TEAMS}][{participant_index}][{PART_IDX_HOME_AWAY_TYPE}",
    )


def _require_type(value: Any, expected_type: type[Any], row_index: int, field: int | str) -> None:
    if not isinstance(value, expected_type):
        raise ContestSchemaError(
            f"contests[{row_index}][{field}] must be {expected_type.__name__}"
        )


def _require_str_or_none(value: Any, row_index: int, field: int | str) -> None:
    if value is not None and not isinstance(value, str):
        raise ContestSchemaError(f"contests[{row_index}][{field}] must be a string or null")
