"""Coordinator tests using fixture transport only."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest

pytest.importorskip("homeassistant")

from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.maxpreps.async_client import AsyncMaxPrepsClient
from custom_components.maxpreps.const import (
    CONF_GENDER,
    CONF_LEVEL,
    CONF_SPORT,
    CONF_SUBSCRIPTIONS,
    UPDATE_INTERVAL,
)
from custom_components.maxpreps.coordinator import (
    MaxPrepsDataUpdateCoordinator,
    ProgramResolutionStatus,
    TermRefreshStatus,
)
from custom_components.maxpreps.exceptions import ContestSchemaError, MaxPrepsError
from custom_components.maxpreps.models import TeamSeason
from custom_components.maxpreps.parsing.sport_seasons import parse_sport_seasons
from custom_components.maxpreps.urls import build_schedule_url
from tests.helpers.async_fixture_transport import AsyncFixtureTransport
from tests.helpers.fixtures import load_sport_seasons, wrap_page_props_in_html
from tests.helpers.schedule_page_props_builder import build_minimal_schedule_page_props
from tests.helpers.coordinator_test_helpers import centennial_entry, FROZEN_APPLICABLE_DATE
from tests.test_client import CENTENNIAL_FOOTBALL_SCHEDULE_URL
from tests.test_search import CENTENNIAL, CENTENNIAL_ROSWELL_URL

FRESHMAN_BASEBALL_SPRING_CANONICAL = (
    "https://www.maxpreps.com/ga/roswell/centennial-knights/baseball/freshman/"
)
FROSH_BASEBALL_FALL_CANONICAL = (
    "https://www.maxpreps.com/ga/roswell/centennial-knights/baseball/freshman/fall/"
)
FRESHMAN_BASEBALL_SPRING_SCHEDULE_URL = build_schedule_url(
    FRESHMAN_BASEBALL_SPRING_CANONICAL
)
FRESHMAN_BASEBALL_FALL_SCHEDULE_URL = build_schedule_url(FROSH_BASEBALL_FALL_CANONICAL)
FRESHMAN_BASEBALL_SPRING_ID = "631feb7b-f4f4-44d1-96b7-a75a2b6507ed"
FRESHMAN_BASEBALL_FALL_ID = "519650ec-c701-4eee-ab7f-1b3026a0e2b3"
FOOTBALL_SUBSCRIPTION = {
    CONF_SPORT: "Football",
    CONF_GENDER: "Boys",
    CONF_LEVEL: "Varsity",
}
FRESHMAN_BASEBALL_SUBSCRIPTION = {
    CONF_SPORT: "Baseball",
    CONF_GENDER: "Boys",
    CONF_LEVEL: "Freshman",
}
UNRESOLVED_SUBSCRIPTION = {
    CONF_SPORT: "Football",
    CONF_GENDER: "Girls",
    CONF_LEVEL: "Varsity",
}


def _centennial_team_seasons() -> list[TeamSeason]:
    rows = load_sport_seasons(f"{CENTENNIAL}/sport-seasons-26-27.json")
    return parse_sport_seasons(rows)


def _freshman_baseball_spring() -> TeamSeason:
    for team_season in _centennial_team_seasons():
        if team_season.sport_season_id == FRESHMAN_BASEBALL_SPRING_ID:
            return team_season
    raise AssertionError("freshman baseball spring row not found")


def _freshman_baseball_fall() -> TeamSeason:
    for team_season in _centennial_team_seasons():
        if team_season.sport_season_id == FRESHMAN_BASEBALL_FALL_ID:
            return team_season
    raise AssertionError("freshman baseball fall row not found")


class CoordinatorTestTransport:
    """Fixture transport with freshman baseball schedule mappings and optional failures."""

    def __init__(
        self,
        *,
        fail_urls: frozenset[str] = frozenset(),
        school_home_fail: bool = False,
    ) -> None:
        self._base = AsyncFixtureTransport()
        self._fail_urls = fail_urls
        self._school_home_fail = school_home_fail
        self._extra_html: dict[str, str] = {}
        self._register_freshman_baseball_schedules()

    def _register_freshman_baseball_schedules(self) -> None:
        spring = _freshman_baseball_spring()
        fall = _freshman_baseball_fall()
        self._extra_html[FRESHMAN_BASEBALL_SPRING_SCHEDULE_URL] = wrap_page_props_in_html(
            build_minimal_schedule_page_props(spring)
        )
        self._extra_html[FRESHMAN_BASEBALL_FALL_SCHEDULE_URL] = wrap_page_props_in_html(
            build_minimal_schedule_page_props(fall)
        )

    @property
    def requested_urls(self) -> list[str]:
        return self._base.requested_urls

    async def fetch(self, url: str) -> str:
        if self._school_home_fail and url == CENTENNIAL_ROSWELL_URL:
            raise MaxPrepsError("simulated school-home failure")
        if url in self._fail_urls:
            raise ContestSchemaError(f"simulated schedule failure for {url}")
        if url in self._extra_html:
            self._base.requested_urls.append(url)
            return self._extra_html[url]
        return await self._base.fetch(url)


def _centennial_entry(
  subscriptions: list[dict[str, str]],
) -> MockConfigEntry:
    return centennial_entry(subscriptions)


@pytest.fixture
def frozen_applicable_date():
    with patch(
        "custom_components.maxpreps.school_year.homeassistant_local_date",
        return_value=FROZEN_APPLICABLE_DATE,
    ):
        yield FROZEN_APPLICABLE_DATE


@pytest.fixture
def coordinator_client():
    transport = CoordinatorTestTransport()
    client = AsyncMaxPrepsClient(transport)
    with patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=client,
    ):
        yield client, transport


def _program_by_subscription(coordinator, subscription: dict[str, str]):
    data = coordinator.data
    assert data is not None
    for program in data.programs:
        if (
            program.sport == subscription[CONF_SPORT]
            and program.gender == subscription[CONF_GENDER]
            and program.level == subscription[CONF_LEVEL]
        ):
            return program
    raise AssertionError(f"program not found for {subscription!r}")


@pytest.mark.asyncio
async def test_update_interval_is_twelve_hours() -> None:
    assert UPDATE_INTERVAL.total_seconds() == 12 * 60 * 60


@pytest.mark.asyncio
async def test_success_snapshot_football_and_multi_term_freshman_baseball(
    hass, enable_custom_integrations, coordinator_client, frozen_applicable_date
) -> None:
    """Football has one term; freshman baseball has two schedule fetches and two terms."""
    _, transport = coordinator_client
    entry = _centennial_entry(
        [FOOTBALL_SUBSCRIPTION, FRESHMAN_BASEBALL_SUBSCRIPTION]
    )
    entry.add_to_hass(hass)

    coordinator = MaxPrepsDataUpdateCoordinator(hass, entry)
    await coordinator.async_refresh()

    football = _program_by_subscription(coordinator, FOOTBALL_SUBSCRIPTION)
    freshman = _program_by_subscription(coordinator, FRESHMAN_BASEBALL_SUBSCRIPTION)

    assert football.resolution_status == ProgramResolutionStatus.RESOLVED
    assert len(football.terms) == 1
    assert football.terms[0].status == TermRefreshStatus.REFRESHED

    assert freshman.resolution_status == ProgramResolutionStatus.RESOLVED
    assert len(freshman.terms) == 2
    seasons = {term.team_season.season for term in freshman.terms}
    assert seasons == {"Fall", "Spring"}
    assert freshman.terms[0].status == TermRefreshStatus.REFRESHED
    assert freshman.terms[1].status == TermRefreshStatus.REFRESHED

    assert CENTENNIAL_FOOTBALL_SCHEDULE_URL in transport.requested_urls
    assert FRESHMAN_BASEBALL_SPRING_SCHEDULE_URL in transport.requested_urls
    assert FRESHMAN_BASEBALL_FALL_SCHEDULE_URL in transport.requested_urls


@pytest.mark.asyncio
async def test_one_freshman_baseball_term_failure_isolates_siblings(
    hass, enable_custom_integrations, frozen_applicable_date
) -> None:
    """One freshman term error does not drop the sibling term or football."""
    transport = CoordinatorTestTransport(
        fail_urls=frozenset({FRESHMAN_BASEBALL_SPRING_SCHEDULE_URL})
    )
    client = AsyncMaxPrepsClient(transport)
    with patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=client,
    ):
        entry = _centennial_entry(
            [FOOTBALL_SUBSCRIPTION, FRESHMAN_BASEBALL_SUBSCRIPTION]
        )
        entry.add_to_hass(hass)
        coordinator = MaxPrepsDataUpdateCoordinator(hass, entry)
        await coordinator.async_refresh()

    freshman = _program_by_subscription(coordinator, FRESHMAN_BASEBALL_SUBSCRIPTION)
    football = _program_by_subscription(coordinator, FOOTBALL_SUBSCRIPTION)

    assert len(freshman.terms) == 2
    by_season = {term.team_season.season: term for term in freshman.terms}
    assert by_season["Spring"].status == TermRefreshStatus.ERROR
    assert by_season["Spring"].schedule is None
    assert by_season["Fall"].status == TermRefreshStatus.REFRESHED
    assert football.terms[0].status == TermRefreshStatus.REFRESHED


@pytest.mark.asyncio
async def test_whole_program_schedule_failures_do_not_affect_siblings(
    hass, enable_custom_integrations, frozen_applicable_date
) -> None:
    """When every term in one program fails, other subscribed programs still refresh."""
    transport = CoordinatorTestTransport(
        fail_urls=frozenset(
            {
                FRESHMAN_BASEBALL_SPRING_SCHEDULE_URL,
                FRESHMAN_BASEBALL_FALL_SCHEDULE_URL,
            }
        )
    )
    client = AsyncMaxPrepsClient(transport)
    with patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=client,
    ):
        entry = _centennial_entry(
            [FOOTBALL_SUBSCRIPTION, FRESHMAN_BASEBALL_SUBSCRIPTION]
        )
        entry.add_to_hass(hass)
        coordinator = MaxPrepsDataUpdateCoordinator(hass, entry)
        await coordinator.async_refresh()

    freshman = _program_by_subscription(coordinator, FRESHMAN_BASEBALL_SUBSCRIPTION)
    football = _program_by_subscription(coordinator, FOOTBALL_SUBSCRIPTION)

    assert all(term.status == TermRefreshStatus.ERROR for term in freshman.terms)
    assert football.terms[0].status == TermRefreshStatus.REFRESHED


@pytest.mark.asyncio
async def test_school_home_failure_after_success_raises_update_failed_retains_data(
    hass, enable_custom_integrations, frozen_applicable_date
) -> None:
    """Entry-wide school-home failure retains the last snapshot."""
    transport = CoordinatorTestTransport()
    client = AsyncMaxPrepsClient(transport)
    with patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=client,
    ):
        entry = _centennial_entry([FRESHMAN_BASEBALL_SUBSCRIPTION])
        entry.add_to_hass(hass)
        coordinator = MaxPrepsDataUpdateCoordinator(hass, entry)
        await coordinator.async_refresh()

        prior = coordinator.data
        assert prior is not None
        assert len(prior.programs[0].terms) == 2

        failing_transport = CoordinatorTestTransport(school_home_fail=True)
        failing_client = AsyncMaxPrepsClient(failing_transport)
        with patch(
            "custom_components.maxpreps.client_factory.create_async_client",
            return_value=failing_client,
        ):
            await coordinator.async_refresh()

        assert coordinator.data == prior
        assert not coordinator.last_update_success


@pytest.mark.asyncio
async def test_first_setup_school_home_failure_raises_config_entry_not_ready(
    hass, enable_custom_integrations, frozen_applicable_date
) -> None:
    transport = CoordinatorTestTransport(school_home_fail=True)
    client = AsyncMaxPrepsClient(transport)
    with patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=client,
    ):
        entry = _centennial_entry([FOOTBALL_SUBSCRIPTION])
        entry.add_to_hass(hass)

        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state == ConfigEntryState.SETUP_RETRY


@pytest.mark.asyncio
async def test_unresolved_subscription_has_unavailable_payload(
    hass, enable_custom_integrations, frozen_applicable_date
) -> None:
    """Subscription with no applicable-year rows is unresolved; options unchanged."""
    transport = CoordinatorTestTransport()
    client = AsyncMaxPrepsClient(transport)
    subscriptions = [FOOTBALL_SUBSCRIPTION, UNRESOLVED_SUBSCRIPTION]
    with patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=client,
    ):
        entry = _centennial_entry(subscriptions)
        entry.add_to_hass(hass)
        coordinator = MaxPrepsDataUpdateCoordinator(hass, entry)
        await coordinator.async_refresh()

    unresolved = _program_by_subscription(coordinator, UNRESOLVED_SUBSCRIPTION)
    assert unresolved.resolution_status == ProgramResolutionStatus.UNRESOLVED
    assert unresolved.terms == ()
    assert entry.options[CONF_SUBSCRIPTIONS] == subscriptions


@pytest.mark.asyncio
async def test_stale_term_retains_last_good_schedule_on_refresh_failure(
    hass, enable_custom_integrations, frozen_applicable_date
) -> None:
    """A previously successful term keeps its schedule when the next refresh fails."""
    transport = CoordinatorTestTransport()
    client = AsyncMaxPrepsClient(transport)
    with patch(
        "custom_components.maxpreps.client_factory.create_async_client",
        return_value=client,
    ):
        entry = _centennial_entry(
            [FOOTBALL_SUBSCRIPTION, FRESHMAN_BASEBALL_SUBSCRIPTION]
        )
        entry.add_to_hass(hass)
        coordinator = MaxPrepsDataUpdateCoordinator(hass, entry)
        await coordinator.async_refresh()

        spring_before = next(
            term
            for term in _program_by_subscription(
                coordinator, FRESHMAN_BASEBALL_SUBSCRIPTION
            ).terms
            if term.team_season.season == "Spring"
        )
        assert spring_before.status == TermRefreshStatus.REFRESHED
        assert spring_before.schedule is not None

        failing_transport = CoordinatorTestTransport(
            fail_urls=frozenset({FRESHMAN_BASEBALL_SPRING_SCHEDULE_URL})
        )
        failing_client = AsyncMaxPrepsClient(failing_transport)
        with patch(
            "custom_components.maxpreps.client_factory.create_async_client",
            return_value=failing_client,
        ):
            await coordinator.async_refresh()

    freshman = _program_by_subscription(coordinator, FRESHMAN_BASEBALL_SUBSCRIPTION)
    football = _program_by_subscription(coordinator, FOOTBALL_SUBSCRIPTION)
    by_season = {term.team_season.season: term for term in freshman.terms}

    assert by_season["Spring"].status == TermRefreshStatus.STALE
    assert by_season["Spring"].schedule is spring_before.schedule
    assert by_season["Spring"].error_type == "ContestSchemaError"
    assert by_season["Fall"].status == TermRefreshStatus.REFRESHED
    assert football.terms[0].status == TermRefreshStatus.REFRESHED


@pytest.mark.asyncio
async def test_setup_entry_wires_coordinator_without_live_http(
    hass, enable_custom_integrations, coordinator_client, frozen_applicable_date
) -> None:
    entry = _centennial_entry([FOOTBALL_SUBSCRIPTION])
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is not None
    assert entry.runtime_data.data is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
