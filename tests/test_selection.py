import pytest

from custom_components.maxpreps.exceptions import (
    CurrentCohortAmbiguousError,
    CurrentCohortEmptyError,
)
from custom_components.maxpreps.models import TeamSeason
from custom_components.maxpreps.parsing.sport_seasons import parse_sport_seasons
from custom_components.maxpreps.selection import (
    _school_year_start,
    canonical_url_year_segment,
    canonical_url_year_segments,
    current_cohort_year,
    in_current_cohort,
    is_supported_format,
    selectable_team_seasons,
)
from tests.helpers.fixtures import load_sport_seasons
from tests.helpers.team_season_builders import make_team_season
from tests.test_search import (
    BAINBRIDGE,
    CENTENNIAL,
    PIKE_COUNTY,
    ST_EDWARD,
)

CURRENT_YEAR = "26-27"
EXCLUDED_SPORTS = {
    "Soccer",
    "Lacrosse",
    "Flag Football",
    "Softball",
    "Tennis",
    "Golf",
    "Track",
    "Swimming",
    "Wrestling",
}
ALLOWLISTED_SPORTS = {"Football", "Baseball", "Basketball", "Volleyball"}


def _load_team_seasons(slug: str) -> list[TeamSeason]:
    rows = load_sport_seasons(f"{slug}/sport-seasons-26-27.json")
    return parse_sport_seasons(rows)


def test_empty_input_raises_typed_error():
    with pytest.raises(CurrentCohortEmptyError, match="empty"):
        current_cohort_year([])

    with pytest.raises(CurrentCohortEmptyError):
        in_current_cohort([])

    with pytest.raises(CurrentCohortEmptyError):
        selectable_team_seasons([])


def test_canonical_url_year_segment_matches_path_segment_only():
    assert (
        canonical_url_year_segment(
            "https://www.maxpreps.com/ga/zebulon/pike-county-pirates/soccer/winter/11-12/schedule/"
        )
        == "11-12"
    )
    assert (
        canonical_url_year_segment(
            "https://www.maxpreps.com/ga/zebulon/pike-county-pirates/football/"
        )
        is None
    )
    assert canonical_url_year_segments(
        "https://www.maxpreps.com/ga/football/26-27/region/aaa-region-2/"
    ) == ("26-27",)


def test_is_supported_format_allowlist():
    assert is_supported_format(make_team_season(sport="Football"))
    assert is_supported_format(make_team_season(sport="Baseball"))
    assert is_supported_format(make_team_season(sport="Basketball"))
    assert is_supported_format(make_team_season(sport="Volleyball"))
    assert not is_supported_format(make_team_season(sport="Soccer"))
    assert not is_supported_format(make_team_season(sport="Tennis"))


def test_pike_county_current_cohort_excludes_11_12_leftovers():
    team_seasons = _load_team_seasons(PIKE_COUNTY)

    assert current_cohort_year(team_seasons) == CURRENT_YEAR

    cohort_rows = in_current_cohort(team_seasons)
    assert all(team_season.year == CURRENT_YEAR for team_season in cohort_rows)
    assert len(cohort_rows) == 46
    assert {team_season.year for team_season in team_seasons} == {CURRENT_YEAR, "11-12"}


def test_centennial_football_and_baseball_varsity_are_selectable():
    team_seasons = _load_team_seasons(CENTENNIAL)
    selectable = selectable_team_seasons(team_seasons)

    varsity_football = [
        row
        for row in selectable
        if row.sport == "Football"
        and row.gender == "Boys"
        and row.level == "Varsity"
    ]
    varsity_baseball = [
        row
        for row in selectable
        if row.sport == "Baseball"
        and row.gender == "Boys"
        and row.level == "Varsity"
    ]
    assert len(varsity_football) == 1
    assert len(varsity_baseball) == 1


def test_centennial_selectable_includes_allowlisted_sports_only():
    team_seasons = _load_team_seasons(CENTENNIAL)
    selectable = selectable_team_seasons(team_seasons)

    selectable_sports = {row.sport for row in selectable}
    assert ALLOWLISTED_SPORTS.issubset(selectable_sports)
    assert selectable_sports.isdisjoint(EXCLUDED_SPORTS)


def test_centennial_jv_soccer_stays_in_cohort_but_not_selectable():
    team_seasons = _load_team_seasons(CENTENNIAL)
    cohort_rows = in_current_cohort(team_seasons)
    selectable = selectable_team_seasons(team_seasons)

    jv_soccer_cohort = [
        row for row in cohort_rows if row.sport == "Soccer" and row.level == "JV"
    ]
    assert {(row.gender, row.season) for row in jv_soccer_cohort} == {
        ("Boys", "Spring"),
        ("Girls", "Spring"),
        ("Boys", "Winter"),
    }
    assert not any(row.sport == "Soccer" for row in selectable)


def test_four_school_fixtures_resolve_to_26_27_cohort():
    for slug in (CENTENNIAL, BAINBRIDGE, PIKE_COUNTY, ST_EDWARD):
        team_seasons = _load_team_seasons(slug)
        assert current_cohort_year(team_seasons) == CURRENT_YEAR


def test_pike_unfiltered_parse_still_includes_11_12_rows():
    team_seasons = _load_team_seasons(PIKE_COUNTY)
    legacy_rows = [row for row in team_seasons if row.year == "11-12"]
    assert len(legacy_rows) == 2


def test_preserves_input_order():
    team_seasons = _load_team_seasons(CENTENNIAL)
    selectable = selectable_team_seasons(team_seasons)

    expected = [
        row for row in team_seasons if row.year == CURRENT_YEAR and row.sport in ALLOWLISTED_SPORTS
    ]
    assert selectable == expected


def test_uniform_year_returns_that_cohort():
    rows = [
        make_team_season(sport_season_id="a", sport="Football"),
        make_team_season(sport_season_id="b", sport="Soccer", year="26-27"),
    ]
    assert current_cohort_year(rows) == CURRENT_YEAR
    assert len(in_current_cohort(rows)) == 2


def test_ambiguous_mixed_years_without_clear_majority():
    rows = [
        make_team_season(sport_season_id="a", year="25-26"),
        make_team_season(sport_season_id="b", year="25-26"),
        make_team_season(sport_season_id="c", year="26-27"),
        make_team_season(sport_season_id="d", year="27-28"),
    ]
    with pytest.raises(CurrentCohortAmbiguousError, match="no unambiguous majority"):
        current_cohort_year(rows)


def test_ambiguous_tied_modal_years():
    rows = [
        make_team_season(sport_season_id="a", year="25-26"),
        make_team_season(sport_season_id="b", year="25-26"),
        make_team_season(sport_season_id="c", year="26-27"),
        make_team_season(sport_season_id="d", year="26-27"),
    ]
    with pytest.raises(CurrentCohortAmbiguousError, match="tied modal years"):
        current_cohort_year(rows)


def test_ambiguous_modal_year_disagrees_with_url_year_segment():
    rows = [
        make_team_season(
            sport_season_id=f"row-{index}",
            year="26-27",
        )
        for index in range(5)
    ]
    rows.append(
        make_team_season(
            sport_season_id="leftover",
            year="25-26",
            canonical_url=(
                "https://www.maxpreps.com/ga/roswell/centennial-knights/"
                "football/24-25/schedule/"
            ),
        )
    )
    with pytest.raises(
        CurrentCohortAmbiguousError,
        match="not a clearly identified historical leftover",
    ):
        current_cohort_year(rows)


def test_ambiguous_mid_rollover_adjacent_school_years():
    rows = [
        make_team_season(sport_season_id=f"current-{index}", year="26-27")
        for index in range(6)
    ]
    rows.extend(
        make_team_season(
            sport_season_id=f"next-{index}",
            year="27-28",
            canonical_url=(
                "https://www.maxpreps.com/ga/roswell/centennial-knights/football/"
            ),
        )
        for index in range(2)
    )
    with pytest.raises(
        CurrentCohortAmbiguousError,
        match="adjacent school years",
    ):
        current_cohort_year(rows)


def test_ambiguous_historical_leftover_without_url_year_segment():
    rows = [
        make_team_season(sport_season_id=f"current-{index}", year="26-27")
        for index in range(5)
    ]
    rows.append(
        make_team_season(
            sport_season_id="leftover",
            year="25-26",
            canonical_url=(
                "https://www.maxpreps.com/ga/roswell/centennial-knights/soccer/winter/"
            ),
        )
    )
    with pytest.raises(
        CurrentCohortAmbiguousError,
        match="not a clearly identified historical leftover",
    ):
        current_cohort_year(rows)


def test_ambiguous_current_row_with_contradictory_url_year_segment():
    rows = [
        make_team_season(sport_season_id=f"current-{index}", year="26-27")
        for index in range(5)
    ]
    rows.append(
        make_team_season(
            sport_season_id="contradiction",
            year="26-27",
            canonical_url=(
                "https://www.maxpreps.com/ga/roswell/centennial-knights/"
                "football/25-26/schedule/"
            ),
        )
    )
    with pytest.raises(
        CurrentCohortAmbiguousError,
        match="contradictory canonical_url year-segment",
    ):
        current_cohort_year(rows)


def test_clear_majority_with_identified_historical_leftovers():
    rows = [
        make_team_season(sport_season_id=f"current-{index}", year="26-27")
        for index in range(5)
    ]
    rows.append(
        make_team_season(
            sport_season_id="leftover",
            year="11-12",
            sport="Soccer",
            season="Winter",
            canonical_url=(
                "https://www.maxpreps.com/ga/zebulon/pike-county-pirates/"
                "soccer/winter/11-12/schedule/"
            ),
        )
    )
    assert current_cohort_year(rows) == CURRENT_YEAR
    assert len(in_current_cohort(rows)) == 5


def test_school_year_comparison_is_numeric_not_lexical():
    assert _school_year_start("09-10") < _school_year_start("10-11")
    assert _school_year_start("9-10") < _school_year_start("10-11")


def test_malformed_year_raises_ambiguity_not_value_error():
    rows = [
        make_team_season(sport_season_id="bad", year="not-a-year"),
        *(
            make_team_season(sport_season_id=f"ok-{index}", year="26-27")
            for index in range(5)
        ),
    ]
    with pytest.raises(CurrentCohortAmbiguousError, match="malformed school year"):
        current_cohort_year(rows)


def test_uniform_malformed_year_raises_ambiguity_not_value_error():
    rows = [make_team_season(sport_season_id="only", year="bogus")]
    with pytest.raises(CurrentCohortAmbiguousError, match="malformed school year"):
        current_cohort_year(rows)


def test_ambiguous_url_with_multiple_year_path_segments():
    rows = [
        make_team_season(sport_season_id=f"current-{index}", year="26-27")
        for index in range(5)
    ]
    rows.append(
        make_team_season(
            sport_season_id="multi-segment",
            year="26-27",
            canonical_url="https://www.maxpreps.com/foo/25-26/bar/26-27/schedule/",
        )
    )
    with pytest.raises(
        CurrentCohortAmbiguousError,
        match="contradictory canonical_url year-segment",
    ):
        current_cohort_year(rows)


def test_adjacent_school_years_use_numeric_start_not_lexical_order():
    rows = [
        make_team_season(sport_season_id=f"majority-{index}", year="9-10")
        for index in range(6)
    ]
    rows.extend(
        make_team_season(sport_season_id=f"minority-{index}", year="10-11")
        for index in range(2)
    )
    with pytest.raises(
        CurrentCohortAmbiguousError,
        match="adjacent school years",
    ):
        current_cohort_year(rows)
