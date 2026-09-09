"""Slice 11 — school-year rollover retention and polling (fixture transport only)."""

from __future__ import annotations

import copy
from datetime import date
from unittest.mock import patch

import pytest

pytest.importorskip("homeassistant")

from homeassistant.helpers import entity_registry as er

from custom_components.maxpreps.async_client import AsyncMaxPrepsClient
from custom_components.maxpreps.const import (
    ROLLOVER_UPDATE_INTERVAL,
    UPDATE_INTERVAL,
)
from custom_components.maxpreps.coordinator import (
    MaxPrepsDataUpdateCoordinator,
    ProgramResolutionStatus,
    TermRefreshStatus,
)
from custom_components.maxpreps.models import TeamSeason
from custom_components.maxpreps.parsing.sport_seasons import parse_sport_seasons
from custom_components.maxpreps.program_sensor import (
    find_last_game,
    program_is_available,
    program_unique_id,
)
from custom_components.maxpreps.school_year import applicable_school_year
from custom_components.maxpreps.urls import build_schedule_url
from tests.helpers.coordinator_test_helpers import centennial_entry
from tests.helpers.fixtures import load_schedule_page_props, load_sport_seasons, wrap_page_props_in_html
from tests.helpers.schedule_page_props_builder import build_minimal_schedule_page_props
from tests.test_client import CENTENNIAL_FOOTBALL_SCHEDULE_URL
from tests.test_coordinator import (
    FRESHMAN_BASEBALL_FALL_SCHEDULE_URL,
    FRESHMAN_BASEBALL_SPRING_SCHEDULE_URL,
    FRESHMAN_BASEBALL_SUBSCRIPTION,
    FOOTBALL_SUBSCRIPTION,
    CoordinatorTestTransport,
    _program_by_subscription,
)
from tests.test_search import CENTENNIAL_ROSWELL_ID, CENTENNIAL_ROSWELL_URL

SEPTEMBER_2026 = date(2026, 9, 2)
JULY_1_2027 = date(2027, 7, 1)

FOOTBALL_27_28_SPORT_SEASON_ID = "f8e3a1b2-4c5d-6e7f-8091-a2b3c4d5e6f7"
FRESHMAN_BASEBALL_FALL_27_28_ID = "aabbccdd-1111-2222-3333-444455556666"
FRESHMAN_BASEBALL_SPRING_27_28_ID = "aabbccdd-7777-8888-9999-aaaabbbbcccc"

FOOTBALL_UNIQUE_ID = f"{CENTENNIAL_ROSWELL_ID}:Boys:Varsity:Football"
FRESHMAN_BASEBALL_UNIQUE_ID = f"{CENTENNIAL_ROSWELL_ID}:Boys:Freshman:Baseball"


def _centennial_sport_season_rows() -> list[dict]:
    return copy.deepcopy(load_sport_seasons("centennial/sport-seasons-26-27.json"))


def _row_for_program(
    rows: list[dict],
    *,
    sport: str,
    gender: str,
    level: str,
) -> dict:
    for row in rows:
        if (
            row["sport"] == sport
            and row["gender"] == gender
            and row["level"] == level
        ):
            return row
    raise AssertionError(f"row not found for {sport}/{gender}/{level}")


def _rows_for_program(
    rows: list[dict],
    *,
    sport: str,
    gender: str,
    level: str,
) -> list[dict]:
    return [
        row
        for row in rows
        if row["sport"] == sport
        and row["gender"] == gender
        and row["level"] == level
    ]


def _clone_row_for_year(row: dict, year: str, sport_season_id: str) -> dict:
    cloned = copy.deepcopy(row)
    cloned["year"] = year
    cloned["sportSeasonId"] = sport_season_id
    return cloned


def _school_home_html(rows: list[dict]) -> str:
    return wrap_page_props_in_html({"schoolContext": {"sportSeasons": rows}})


class RolloverTestTransport:
    """Fixture transport with synthetic school-home rows and schedule mappings."""

    def __init__(
        self,
        *,
        school_home_rows: list[dict] | None = None,
        fail_urls: frozenset[str] = frozenset(),
        extra_schedule_html: dict[str, str] | None = None,
    ) -> None:
        self._fail_urls = fail_urls
        self._base = CoordinatorTestTransport(fail_urls=fail_urls)
        self._school_home_rows = school_home_rows
        self._extra_schedule_html = extra_schedule_html or {}
        self._register_default_schedules()

    def _register_default_schedules(self) -> None:
        if CENTENNIAL_FOOTBALL_SCHEDULE_URL not in self._extra_schedule_html:
            page_props = load_schedule_page_props("centennial/schedule-26-27.json")
            assert page_props is not None
            self._extra_schedule_html[CENTENNIAL_FOOTBALL_SCHEDULE_URL] = (
                wrap_page_props_in_html(page_props)
            )

    @property
    def requested_urls(self) -> list[str]:
        return self._base.requested_urls

    async def fetch(self, url: str) -> str:
        if url == CENTENNIAL_ROSWELL_URL and self._school_home_rows is not None:
            self._base.requested_urls.append(url)
            return _school_home_html(self._school_home_rows)
        if url in self._fail_urls:
            return await self._base.fetch(url)
        if url in self._extra_schedule_html:
            self._base.requested_urls.append(url)
            return self._extra_schedule_html[url]
        return await self._base.fetch(url)


def _football_team_season(year: str, sport_season_id: str) -> TeamSeason:
    rows = _centennial_sport_season_rows()
    row = _clone_row_for_year(
        _row_for_program(rows, sport="Football", gender="Boys", level="Varsity"),
        year,
        sport_season_id,
    )
    return parse_sport_seasons([row])[0]


def _freshman_baseball_team_seasons(year: str) -> list[TeamSeason]:
    rows = _centennial_sport_season_rows()
    program_rows = _rows_for_program(
        rows, sport="Baseball", gender="Boys", level="Freshman"
    )
    if year == "27-28":
        ids = {
            "Fall": FRESHMAN_BASEBALL_FALL_27_28_ID,
            "Spring": FRESHMAN_BASEBALL_SPRING_27_28_ID,
        }
        cloned = [
            _clone_row_for_year(row, year, ids[row["season"]]) for row in program_rows
        ]
    else:
        cloned = program_rows
    return parse_sport_seasons(cloned)


def _register_freshman_baseball_schedules(
    transport: RolloverTestTransport,
    year: str,
) -> None:
    for team_season in _freshman_baseball_team_seasons(year):
        schedule_url = build_schedule_url(team_season.canonical_url)
        transport._extra_schedule_html[schedule_url] = wrap_page_props_in_html(
            build_minimal_schedule_page_props(team_season)
        )


@pytest.fixture
def patch_local_date():
    """Yield a callable that sets homeassistant_local_date for the test."""

    def _apply(local_date: date):
        return patch(
            "custom_components.maxpreps.school_year.homeassistant_local_date",
            return_value=local_date,
        )

    return _apply


def _state_for_unique_id(hass, entry, unique_id: str):
    registry = er.async_get(hass)
    entity = next(
        entity
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
        if entity.unique_id == unique_id
    )
    return hass.states.get(entity.entity_id)


@pytest.mark.asyncio
async def test_september_2026_applicable_year_and_football_unique_id(
    hass, enable_custom_integrations, patch_local_date
) -> None:
    transport = RolloverTestTransport()
    client = AsyncMaxPrepsClient(transport)
    entry = centennial_entry([FOOTBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)

    with patch_local_date(SEPTEMBER_2026), patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=client,
    ):
        coordinator = MaxPrepsDataUpdateCoordinator(hass, entry)
        await coordinator.async_refresh()

    assert applicable_school_year(SEPTEMBER_2026) == "26-27"
    assert coordinator.data is not None
    assert coordinator.data.applicable_school_year == "26-27"

    football = _program_by_subscription(coordinator, FOOTBALL_SUBSCRIPTION)
    assert football.resolution_status == ProgramResolutionStatus.RESOLVED
    assert program_unique_id(CENTENNIAL_ROSWELL_ID, football) == FOOTBALL_UNIQUE_ID
    assert coordinator.update_interval == UPDATE_INTERVAL


@pytest.mark.asyncio
async def test_july_1_rollover_retains_last_good_without_new_year_rows(
    hass, enable_custom_integrations, patch_local_date
) -> None:
    """After July 1 with no 27-28 football row, last-good 26-27 data stays available."""
    transport = RolloverTestTransport()
    client = AsyncMaxPrepsClient(transport)
    entry = centennial_entry([FOOTBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)

    with patch_local_date(SEPTEMBER_2026), patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=client,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    coordinator = entry.runtime_data
    football_before = _program_by_subscription(coordinator, FOOTBALL_SUBSCRIPTION)
    assert football_before.terms[0].schedule is not None
    assert find_last_game(football_before) is not None

    with patch_local_date(JULY_1_2027), patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=client,
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    assert coordinator.data is not None
    assert coordinator.data.applicable_school_year == "27-28"
    football = _program_by_subscription(coordinator, FOOTBALL_SUBSCRIPTION)
    assert football.resolution_status == ProgramResolutionStatus.WAITING_FOR_APPLICABLE_YEAR
    assert football.terms[0].status == TermRefreshStatus.STALE
    assert football.terms[0].team_season.year == "26-27"
    assert football.terms[0].schedule is football_before.terms[0].schedule
    assert program_is_available(football) is True
    assert coordinator.update_interval == ROLLOVER_UPDATE_INTERVAL
    assert ROLLOVER_UPDATE_INTERVAL.total_seconds() <= 24 * 60 * 60

    registry = er.async_get(hass)
    entity = next(
        entity
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
        if entity.unique_id == FOOTBALL_UNIQUE_ID
    )
    state = hass.states.get(entity.entity_id)
    assert state.state != "unavailable"
    assert "last_game" in state.attributes


@pytest.mark.asyncio
async def test_27_28_football_row_appears_restores_twelve_hour_interval(
    hass, enable_custom_integrations, patch_local_date
) -> None:
    rows_26_27 = _centennial_sport_season_rows()
    football_27_28 = _clone_row_for_year(
        _row_for_program(rows_26_27, sport="Football", gender="Boys", level="Varsity"),
        "27-28",
        FOOTBALL_27_28_SPORT_SEASON_ID,
    )
    rows_with_27_28 = rows_26_27 + [football_27_28]

    waiting_transport = RolloverTestTransport()
    client = AsyncMaxPrepsClient(waiting_transport)
    entry = centennial_entry([FOOTBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)

    with patch_local_date(SEPTEMBER_2026), patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=client,
    ):
        coordinator = MaxPrepsDataUpdateCoordinator(hass, entry)
        await coordinator.async_refresh()

    with patch_local_date(JULY_1_2027), patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=client,
    ):
        await coordinator.async_refresh()

    assert coordinator.update_interval == ROLLOVER_UPDATE_INTERVAL

    published_transport = RolloverTestTransport(school_home_rows=rows_with_27_28)
    football_27_28_team = _football_team_season("27-28", FOOTBALL_27_28_SPORT_SEASON_ID)
    published_transport._extra_schedule_html[CENTENNIAL_FOOTBALL_SCHEDULE_URL] = (
        wrap_page_props_in_html(build_minimal_schedule_page_props(football_27_28_team))
    )
    published_client = AsyncMaxPrepsClient(published_transport)
    with patch_local_date(JULY_1_2027), patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=published_client,
    ):
        await coordinator.async_refresh()

    football = _program_by_subscription(coordinator, FOOTBALL_SUBSCRIPTION)
    assert football.resolution_status == ProgramResolutionStatus.RESOLVED
    assert len(football.terms) == 1
    assert football.terms[0].team_season.year == "27-28"
    assert football.terms[0].status == TermRefreshStatus.REFRESHED
    assert CENTENNIAL_FOOTBALL_SCHEDULE_URL in published_transport.requested_urls
    assert coordinator.update_interval == UPDATE_INTERVAL
    assert program_unique_id(CENTENNIAL_ROSWELL_ID, football) == FOOTBALL_UNIQUE_ID


@pytest.mark.asyncio
async def test_multi_term_27_28_freshman_baseball_two_fetches_one_entity(
    hass, enable_custom_integrations, patch_local_date
) -> None:
    rows_26_27 = _centennial_sport_season_rows()
    freshman_rows = _rows_for_program(
        rows_26_27, sport="Baseball", gender="Boys", level="Freshman"
    )
    rows_27_28 = [
        _clone_row_for_year(
            row,
            "27-28",
            FRESHMAN_BASEBALL_FALL_27_28_ID
            if row["season"] == "Fall"
            else FRESHMAN_BASEBALL_SPRING_27_28_ID,
        )
        for row in freshman_rows
    ]
    transport = RolloverTestTransport(school_home_rows=rows_27_28)
    _register_freshman_baseball_schedules(transport, "27-28")
    client = AsyncMaxPrepsClient(transport)
    entry = centennial_entry([FRESHMAN_BASEBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)

    with patch_local_date(JULY_1_2027), patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=client,
    ):
        coordinator = MaxPrepsDataUpdateCoordinator(hass, entry)
        await coordinator.async_refresh()

    freshman = _program_by_subscription(coordinator, FRESHMAN_BASEBALL_SUBSCRIPTION)
    assert freshman.resolution_status == ProgramResolutionStatus.RESOLVED
    assert len(freshman.terms) == 2
    seasons = {term.team_season.season for term in freshman.terms}
    assert seasons == {"Fall", "Spring"}
    assert all(term.team_season.year == "27-28" for term in freshman.terms)
    assert FRESHMAN_BASEBALL_FALL_SCHEDULE_URL in transport.requested_urls
    assert FRESHMAN_BASEBALL_SPRING_SCHEDULE_URL in transport.requested_urls
    assert program_unique_id(CENTENNIAL_ROSWELL_ID, freshman) == FRESHMAN_BASEBALL_UNIQUE_ID


@pytest.mark.asyncio
async def test_coexistence_of_adjacent_years_does_not_abort(
    hass, enable_custom_integrations, patch_local_date
) -> None:
    """26-27 leftovers plus 27-28 majority rows do not trigger modal ambiguity."""
    rows_26_27 = _centennial_sport_season_rows()
    football_27_28 = _clone_row_for_year(
        _row_for_program(rows_26_27, sport="Football", gender="Boys", level="Varsity"),
        "27-28",
        FOOTBALL_27_28_SPORT_SEASON_ID,
    )
    rows_mixed = rows_26_27 + [football_27_28]

    transport = RolloverTestTransport(school_home_rows=rows_mixed)
    football_27_28_team = _football_team_season("27-28", FOOTBALL_27_28_SPORT_SEASON_ID)
    transport._extra_schedule_html[CENTENNIAL_FOOTBALL_SCHEDULE_URL] = (
        wrap_page_props_in_html(build_minimal_schedule_page_props(football_27_28_team))
    )
    client = AsyncMaxPrepsClient(transport)
    entry = centennial_entry([FOOTBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)

    with patch_local_date(JULY_1_2027), patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=client,
    ):
        coordinator = MaxPrepsDataUpdateCoordinator(hass, entry)
        await coordinator.async_refresh()

    football = _program_by_subscription(coordinator, FOOTBALL_SUBSCRIPTION)
    assert football.resolution_status == ProgramResolutionStatus.RESOLVED
    assert football.terms[0].team_season.year == "27-28"


@pytest.mark.asyncio
async def test_27_28_row_with_failing_schedule_keeps_prior_year_until_success(
    hass, enable_custom_integrations, patch_local_date
) -> None:
    rows_26_27 = _centennial_sport_season_rows()
    football_27_28 = _clone_row_for_year(
        _row_for_program(rows_26_27, sport="Football", gender="Boys", level="Varsity"),
        "27-28",
        FOOTBALL_27_28_SPORT_SEASON_ID,
    )
    rows_with_27_28 = rows_26_27 + [football_27_28]

    waiting_transport = RolloverTestTransport()
    client = AsyncMaxPrepsClient(waiting_transport)
    entry = centennial_entry([FOOTBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)

    with patch_local_date(SEPTEMBER_2026), patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=client,
    ):
        coordinator = MaxPrepsDataUpdateCoordinator(hass, entry)
        await coordinator.async_refresh()

    with patch_local_date(JULY_1_2027), patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=client,
    ):
        await coordinator.async_refresh()

    football_waiting = _program_by_subscription(coordinator, FOOTBALL_SUBSCRIPTION)
    assert football_waiting.resolution_status == (
        ProgramResolutionStatus.WAITING_FOR_APPLICABLE_YEAR
    )
    prior_schedule = football_waiting.terms[0].schedule
    assert prior_schedule is not None
    assert football_waiting.terms[0].team_season.year == "26-27"

    failing_transport = RolloverTestTransport(
        school_home_rows=rows_with_27_28,
        fail_urls=frozenset({CENTENNIAL_FOOTBALL_SCHEDULE_URL}),
    )
    failing_client = AsyncMaxPrepsClient(failing_transport)
    with patch_local_date(JULY_1_2027), patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=failing_client,
    ):
        await coordinator.async_refresh()

    football_failed = _program_by_subscription(coordinator, FOOTBALL_SUBSCRIPTION)
    assert football_failed.resolution_status == (
        ProgramResolutionStatus.WAITING_FOR_APPLICABLE_YEAR
    )
    assert football_failed.terms[0].schedule is prior_schedule
    assert football_failed.terms[0].team_season.year == "26-27"
    assert CENTENNIAL_FOOTBALL_SCHEDULE_URL in failing_transport.requested_urls
    assert coordinator.update_interval == ROLLOVER_UPDATE_INTERVAL

    success_transport = RolloverTestTransport(school_home_rows=rows_with_27_28)
    football_27_28_team = _football_team_season("27-28", FOOTBALL_27_28_SPORT_SEASON_ID)
    success_transport._extra_schedule_html[CENTENNIAL_FOOTBALL_SCHEDULE_URL] = (
        wrap_page_props_in_html(build_minimal_schedule_page_props(football_27_28_team))
    )
    success_client = AsyncMaxPrepsClient(success_transport)
    with patch_local_date(JULY_1_2027), patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=success_client,
    ):
        await coordinator.async_refresh()

    football_success = _program_by_subscription(coordinator, FOOTBALL_SUBSCRIPTION)
    assert football_success.resolution_status == ProgramResolutionStatus.RESOLVED
    assert football_success.terms[0].team_season.year == "27-28"
    assert football_success.terms[0].status == TermRefreshStatus.REFRESHED
    assert coordinator.update_interval == UPDATE_INTERVAL


@pytest.mark.asyncio
async def test_multi_term_rollover_replaces_prior_year_when_both_terms_publish(
    hass, enable_custom_integrations, patch_local_date
) -> None:
    rows_26_27 = _centennial_sport_season_rows()
    freshman_rows = _rows_for_program(
        rows_26_27, sport="Baseball", gender="Boys", level="Freshman"
    )
    rows_27_28 = [
        _clone_row_for_year(
            row,
            "27-28",
            FRESHMAN_BASEBALL_FALL_27_28_ID
            if row["season"] == "Fall"
            else FRESHMAN_BASEBALL_SPRING_27_28_ID,
        )
        for row in freshman_rows
    ]
    rows_mixed = rows_26_27 + rows_27_28

    transport = RolloverTestTransport()
    _register_freshman_baseball_schedules(transport, "26-27")
    client = AsyncMaxPrepsClient(transport)
    entry = centennial_entry([FRESHMAN_BASEBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)

    with patch_local_date(SEPTEMBER_2026), patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=client,
    ):
        coordinator = MaxPrepsDataUpdateCoordinator(hass, entry)
        await coordinator.async_refresh()

    freshman_before = _program_by_subscription(
        coordinator, FRESHMAN_BASEBALL_SUBSCRIPTION
    )
    assert all(term.team_season.year == "26-27" for term in freshman_before.terms)

    published_transport = RolloverTestTransport(school_home_rows=rows_mixed)
    _register_freshman_baseball_schedules(published_transport, "27-28")
    published_client = AsyncMaxPrepsClient(published_transport)
    with patch_local_date(JULY_1_2027), patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=published_client,
    ):
        await coordinator.async_refresh()
        await coordinator.async_refresh()

    freshman_after = _program_by_subscription(
        coordinator, FRESHMAN_BASEBALL_SUBSCRIPTION
    )
    assert freshman_after.resolution_status == ProgramResolutionStatus.RESOLVED
    assert len(freshman_after.terms) == 2
    assert all(term.team_season.year == "27-28" for term in freshman_after.terms)
    assert all(term.status == TermRefreshStatus.REFRESHED for term in freshman_after.terms)
    assert not any(term.team_season.year == "26-27" for term in freshman_after.terms)
    assert coordinator.update_interval == UPDATE_INTERVAL
