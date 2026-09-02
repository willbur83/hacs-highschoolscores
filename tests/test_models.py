from datetime import datetime

from custom_components.maxpreps.models import (
    Game,
    GameStatus,
    HomeAway,
    Schedule,
    School,
    TeamSeason,
)


def test_school_construction():
    school = School(
        school_id="52dea55b-3988-4979-b5fd-20376058997f",
        canonical_url="https://www.maxpreps.com/ga/roswell/centennial-knights/",
        name="Centennial",
        city="Roswell",
        state="GA",
        zip="30075",
        mascot="Knights",
        mascot_url="https://image.maxpreps.io/school-mascot/example.gif",
    )
    assert school.school_id == "52dea55b-3988-4979-b5fd-20376058997f"
    assert school.name == "Centennial"


def test_team_season_display_label():
    team_season = TeamSeason(
        school_id="52dea55b-3988-4979-b5fd-20376058997f",
        sport_season_id="2286cd80-c46d-4739-8dd1-92a67ca8daa7",
        canonical_url="https://www.maxpreps.com/ga/roswell/centennial-knights/football/schedule/",
        sport="Football",
        gender="Boys",
        level="Varsity",
        year="26-27",
        season="Fall",
        all_season_id="22e2b335-334e-4d4d-9f67-a0f716bb1ccd",
        is_published=True,
    )
    assert team_season.display_label == "Boys Varsity Football"


def test_team_season_identity_requires_school_id():
    shared_sport_season_id = "2286cd80-c46d-4739-8dd1-92a67ca8daa7"
    centennial = TeamSeason(
        school_id="52dea55b-3988-4979-b5fd-20376058997f",
        sport_season_id=shared_sport_season_id,
        canonical_url="https://www.maxpreps.com/ga/roswell/centennial-knights/football/schedule/",
        sport="Football",
        gender="Boys",
        level="Varsity",
        year="26-27",
        season="Fall",
    )
    other_school = TeamSeason(
        school_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        sport_season_id=shared_sport_season_id,
        canonical_url="https://www.maxpreps.com/ga/example/example-eagles/football/schedule/",
        sport="Football",
        gender="Boys",
        level="Varsity",
        year="26-27",
        season="Fall",
    )
    assert centennial != other_school
    assert centennial.identity_key() != other_school.identity_key()
    assert len({centennial, other_school}) == 2


def test_game_date_is_timezone_naive():
    game = Game(
        id="30b79240-4c41-4e25-b850-0052d1221fbd",
        date=datetime(2026, 8, 20, 16, 30, 0),
        status=GameStatus.FINAL,
        team_name="Centennial Knights",
        opponent_name="Dunwoody",
        home_away=HomeAway.NEUTRAL,
        team_score=23,
        opponent_score=21,
        result="W",
        venue="Mercedes-Benz Stadium",
        game_url="https://www.maxpreps.com/game/example",
    )
    assert game.date.tzinfo is None


def test_schedule_construction():
    team_season = TeamSeason(
        school_id="52dea55b-3988-4979-b5fd-20376058997f",
        sport_season_id="2286cd80-c46d-4739-8dd1-92a67ca8daa7",
        canonical_url="https://www.maxpreps.com/ga/roswell/centennial-knights/football/schedule/",
        sport="Football",
        gender="Boys",
        level="Varsity",
        year="26-27",
        season="Fall",
    )
    game = Game(
        id="30b79240-4c41-4e25-b850-0052d1221fbd",
        date=datetime(2026, 9, 4, 19, 30, 0),
        status=GameStatus.SCHEDULED,
        team_name="Centennial Knights",
        opponent_name="Alpharetta",
        home_away=HomeAway.HOME,
    )
    schedule = Schedule(
        team_season=team_season,
        games=[game],
        team_logo="https://image.maxpreps.io/team-logo/example.png",
        team_record="2-0",
    )
    assert schedule.team_season == team_season
    assert len(schedule.games) == 1
    assert schedule.games[0].status == GameStatus.SCHEDULED
