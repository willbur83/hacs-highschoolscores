"""Shared helpers for school-home pageProps used by sync and async clients."""

from __future__ import annotations

from typing import Any

from custom_components.maxpreps.exceptions import SportSeasonsSchemaError


def extract_sport_seasons(page_props: dict[str, Any]) -> list[dict[str, Any]]:
    """Return raw ``sportSeasons`` rows from school-home ``pageProps``."""
    school_context = page_props.get("schoolContext")
    if not isinstance(school_context, dict):
        raise SportSeasonsSchemaError("pageProps.schoolContext must be an object")

    sport_seasons = school_context.get("sportSeasons")
    if sport_seasons is None:
        raise SportSeasonsSchemaError("pageProps.schoolContext.sportSeasons is required")
    if not isinstance(sport_seasons, list):
        raise SportSeasonsSchemaError("pageProps.schoolContext.sportSeasons must be a list")

    return sport_seasons
