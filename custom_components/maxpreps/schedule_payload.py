"""Pure websocket schedule DTO serializer (no Home Assistant imports)."""

from __future__ import annotations

from typing import Any

from custom_components.maxpreps.snapshots import ProgramSnapshot, TermSnapshot
from custom_components.maxpreps.models import GameStatus
from custom_components.maxpreps.program_identity import ParsedProgramUniqueId, program_identity_matches
from custom_components.maxpreps.program_sensor import ProgramGameRef, game_attribute, program_display_label
from custom_components.maxpreps.programs import ordered_deduplicated_season_terms

SCHEMA_VERSION = 1


def _term_season_name(term: TermSnapshot) -> str:
    if term.team_season is not None:
        return term.team_season.season
    return ""


def sort_term_snapshots_for_presentation(
    terms: tuple[TermSnapshot, ...],
) -> tuple[TermSnapshot, ...]:
    """Order coordinator term snapshots for websocket DTO presentation."""
    if not terms:
        return terms

    season_names = [_term_season_name(term) for term in terms if _term_season_name(term)]
    order = ordered_deduplicated_season_terms(season_names)
    rank = {name: index for index, name in enumerate(order)}

    def sort_key(term: TermSnapshot) -> tuple[int, str]:
        name = _term_season_name(term)
        if name in rank:
            return (rank[name], "")
        return (len(order), name.casefold())

    return tuple(sorted(terms, key=sort_key))


def find_program_snapshot(
    programs: tuple[ProgramSnapshot, ...],
    identity: ParsedProgramUniqueId,
) -> ProgramSnapshot | None:
    """Match a coordinator program by stable subscription identity."""
    for program in programs:
        if program_identity_matches(program, identity):
            return program
    return None


def _serialize_term_games(term: TermSnapshot) -> list[dict[str, Any]]:
    if term.schedule is None:
        return []

    season = term.team_season.season if term.team_season is not None else None
    games = [
        game
        for game in term.schedule.games
        if game.status is not GameStatus.DELETED
    ]
    games.sort(key=lambda game: (game.date, game.id))
    return [
        game_attribute(ProgramGameRef(game=game, season=season))
        for game in games
    ]


def _serialize_term(term: TermSnapshot) -> dict[str, Any]:
    team_season = term.team_season
    return {
        "season": team_season.season if team_season is not None else None,
        "year": team_season.year if team_season is not None else None,
        "status": term.status.value,
        "games": _serialize_term_games(term),
    }


def build_program_schedule_payload(
    entity_id: str,
    *,
    school_id: str,
    school_name: str,
    applicable_school_year: str,
    program: ProgramSnapshot,
) -> dict[str, Any]:
    """Build the Phase 4 websocket schedule DTO for one program."""
    ordered_terms = sort_term_snapshots_for_presentation(program.terms)
    return {
        "schema_version": SCHEMA_VERSION,
        "entity_id": entity_id,
        "school_id": school_id,
        "school_name": school_name,
        "applicable_school_year": applicable_school_year,
        "sport": program.sport,
        "gender": program.gender,
        "level": program.level,
        "display_label": program_display_label(program),
        "resolution_status": program.resolution_status.value,
        "terms": [_serialize_term(term) for term in ordered_terms],
    }


__all__ = [
    "SCHEMA_VERSION",
    "build_program_schedule_payload",
    "find_program_snapshot",
    "sort_term_snapshots_for_presentation",
]
