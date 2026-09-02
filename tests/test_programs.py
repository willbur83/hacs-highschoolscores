"""Unit tests for school-year program grouping."""

from __future__ import annotations

import pytest

from custom_components.maxpreps.programs import group_school_year_programs
from tests.helpers.team_season_builders import make_team_season


def test_single_term_program_label():
    program = group_school_year_programs(
        [make_team_season(sport="Football", season="Fall")]
    )[0]
    assert program.season_terms == ("Fall",)
    assert program.display_label == "Boys Varsity Football (Fall 26-27)"
    assert len(program.team_seasons) == 1


def test_two_terms_ordered_fall_before_spring():
    programs = group_school_year_programs(
        [
            make_team_season(
                sport="Baseball",
                level="Freshman",
                season="Spring",
                sport_season_id="spring-id",
            ),
            make_team_season(
                sport="Baseball",
                level="Freshman",
                season="Fall",
                sport_season_id="fall-id",
            ),
        ]
    )
    assert len(programs) == 1
    program = programs[0]
    assert program.season_terms == ("Fall", "Spring")
    assert program.display_label == "Boys Freshman Baseball (Fall, Spring 26-27)"
    assert len(program.team_seasons) == 2


def test_unknown_term_after_conventional_names():
    programs = group_school_year_programs(
        [
            make_team_season(season="Fall"),
            make_team_season(season="Autumn", sport_season_id="autumn-id"),
            make_team_season(season="Spring", sport_season_id="spring-id"),
        ]
    )
    assert programs[0].season_terms == ("Fall", "Spring", "Autumn")


def test_duplicate_subscription_key_is_one_group():
    programs = group_school_year_programs(
        [
            make_team_season(
                sport="Baseball",
                level="Freshman",
                season="Spring",
                sport_season_id="spring-id",
            ),
            make_team_season(
                sport="Baseball",
                level="Freshman",
                season="Fall",
                sport_season_id="fall-id",
            ),
        ]
    )
    assert len(programs) == 1
    assert programs[0].sport == "Baseball"
    assert programs[0].gender == "Boys"
    assert programs[0].level == "Freshman"


def test_multiple_years_in_group_raises():
    with pytest.raises(ValueError, match="multiple years"):
        group_school_year_programs(
            [
                make_team_season(year="25-26"),
                make_team_season(year="26-27", sport_season_id="other"),
            ]
        )


def test_deduplicates_identical_term_names():
    program = group_school_year_programs(
        [
            make_team_season(season="Fall"),
            make_team_season(season="Fall", sport_season_id="fall-dup"),
        ]
    )[0]
    assert program.season_terms == ("Fall",)
