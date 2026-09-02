"""Async MaxPreps client facade tests (AsyncFixtureTransport only)."""

from __future__ import annotations

import pytest

from custom_components.maxpreps.async_client import AsyncMaxPrepsClient
from custom_components.maxpreps.client import MaxPrepsClient
from custom_components.maxpreps.exceptions import NextDataNotFoundError, SearchSchemaError
from custom_components.maxpreps.models import GameStatus, TeamSeason
from tests.helpers.async_fixture_transport import AsyncFixtureTransport
from tests.helpers.fixture_transport import FixtureTransport, FixtureUrlNotMappedError
from tests.helpers.fixtures import wrap_page_props_in_html
from tests.test_client import (
    CENTENNIAL_BASEBALL_CANONICAL,
    CENTENNIAL_BASEBALL_SCHEDULE_URL,
    CENTENNIAL_BASKETBALL_GIRLS_SCHEDULE_URL,
    CENTENNIAL_FOOTBALL_CANONICAL,
    CENTENNIAL_FOOTBALL_SCHEDULE_URL,
    CENTENNIAL_ROSWELL_URL,
    CENTENNIAL_SEARCH_URL,
    CENTENNIAL_TENNIS_CANONICAL,
    CENTENNIAL_TENNIS_SCHEDULE_URL,
    CURRENT_YEAR,
    SAINT_EDWARD_SEARCH_URL,
    ST_EDWARD_SEARCH_URL,
    _centennial_roswell_school,
    _find_team,
)
from tests.test_schedule import (
    BASEBALL_SPORT_SEASON_ID,
    FOOTBALL_SPORT_SEASON_ID,
    RIVERWOOD_CONTEST_ID,
)
from tests.test_search import (
    CENTENNIAL_ROSWELL_ID,
    CENTENNIAL_ROSWELL_URL,
    ST_EDWARD_OH_ID,
    ST_EDWARD_OH_URL,
)


class _AsyncSaintSearchOnlyTransport:
    """Serve a fixed HTML body for the Saint Edward search URL only."""

    def __init__(self, html: str) -> None:
        self._html = html
        self.requested_urls: list[str] = []

    async def fetch(self, url: str) -> str:
        self.requested_urls.append(url)
        if url != SAINT_EDWARD_SEARCH_URL:
            raise AssertionError(f"unexpected search URL during error test: {url}")
        return self._html


class _AsyncRaisingSaintSearchTransport:
    """Simulate an unmapped search URL at the transport layer."""

    def __init__(self) -> None:
        self.requested_urls: list[str] = []

    async def fetch(self, url: str) -> str:
        self.requested_urls.append(url)
        raise FixtureUrlNotMappedError(f"No fixture mapped for URL: {url}")


@pytest.fixture
def transport() -> AsyncFixtureTransport:
    return AsyncFixtureTransport()


@pytest.fixture
def client(transport: AsyncFixtureTransport) -> AsyncMaxPrepsClient:
    return AsyncMaxPrepsClient(transport)


async def test_search_schools_centennial(
    client: AsyncMaxPrepsClient,
    transport: AsyncFixtureTransport,
) -> None:
    schools = await client.search_schools("Centennial")

    assert transport.requested_urls == [CENTENNIAL_SEARCH_URL]
    roswell = next(school for school in schools if school.school_id == CENTENNIAL_ROSWELL_ID)
    assert roswell.canonical_url == CENTENNIAL_ROSWELL_URL
    assert roswell.city == "Roswell"
    assert roswell.state == "GA"


async def test_search_schools_saint_edward_retries_with_st(
    client: AsyncMaxPrepsClient,
    transport: AsyncFixtureTransport,
) -> None:
    schools = await client.search_schools("Saint Edward")

    assert transport.requested_urls == [SAINT_EDWARD_SEARCH_URL, ST_EDWARD_SEARCH_URL]
    target = next(school for school in schools if school.school_id == ST_EDWARD_OH_ID)
    assert target.canonical_url == ST_EDWARD_OH_URL
    assert target.name == "St. Edward"
    assert target.city == "Lakewood"
    assert target.state == "OH"


async def test_search_schools_st_edward_single_fetch(
    client: AsyncMaxPrepsClient,
    transport: AsyncFixtureTransport,
) -> None:
    schools = await client.search_schools("St. Edward")

    assert transport.requested_urls == [ST_EDWARD_SEARCH_URL]
    target = next(school for school in schools if school.school_id == ST_EDWARD_OH_ID)
    assert target.canonical_url == ST_EDWARD_OH_URL


@pytest.mark.parametrize(
    ("transport", "expected_error"),
    [
        pytest.param(
            _AsyncSaintSearchOnlyTransport(
                wrap_page_props_in_html({"initialSchoolResults": "not-a-list"})
            ),
            SearchSchemaError,
            id="parser_schema_error",
        ),
        pytest.param(
            _AsyncSaintSearchOnlyTransport("<!DOCTYPE html><html><body></body></html>"),
            NextDataNotFoundError,
            id="parser_next_data_missing",
        ),
        pytest.param(
            _AsyncRaisingSaintSearchTransport(),
            FixtureUrlNotMappedError,
            id="transport_fetch_error",
        ),
    ],
)
async def test_search_schools_saint_errors_do_not_retry(transport, expected_error) -> None:
    client = AsyncMaxPrepsClient(transport)

    with pytest.raises(expected_error):
        await client.search_schools("Saint Edward")

    assert transport.requested_urls == [SAINT_EDWARD_SEARCH_URL]


async def test_centennial_pipeline_teams_and_schedules(
    client: AsyncMaxPrepsClient,
    transport: AsyncFixtureTransport,
) -> None:
    school = _centennial_roswell_school()
    team_seasons = await client.get_school_teams(school)

    assert transport.requested_urls == [CENTENNIAL_ROSWELL_URL]
    football = _find_team(
        team_seasons,
        sport="Football",
        sport_season_id=FOOTBALL_SPORT_SEASON_ID,
    )
    baseball = _find_team(
        team_seasons,
        sport="Baseball",
        sport_season_id=BASEBALL_SPORT_SEASON_ID,
    )
    assert football.canonical_url == CENTENNIAL_FOOTBALL_CANONICAL
    assert baseball.canonical_url == CENTENNIAL_BASEBALL_CANONICAL

    football_schedule = await client.get_schedule(football)
    assert transport.requested_urls == [
        CENTENNIAL_ROSWELL_URL,
        CENTENNIAL_FOOTBALL_SCHEDULE_URL,
    ]

    baseball_schedule = await client.get_schedule(baseball)
    assert transport.requested_urls == [
        CENTENNIAL_ROSWELL_URL,
        CENTENNIAL_FOOTBALL_SCHEDULE_URL,
        CENTENNIAL_BASEBALL_SCHEDULE_URL,
    ]
    assert len(football_schedule.games) == 10
    assert all(game.status is not GameStatus.DELETED for game in football_schedule.games)
    assert RIVERWOOD_CONTEST_ID not in {game.id for game in football_schedule.games}
    assert football_schedule.team_record == "2-0"
    assert len(baseball_schedule.games) == 30
    assert baseball_schedule.team_record is None


async def test_basketball_girls_schedule_url_preserves_gender_segment(
    client: AsyncMaxPrepsClient,
    transport: AsyncFixtureTransport,
) -> None:
    school = _centennial_roswell_school()
    team_seasons = await client.get_school_teams(school)
    girls_basketball_matches = [
        team
        for team in team_seasons
        if team.year == CURRENT_YEAR
        and team.sport == "Basketball"
        and team.gender == "Girls"
        and team.level == "Varsity"
    ]
    assert len(girls_basketball_matches) == 1
    girls_basketball = girls_basketball_matches[0]

    schedule = await client.get_schedule(girls_basketball)

    assert CENTENNIAL_BASKETBALL_GIRLS_SCHEDULE_URL in transport.requested_urls
    assert len(schedule.games) > 0


async def test_tennis_schedule_raises_next_data_not_found(
    client: AsyncMaxPrepsClient,
    transport: AsyncFixtureTransport,
) -> None:
    tennis_team = TeamSeason(
        school_id=CENTENNIAL_ROSWELL_ID,
        sport_season_id="unused-for-fetch",
        canonical_url=CENTENNIAL_TENNIS_CANONICAL,
        sport="Tennis",
        gender="Boys",
        level="Varsity",
        year=CURRENT_YEAR,
        season="Spring",
    )

    with pytest.raises(NextDataNotFoundError) as exc_info:
        await client.get_schedule(tennis_team)

    message = str(exc_info.value).lower()
    assert "aspx" not in message
    assert "legacy" not in message
    assert "tennis" not in message
    assert transport.requested_urls == [CENTENNIAL_TENNIS_SCHEDULE_URL]


async def test_centennial_football_matches_sync_facade() -> None:
    """Async and sync facades produce equivalent models for the same fixtures."""
    sync_transport = FixtureTransport()
    async_transport = AsyncFixtureTransport()
    sync_client = MaxPrepsClient(sync_transport)
    async_client = AsyncMaxPrepsClient(async_transport)

    school = _centennial_roswell_school()

    sync_teams = sync_client.get_school_teams(school)
    async_teams = await async_client.get_school_teams(school)
    sync_football = _find_team(
        sync_teams,
        sport="Football",
        sport_season_id=FOOTBALL_SPORT_SEASON_ID,
    )
    async_football = _find_team(
        async_teams,
        sport="Football",
        sport_season_id=FOOTBALL_SPORT_SEASON_ID,
    )
    assert async_football == sync_football

    sync_schedule = sync_client.get_schedule(sync_football)
    async_schedule = await async_client.get_schedule(async_football)
    assert async_schedule == sync_schedule

    sync_schools = sync_client.search_schools("Centennial")
    async_schools = await async_client.search_schools("Centennial")
    sync_roswell = next(s for s in sync_schools if s.school_id == CENTENNIAL_ROSWELL_ID)
    async_roswell = next(s for s in async_schools if s.school_id == CENTENNIAL_ROSWELL_ID)
    assert async_roswell == sync_roswell
