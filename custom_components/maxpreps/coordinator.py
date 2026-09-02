"""DataUpdateCoordinator for MaxPreps school entries."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from custom_components.maxpreps import client_factory
from custom_components.maxpreps.const import (
    CONF_CANONICAL_URL,
    CONF_CITY,
    CONF_GENDER,
    CONF_LEVEL,
    CONF_MASCOT,
    CONF_MASCOT_URL,
    CONF_NAME,
    CONF_SCHOOL_ID,
    CONF_SPORT,
    CONF_STATE,
    CONF_SUBSCRIPTIONS,
    DOMAIN,
    UPDATE_INTERVAL,
)
from custom_components.maxpreps.exceptions import MaxPrepsError
from custom_components.maxpreps.models import Schedule, School, TeamSeason
from custom_components.maxpreps.school_year import applicable_school_year
from custom_components.maxpreps import school_year
from custom_components.maxpreps.selection import team_seasons_for_applicable_year

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from custom_components.maxpreps.async_client import AsyncMaxPrepsClient

_LOGGER = logging.getLogger(__name__)


class TermRefreshStatus(StrEnum):
    """Per-term schedule refresh outcome for the current coordinator cycle."""

    REFRESHED = "refreshed"
    STALE = "stale"
    ERROR = "error"


class ProgramResolutionStatus(StrEnum):
    """Whether a subscription resolved to provider rows for the applicable year."""

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


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


def school_from_entry(entry: ConfigEntry) -> School:
    """Build a ``School`` model from stable config-entry data."""
    return School(
        school_id=entry.data[CONF_SCHOOL_ID],
        canonical_url=entry.data[CONF_CANONICAL_URL],
        name=entry.data[CONF_NAME],
        city=entry.data.get(CONF_CITY),
        state=entry.data.get(CONF_STATE),
        mascot=entry.data.get(CONF_MASCOT),
        mascot_url=entry.data.get(CONF_MASCOT_URL),
    )


def _subscription_key(subscription: dict[str, str]) -> tuple[str, str, str]:
    return (subscription[CONF_SPORT], subscription[CONF_GENDER], subscription[CONF_LEVEL])


def _match_subscription_rows(
    team_seasons: list[TeamSeason],
    subscription: dict[str, str],
    applicable_year: str,
) -> list[TeamSeason]:
    sport, gender, level = _subscription_key(subscription)
    return [
        team_season
        for team_season in team_seasons
        if team_season.sport == sport
        and team_season.gender == gender
        and team_season.level == level
        and team_season.year == applicable_year
    ]


def _prior_term_snapshot(
    prior_program: ProgramSnapshot | None,
    team_season: TeamSeason,
) -> TermSnapshot | None:
    if prior_program is None:
        return None
    for term in prior_program.terms:
        if term.team_season is not None and term.team_season == team_season:
            return term
    return None


async def _refresh_term(
    client: AsyncMaxPrepsClient,
    team_season: TeamSeason,
    prior: TermSnapshot | None,
) -> TermSnapshot:
    try:
        schedule = await client.get_schedule(team_season)
        return TermSnapshot(
            team_season=schedule.team_season,
            schedule=schedule,
            status=TermRefreshStatus.REFRESHED,
            error_type=None,
            error_message=None,
            last_success_at=dt_util.utcnow(),
        )
    except MaxPrepsError as err:
        if prior is not None and prior.schedule is not None:
            return TermSnapshot(
                team_season=prior.team_season,
                schedule=prior.schedule,
                status=TermRefreshStatus.STALE,
                error_type=type(err).__name__,
                error_message=str(err),
                last_success_at=prior.last_success_at,
            )
        return TermSnapshot(
            team_season=team_season,
            schedule=None,
            status=TermRefreshStatus.ERROR,
            error_type=type(err).__name__,
            error_message=str(err),
            last_success_at=None,
        )


async def _build_program_snapshot(
    client: AsyncMaxPrepsClient,
    subscription: dict[str, str],
    team_seasons: list[TeamSeason],
    applicable_year: str,
    prior_program: ProgramSnapshot | None,
) -> ProgramSnapshot:
    sport, gender, level = _subscription_key(subscription)
    matching_rows = _match_subscription_rows(team_seasons, subscription, applicable_year)

    if not matching_rows:
        return ProgramSnapshot(
            sport=sport,
            gender=gender,
            level=level,
            resolution_status=ProgramResolutionStatus.UNRESOLVED,
            terms=(),
        )

    term_snapshots: list[TermSnapshot] = []
    for team_season in matching_rows:
        prior_term = _prior_term_snapshot(prior_program, team_season)
        term_snapshots.append(
            await _refresh_term(client, team_season, prior_term)
        )

    return ProgramSnapshot(
        sport=sport,
        gender=gender,
        level=level,
        resolution_status=ProgramResolutionStatus.RESOLVED,
        terms=tuple(term_snapshots),
    )


class MaxPrepsDataUpdateCoordinator(DataUpdateCoordinator[MaxPrepsCoordinatorData]):
    """Coordinator for one MaxPreps school config entry."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.config_entry = entry

    async def _async_update_data(self) -> MaxPrepsCoordinatorData:
        school = school_from_entry(self.config_entry)
        local_date = school_year.homeassistant_local_date(self.hass)
        applicable_year = applicable_school_year(local_date)
        client = client_factory.create_async_client(self.hass)

        try:
            team_seasons = await client.get_school_teams(school)
        except MaxPrepsError as err:
            raise UpdateFailed(f"School home fetch failed: {err}") from err

        subscriptions = self.config_entry.options.get(CONF_SUBSCRIPTIONS, [])
        prior_data = self.data
        prior_programs: dict[tuple[str, str, str], ProgramSnapshot] = {}
        if prior_data is not None:
            for program in prior_data.programs:
                prior_programs[(program.sport, program.gender, program.level)] = program

        programs: list[ProgramSnapshot] = []
        for subscription in subscriptions:
            key = _subscription_key(subscription)
            programs.append(
                await _build_program_snapshot(
                    client,
                    subscription,
                    team_seasons,
                    applicable_year,
                    prior_programs.get(key),
                )
            )

        return MaxPrepsCoordinatorData(
            school=school,
            applicable_school_year=applicable_year,
            programs=tuple(programs),
            refreshed_at=dt_util.utcnow(),
        )


__all__ = [
    "MaxPrepsCoordinatorData",
    "MaxPrepsDataUpdateCoordinator",
    "ProgramResolutionStatus",
    "ProgramSnapshot",
    "TermRefreshStatus",
    "TermSnapshot",
    "school_from_entry",
]
