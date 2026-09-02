"""Normalized MaxPreps domain models (no parsing or transport)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class GameStatus(StrEnum):
    DELETED = "deleted"
    SCHEDULED = "scheduled"
    FINAL = "final"
    UNKNOWN = "unknown"


class HomeAway(StrEnum):
    HOME = "home"
    AWAY = "away"
    NEUTRAL = "neutral"


@dataclass(frozen=True, slots=True)
class School:
    school_id: str
    canonical_url: str
    name: str
    city: str
    state: str
    zip: str | None = None
    mascot: str | None = None
    mascot_url: str | None = None


@dataclass(frozen=True, slots=True)
class TeamSeason:
    school_id: str
    sport_season_id: str
    canonical_url: str
    sport: str
    gender: str
    level: str
    year: str
    season: str
    all_season_id: str | None = None
    is_published: bool | None = None

    @property
    def display_label(self) -> str:
        return f"{self.gender} {self.level} {self.sport}"

    def identity_key(self) -> tuple[str, str]:
        """Composite team-season identity; sport_season_id alone is not globally unique."""
        return (self.school_id, self.sport_season_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TeamSeason):
            return NotImplemented
        return self.identity_key() == other.identity_key()

    def __hash__(self) -> int:
        return hash(self.identity_key())


@dataclass(frozen=True, slots=True)
class Game:
    id: str
    date: datetime
    status: GameStatus
    team_name: str
    opponent_name: str
    home_away: HomeAway
    opponent_id: str | None = None
    team_score: int | None = None
    opponent_score: int | None = None
    result: str | None = None
    venue: str | None = None
    game_url: str | None = None
    status_message: str | None = None


@dataclass(frozen=True, slots=True)
class Schedule:
    team_season: TeamSeason
    games: list[Game] = field(default_factory=list)
    team_logo: str | None = None
    team_record: str | None = None
