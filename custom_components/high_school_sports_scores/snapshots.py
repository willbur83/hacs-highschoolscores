"""Coordinator snapshot models (no Home Assistant imports)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from custom_components.high_school_sports_scores.models import Schedule, School, TeamSeason


class TermRefreshStatus(StrEnum):
    """Per-term schedule refresh outcome for the current coordinator cycle."""

    REFRESHED = "refreshed"
    STALE = "stale"
    ERROR = "error"


class ProgramResolutionStatus(StrEnum):
    """Whether a subscription resolved to provider rows for the applicable year."""

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    WAITING_FOR_APPLICABLE_YEAR = "waiting_for_applicable_year"


@dataclass(frozen=True, slots=True)
class TermSnapshot:
    """One TeamSeason term within a subscribed program."""

    team_season: TeamSeason | None
    schedule: Schedule | None
    status: TermRefreshStatus
    error_type: str | None
    error_message: str | None
    last_success_at: datetime | None


@dataclass(frozen=True, slots=True)
class ProgramSnapshot:
    """Coordinator snapshot for one subscribed ``{sport, gender, level}`` program."""

    sport: str
    gender: str
    level: str
    resolution_status: ProgramResolutionStatus
    terms: tuple[TermSnapshot, ...]


@dataclass(frozen=True, slots=True)
class MaxPrepsCoordinatorData:
    """Full coordinator snapshot for one school config entry."""

    school: School
    applicable_school_year: str
    programs: tuple[ProgramSnapshot, ...]
    refreshed_at: datetime


__all__ = [
    "MaxPrepsCoordinatorData",
    "ProgramResolutionStatus",
    "ProgramSnapshot",
    "TermRefreshStatus",
    "TermSnapshot",
]
