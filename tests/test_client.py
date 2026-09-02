import pytest

from custom_components.maxpreps.client import MaxPrepsClient
from custom_components.maxpreps.exceptions import NextDataNotFoundError
from custom_components.maxpreps.models import GameStatus, School, TeamSeason
from custom_components.maxpreps.urls import build_schedule_url, build_search_url
from tests.helpers.fixture_transport import FixtureTransport
from tests.test_schedule import (
    BASEBALL_SPORT_SEASON_ID,
    FOOTBALL_SPORT_SEASON_ID,
    RIVERWOOD_CONTEST_ID,
)
from tests.test_search import (
    BAINBRIDGE,
    BAINBRIDGE_GA_ID,
    BAINBRIDGE_GA_URL,
    CENTENNIAL,
    CENTENNIAL_ROSWELL_ID,
    CENTENNIAL_ROSWELL_URL,
)

CURRENT_YEAR = "26-27"
CENTENNIAL_SEARCH_URL = build_search_url("Centennial")
CENTENNIAL_FOOTBALL_CANONICAL = (
    "https://www.maxpreps.com/ga/roswell/centennial-knights/football/"
)
CENTENNIAL_BASEBALL_CANONICAL = (
    "https://www.maxpreps.com/ga/roswell/centennial-knights/baseball/"
)
CENTENNIAL_FOOTBALL_SCHEDULE_URL = build_schedule_url(CENTENNIAL_FOOTBALL_CANONICAL)
CENTENNIAL_BASEBALL_SCHEDULE_URL = build_schedule_url(CENTENNIAL_BASEBALL_CANONICAL)
CENTENNIAL_BASKETBALL_GIRLS_CANONICAL = (
    "https://www.maxpreps.com/ga/roswell/centennial-knights/basketball/girls/"
)
CENTENNIAL_BASKETBALL_GIRLS_SCHEDULE_URL = build_schedule_url(
    CENTENNIAL_BASKETBALL_GIRLS_CANONICAL
)
CENTENNIAL_TENNIS_CANONICAL = "https://www.maxpreps.com/ga/roswell/centennial-knights/tennis/"
CENTENNIAL_TENNIS_SCHEDULE_URL = build_schedule_url(CENTENNIAL_TENNIS_CANONICAL)


def _centennial_roswell_school() -> School:
    return School(
        school_id=CENTENNIAL_ROSWELL_ID,
        canonical_url=CENTENNIAL_ROSWELL_URL,
        name="Centennial",
        city="Roswell",
        state="GA",
    )


def _find_team(
    team_seasons: list[TeamSeason],
    *,
    sport: str,
    sport_season_id: str,
) -> TeamSeason:
    matches = [
        team
        for team in team_seasons
        if team.year == CURRENT_YEAR
        and team.sport == sport
        and team.sport_season_id == sport_season_id
        and team.gender == "Boys"
        and team.level == "Varsity"
    ]
    assert len(matches) == 1
    return matches[0]


@pytest.fixture
def transport() -> FixtureTransport:
    return FixtureTransport()


@pytest.fixture
def client(transport: FixtureTransport) -> MaxPrepsClient:
    return MaxPrepsClient(transport)


def test_build_search_url_centennial():
    assert (
        build_search_url("Centennial")
        == "https://www.maxpreps.com/search/?q=centennial&q2=Centennial"
    )


def test_build_schedule_url_preserves_path_segments():
    assert (
        build_schedule_url("https://www.maxpreps.com/ga/roswell/centennial-knights/football")
        == CENTENNIAL_FOOTBALL_SCHEDULE_URL
    )
    assert (
        build_schedule_url(CENTENNIAL_BASKETBALL_GIRLS_CANONICAL)
        == CENTENNIAL_BASKETBALL_GIRLS_SCHEDULE_URL
    )


def test_search_schools_bainbridge(client: MaxPrepsClient, transport: FixtureTransport):
    schools = client.search_schools("Bainbridge")

    assert CENTENNIAL_SEARCH_URL not in transport.requested_urls
    assert build_search_url("Bainbridge") in transport.requested_urls
    target = next(school for school in schools if school.school_id == BAINBRIDGE_GA_ID)
    assert target.canonical_url == BAINBRIDGE_GA_URL


def test_search_schools_centennial(
    client: MaxPrepsClient,
    transport: FixtureTransport,
):
    schools = client.search_schools("Centennial")

    assert CENTENNIAL_SEARCH_URL in transport.requested_urls
    roswell = next(school for school in schools if school.school_id == CENTENNIAL_ROSWELL_ID)
    assert roswell.canonical_url == CENTENNIAL_ROSWELL_URL
    assert roswell.city == "Roswell"
    assert roswell.state == "GA"


def test_centennial_pipeline_teams_and_schedules(
    client: MaxPrepsClient,
    transport: FixtureTransport,
):
    school = _centennial_roswell_school()
    team_seasons = client.get_school_teams(school)

    assert CENTENNIAL_ROSWELL_URL in transport.requested_urls
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

    football_schedule = client.get_schedule(football)
    baseball_schedule = client.get_schedule(baseball)

    assert CENTENNIAL_FOOTBALL_SCHEDULE_URL in transport.requested_urls
    assert CENTENNIAL_BASEBALL_SCHEDULE_URL in transport.requested_urls
    assert len(football_schedule.games) == 10
    assert all(game.status is not GameStatus.DELETED for game in football_schedule.games)
    assert RIVERWOOD_CONTEST_ID not in {game.id for game in football_schedule.games}
    assert football_schedule.team_record == "2-0"
    assert len(baseball_schedule.games) == 30
    assert baseball_schedule.team_record is None


def test_basketball_girls_schedule_url_preserves_gender_segment(
    client: MaxPrepsClient,
    transport: FixtureTransport,
):
    school = _centennial_roswell_school()
    team_seasons = client.get_school_teams(school)
    girls_basketball = next(
        team
        for team in team_seasons
        if team.year == CURRENT_YEAR
        and team.sport == "Basketball"
        and team.gender == "Girls"
        and team.level == "Varsity"
    )

    schedule = client.get_schedule(girls_basketball)

    assert CENTENNIAL_BASKETBALL_GIRLS_SCHEDULE_URL in transport.requested_urls
    assert len(schedule.games) > 0


def test_tennis_schedule_raises_next_data_not_found(
    client: MaxPrepsClient,
    transport: FixtureTransport,
):
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
        client.get_schedule(tennis_team)

    message = str(exc_info.value).lower()
    assert "aspx" not in message
    assert "legacy" not in message
    assert "tennis" not in message
    assert CENTENNIAL_TENNIS_SCHEDULE_URL in transport.requested_urls
