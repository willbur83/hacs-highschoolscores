"""Pure helpers for school-year program grouping and config-flow labels."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from custom_components.maxpreps.models import TeamSeason

_CONVENTIONAL_TERM_ORDER: Final = {
    "Fall": 0,
    "Winter": 1,
    "Spring": 2,
    "Summer": 3,
}


@dataclass(frozen=True, slots=True)
class SchoolYearProgram:
    """One user subscription: sport + gender + level within a single school year."""

    sport: str
    gender: str
    level: str
    year: str
    season_terms: tuple[str, ...]
    team_seasons: tuple[TeamSeason, ...]

    @property
    def display_label(self) -> str:
        """Picker label with informational term(s) and school year."""
        base = f"{self.gender} {self.level} {self.sport}"
        terms = ", ".join(self.season_terms)
        return f"{base} ({terms} {self.year})"


def group_school_year_programs(team_seasons: list[TeamSeason]) -> list[SchoolYearProgram]:
    """Group allowlisted cohort rows into one program per (sport, gender, level).

    Preserves school-home order within each group. Caller should pass rows already
    restricted to one applicable school year (e.g. ``selectable_team_seasons`` output).
    """
    groups: dict[tuple[str, str, str], list[TeamSeason]] = {}
    group_order: list[tuple[str, str, str]] = []

    for team_season in team_seasons:
        key = (team_season.sport, team_season.gender, team_season.level)
        if key not in groups:
            groups[key] = []
            group_order.append(key)
        groups[key].append(team_season)

    programs: list[SchoolYearProgram] = []
    for key in group_order:
        rows = groups[key]
        sport, gender, level = key
        years = {row.year for row in rows}
        if len(years) != 1:
            raise ValueError(
                f"program {gender} {level} {sport} has multiple years: {sorted(years)}"
            )
        year = next(iter(years))
        season_terms = _ordered_deduplicated_season_terms([row.season for row in rows])
        programs.append(
            SchoolYearProgram(
                sport=sport,
                gender=gender,
                level=level,
                year=year,
                season_terms=season_terms,
                team_seasons=tuple(rows),
            )
        )

    return programs


def _ordered_deduplicated_season_terms(seasons: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    unique: list[str] = []
    for season in seasons:
        if season in seen:
            continue
        seen.add(season)
        unique.append(season)

    def sort_key(term: str) -> tuple[int, str]:
        conventional_rank = _CONVENTIONAL_TERM_ORDER.get(term)
        if conventional_rank is not None:
            return (conventional_rank, "")
        return (len(_CONVENTIONAL_TERM_ORDER), term.casefold())

    return tuple(sorted(unique, key=sort_key))
