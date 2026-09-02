import pytest

from custom_components.maxpreps.exceptions import SportSeasonsSchemaError
from custom_components.maxpreps.models import TeamSeason
from custom_components.maxpreps.parsing.sport_seasons import parse_sport_seasons
from tests.helpers.fixtures import load_sport_seasons
from tests.test_search import (
    BAINBRIDGE,
    BAINBRIDGE_GA_ID,
    CENTENNIAL,
    CENTENNIAL_ROSWELL_ID,
    PIKE_COUNTY,
    PIKE_COUNTY_GA_ID,
    ST_EDWARD,
    ST_EDWARD_OH_ID,
)

FOOTBALL_SPORT_SEASON_ID = "2286cd80-c46d-4739-8dd1-92a67ca8daa7"
FOOTBALL_ALL_SEASON_ID = "22e2b335-334e-4d4d-9f67-a0f716bb1ccd"
CURRENT_YEAR = "26-27"


def _find_football(team_seasons: list[TeamSeason]) -> TeamSeason:
    matches = [
        team_season
        for team_season in team_seasons
        if team_season.sport_season_id == FOOTBALL_SPORT_SEASON_ID
        and team_season.year == CURRENT_YEAR
        and team_season.sport == "Football"
        and team_season.gender == "Boys"
        and team_season.level == "Varsity"
    ]
    assert len(matches) == 1
    return matches[0]


def test_parse_centennial_fixture_all_rows():
    rows = load_sport_seasons(f"{CENTENNIAL}/sport-seasons-26-27.json")
    team_seasons = parse_sport_seasons(rows)

    assert len(team_seasons) == len(rows) == 47
    assert {team_season.school_id for team_season in team_seasons} == {
        CENTENNIAL_ROSWELL_ID
    }


def test_parse_pike_county_fixture_includes_11_12_rows():
    rows = load_sport_seasons(f"{PIKE_COUNTY}/sport-seasons-26-27.json")
    team_seasons = parse_sport_seasons(rows)

    assert len(team_seasons) == len(rows) == 48
    legacy_rows = [team_season for team_season in team_seasons if team_season.year == "11-12"]
    assert len(legacy_rows) == 2
    assert {(row.gender, row.sport, row.season) for row in legacy_rows} == {
        ("Boys", "Soccer", "Winter"),
        ("Girls", "Soccer", "Winter"),
    }


def test_parse_bainbridge_fixture():
    rows = load_sport_seasons(f"{BAINBRIDGE}/sport-seasons-26-27.json")
    team_seasons = parse_sport_seasons(rows)

    assert len(team_seasons) == len(rows) == 39
    assert {team_season.school_id for team_season in team_seasons} == {BAINBRIDGE_GA_ID}


def test_parse_st_edward_fixture():
    rows = load_sport_seasons(f"{ST_EDWARD}/sport-seasons-26-27.json")
    team_seasons = parse_sport_seasons(rows)

    assert len(team_seasons) == len(rows) == 32
    assert {team_season.school_id for team_season in team_seasons} == {ST_EDWARD_OH_ID}


def test_football_sport_season_id_shared_across_schools():
    school_ids = {
        CENTENNIAL: CENTENNIAL_ROSWELL_ID,
        BAINBRIDGE: BAINBRIDGE_GA_ID,
        PIKE_COUNTY: PIKE_COUNTY_GA_ID,
        ST_EDWARD: ST_EDWARD_OH_ID,
    }
    football_by_school: dict[str, TeamSeason] = {}
    for slug, school_id in school_ids.items():
        rows = load_sport_seasons(f"{slug}/sport-seasons-26-27.json")
        football = _find_football(parse_sport_seasons(rows))
        assert football.school_id == school_id
        assert football.sport_season_id == FOOTBALL_SPORT_SEASON_ID
        assert football.all_season_id == FOOTBALL_ALL_SEASON_ID
        football_by_school[school_id] = football

    centennial = football_by_school[CENTENNIAL_ROSWELL_ID]
    pike_county = football_by_school[PIKE_COUNTY_GA_ID]
    assert centennial.sport_season_id == pike_county.sport_season_id
    assert centennial.all_season_id == pike_county.all_season_id
    assert centennial.school_id != pike_county.school_id
    assert centennial != pike_county
    assert centennial.identity_key() != pike_county.identity_key()
    assert len({centennial, pike_county}) == 2


def test_centennial_keeps_multi_term_jv_soccer_duplicates():
    rows = load_sport_seasons(f"{CENTENNIAL}/sport-seasons-26-27.json")
    team_seasons = parse_sport_seasons(rows)

    jv_soccer = [
        team_season
        for team_season in team_seasons
        if team_season.sport == "Soccer" and team_season.level == "JV"
    ]
    assert {(row.gender, row.season) for row in jv_soccer} == {
        ("Boys", "Spring"),
        ("Girls", "Spring"),
        ("Boys", "Winter"),
    }
    assert len(jv_soccer) == 3


def test_enumeration_includes_tennis_and_golf_rows():
    rows = load_sport_seasons(f"{CENTENNIAL}/sport-seasons-26-27.json")
    team_seasons = parse_sport_seasons(rows)

    sports = {team_season.sport for team_season in team_seasons}
    assert "Tennis" in sports
    assert "Golf" in sports
    assert len([team_season for team_season in team_seasons if team_season.sport == "Tennis"]) == 4
    assert len([team_season for team_season in team_seasons if team_season.sport == "Golf"]) == 2


def test_display_label_is_derived_not_stored():
    rows = load_sport_seasons(f"{CENTENNIAL}/sport-seasons-26-27.json")
    football = _find_football(parse_sport_seasons(rows))

    assert football.display_label == "Boys Varsity Football"


def test_malformed_row_missing_required_field_raises():
    rows = load_sport_seasons(f"{CENTENNIAL}/sport-seasons-26-27.json")
    bad_row = dict(rows[0])
    del bad_row["season"]
    with pytest.raises(
        SportSeasonsSchemaError,
        match=r"sportSeasons\[0\] missing required field 'season'",
    ):
        parse_sport_seasons([bad_row])


def test_malformed_row_type_raises():
    with pytest.raises(SportSeasonsSchemaError, match=r"sportSeasons\[0\] must be an object"):
        parse_sport_seasons(["not-a-dict"])
