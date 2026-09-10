"""Configured-school logo resolution (no Home Assistant imports)."""

from __future__ import annotations

from typing import Any


def automatic_team_logo_from_programs(
    programs: tuple[Any, ...],
) -> str | None:
    """First non-blank ``Schedule.team_logo`` across coordinator programs, deterministically."""
    for program in programs:
        for term in program.terms:
            schedule = term.schedule
            if schedule is None:
                continue
            team_logo = schedule.team_logo
            if team_logo and team_logo.strip():
                return team_logo.strip()
    return None


def resolve_school_entity_picture(
    *,
    mascot_url: str | None,
    logo_override: str | None,
    programs: tuple[Any, ...],
) -> str | None:
    """School-level ``entity_picture`` URL for all program sensors on one config entry."""
    if logo_override is not None:
        override = logo_override.strip()
        if override:
            return override

    if mascot_url is not None:
        automatic = mascot_url.strip()
        if automatic:
            return automatic

    return automatic_team_logo_from_programs(programs)


def validate_school_logo_override(value: str) -> str | None:
    """Validate user-supplied logo override; empty clears; ``None`` means invalid."""
    stripped = value.strip()
    if not stripped:
        return ""
    if stripped.startswith("https://"):
        return stripped
    if stripped.startswith("/local/"):
        return stripped
    return None
