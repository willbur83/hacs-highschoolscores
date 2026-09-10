"""School logo resolution unit tests (no Home Assistant)."""

from types import SimpleNamespace

from custom_components.high_school_sports_scores.school_logo import (
    automatic_team_logo_from_programs,
    resolve_school_entity_picture,
    validate_school_logo_override,
)
from tests.test_search import CENTENNIAL_ROSWELL_MASCOT_URL


def _term(team_logo: str | None) -> SimpleNamespace:
    schedule = None if team_logo is None else SimpleNamespace(team_logo=team_logo)
    return SimpleNamespace(schedule=schedule)


def _program(*terms: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(terms=terms)


def test_validate_accepts_https_and_local_paths():
    assert (
        validate_school_logo_override("https://example.com/logo.png")
        == "https://example.com/logo.png"
    )
    assert validate_school_logo_override("/local/school.png") == "/local/school.png"
    assert validate_school_logo_override("  ") == ""
    assert validate_school_logo_override("") == ""


def test_validate_rejects_non_https_and_non_local():
    assert validate_school_logo_override("http://example.com/logo.png") is None
    assert validate_school_logo_override("ftp://example.com/logo.png") is None
    assert validate_school_logo_override("school.png") is None


def test_automatic_team_logo_scans_programs_deterministically():
    first_logo = "https://example.com/first.gif"
    second_logo = "https://example.com/second.gif"
    programs = (
        _program(_term(first_logo), _term(second_logo)),
        _program(_term(None)),
    )
    assert automatic_team_logo_from_programs(programs) == first_logo


def test_resolve_prefers_override_then_mascot_then_schedule():
    schedule_logo = "https://example.com/from-schedule.gif"
    programs = (_program(_term(schedule_logo)),)
    override = "https://example.com/override.gif"

    assert (
        resolve_school_entity_picture(
            mascot_url=CENTENNIAL_ROSWELL_MASCOT_URL,
            logo_override=override,
            programs=programs,
        )
        == override
    )
    assert (
        resolve_school_entity_picture(
            mascot_url=CENTENNIAL_ROSWELL_MASCOT_URL,
            logo_override=None,
            programs=programs,
        )
        == CENTENNIAL_ROSWELL_MASCOT_URL
    )
    assert (
        resolve_school_entity_picture(
            mascot_url=None,
            logo_override=None,
            programs=programs,
        )
        == schedule_logo
    )
    assert (
        resolve_school_entity_picture(
            mascot_url=None,
            logo_override=None,
            programs=(),
        )
        is None
    )


def test_cleared_override_restores_automatic_mascot_url():
    assert (
        resolve_school_entity_picture(
            mascot_url=CENTENNIAL_ROSWELL_MASCOT_URL,
            logo_override="",
            programs=(),
        )
        == CENTENNIAL_ROSWELL_MASCOT_URL
    )
