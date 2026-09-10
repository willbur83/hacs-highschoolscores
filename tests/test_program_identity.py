"""Layer 1 tests for program identity helpers (no Home Assistant import)."""

from __future__ import annotations

from custom_components.high_school_sports_scores.program_identity import (
    ParsedProgramUniqueId,
    parse_program_unique_id,
    program_identity_matches,
)


def test_parse_program_unique_id_round_trip() -> None:
    unique_id = "52dea55b-3988-4979-b5fd-20376058997f:Boys:Varsity:Football"
    parsed = parse_program_unique_id(unique_id)
    assert parsed == ParsedProgramUniqueId(
        school_id="52dea55b-3988-4979-b5fd-20376058997f",
        gender="Boys",
        level="Varsity",
        sport="Football",
    )


def test_parse_program_unique_id_rejects_malformed_values() -> None:
    assert parse_program_unique_id("too:few:parts") is None
    assert parse_program_unique_id("") is None


def test_program_identity_matches_subscription_fields() -> None:
    identity = ParsedProgramUniqueId(
        school_id="school",
        gender="Boys",
        level="Varsity",
        sport="Football",
    )

    class _Program:
        sport = "Football"
        gender = "Boys"
        level = "Varsity"

    assert program_identity_matches(_Program(), identity) is True

    class _OtherProgram:
        sport = "Baseball"
        gender = "Boys"
        level = "Varsity"

    assert program_identity_matches(_OtherProgram(), identity) is False
