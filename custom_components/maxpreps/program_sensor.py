"""Pure helpers for program-level sensor state (no Home Assistant imports)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

from custom_components.maxpreps.coordinator import (
    ProgramResolutionStatus,
    ProgramSnapshot,
)
from custom_components.maxpreps.models import Game, GameStatus


@dataclass(frozen=True, slots=True)
class ProgramGameRef:
    """A non-deleted game from one program term."""

    game: Game
    season: str | None


def program_unique_id(school_id: str, program: ProgramSnapshot) -> str:
    """Stable entity unique ID for a subscribed program."""
    return f"{school_id}:{program.gender}:{program.level}:{program.sport}"


def program_display_label(program: ProgramSnapshot) -> str:
    """Short program label without informational term/year parenthetical."""
    return f"{program.gender} {program.level} {program.sport}"


def iter_program_games(program: ProgramSnapshot) -> Iterator[ProgramGameRef]:
    """Yield non-deleted games across all terms of a program."""
    for term in program.terms:
        if term.schedule is None:
            continue
        season = term.team_season.season if term.team_season is not None else None
        for game in term.schedule.games:
            if game.status is not GameStatus.DELETED:
                yield ProgramGameRef(game=game, season=season)


def find_last_game(program: ProgramSnapshot) -> ProgramGameRef | None:
    """Latest final game by provider-naive datetime (never compared to wall clock)."""
    finals = [
        ref for ref in iter_program_games(program) if ref.game.status is GameStatus.FINAL
    ]
    if not finals:
        return None
    return max(finals, key=lambda ref: ref.game.date)


def find_next_game(program: ProgramSnapshot) -> ProgramGameRef | None:
    """Earliest scheduled game by provider-naive datetime (never compared to wall clock)."""
    scheduled = [
        ref
        for ref in iter_program_games(program)
        if ref.game.status is GameStatus.SCHEDULED
    ]
    if not scheduled:
        return None
    return min(scheduled, key=lambda ref: ref.game.date)


def program_native_value(program: ProgramSnapshot) -> str:
    """Compact sensor state using Phase 2 ``Game.status`` vocabulary only."""
    if find_next_game(program) is not None:
        return GameStatus.SCHEDULED.value
    if find_last_game(program) is not None:
        return GameStatus.FINAL.value
    return GameStatus.UNKNOWN.value


def program_is_available(program: ProgramSnapshot) -> bool:
    """Whether the program sensor should report as available."""
    if program.resolution_status is ProgramResolutionStatus.UNRESOLVED:
        return False
    return any(term.schedule is not None for term in program.terms)


def program_team_record(program: ProgramSnapshot) -> str | None:
    """First trustworthy team record present on any term schedule, if any."""
    for term in program.terms:
        if term.schedule is not None and term.schedule.team_record:
            return term.schedule.team_record
    return None


def game_attribute(ref: ProgramGameRef) -> dict[str, Any]:
    """Serialize one game for entity attributes."""
    game = ref.game
    data: dict[str, Any] = {
        "id": game.id,
        "date": game.date.isoformat(),
        "status": game.status.value,
        "opponent_name": game.opponent_name,
        "home_away": game.home_away.value,
    }
    if game.opponent_id is not None:
        data["opponent_id"] = game.opponent_id
    if game.team_score is not None:
        data["team_score"] = game.team_score
    if game.opponent_score is not None:
        data["opponent_score"] = game.opponent_score
    if game.result is not None:
        data["result"] = game.result
    if game.venue is not None:
        data["venue"] = game.venue
    if game.game_url is not None:
        data["game_url"] = game.game_url
    if ref.season is not None:
        data["season"] = ref.season
    return data
