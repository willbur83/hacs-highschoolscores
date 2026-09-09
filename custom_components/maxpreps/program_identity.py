"""Pure helpers for MaxPreps program entity identity (no Home Assistant imports)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedProgramUniqueId:
    """Components of a program sensor ``unique_id``."""

    school_id: str
    gender: str
    level: str
    sport: str


def parse_program_unique_id(unique_id: str) -> ParsedProgramUniqueId | None:
    """Parse ``{school_id}:{gender}:{level}:{sport}``."""
    parts = unique_id.split(":")
    if len(parts) != 4:
        return None
    school_id, gender, level, sport = parts
    if not all((school_id, gender, level, sport)):
        return None
    return ParsedProgramUniqueId(
        school_id=school_id,
        gender=gender,
        level=level,
        sport=sport,
    )


def program_identity_matches(
    program: object,
    identity: ParsedProgramUniqueId,
) -> bool:
    """Return whether a coordinator program snapshot matches parsed identity."""
    return (
        getattr(program, "sport", None) == identity.sport
        and getattr(program, "gender", None) == identity.gender
        and getattr(program, "level", None) == identity.level
    )


__all__ = [
    "ParsedProgramUniqueId",
    "parse_program_unique_id",
    "program_identity_matches",
]
