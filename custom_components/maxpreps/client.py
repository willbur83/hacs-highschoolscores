"""MaxPreps client facade over an injectable transport."""

from __future__ import annotations

from typing import Any

from custom_components.maxpreps.exceptions import SportSeasonsSchemaError
from custom_components.maxpreps.models import Schedule, School, TeamSeason
from custom_components.maxpreps.parsing.next_data import extract_page_props
from custom_components.maxpreps.parsing.schedule import parse_schedule_page_props
from custom_components.maxpreps.parsing.search import parse_search_page_props
from custom_components.maxpreps.parsing.sport_seasons import parse_sport_seasons
from custom_components.maxpreps.transport import Transport
from custom_components.maxpreps.urls import build_schedule_url, build_search_url


class MaxPrepsClient:
    """Fixture-driven MaxPreps client (Slice 9)."""

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def search_schools(self, query: str) -> list[School]:
        """Search schools by short name."""
        html = self._transport.fetch(build_search_url(query))
        page_props = extract_page_props(html)
        return parse_search_page_props(page_props)

    def get_school_teams(self, school: School) -> list[TeamSeason]:
        """Return every team season row from the school home page."""
        html = self._transport.fetch(school.canonical_url)
        page_props = extract_page_props(html)
        rows = _extract_sport_seasons(page_props)
        return parse_sport_seasons(rows)

    def get_schedule(self, team: TeamSeason) -> Schedule:
        """Fetch and decode the head-to-head schedule for ``team``."""
        html = self._transport.fetch(build_schedule_url(team.canonical_url))
        page_props = extract_page_props(html)
        return parse_schedule_page_props(page_props)


def _extract_sport_seasons(page_props: dict[str, Any]) -> list[dict[str, Any]]:
    school_context = page_props.get("schoolContext")
    if not isinstance(school_context, dict):
        raise SportSeasonsSchemaError("pageProps.schoolContext must be an object")

    sport_seasons = school_context.get("sportSeasons")
    if sport_seasons is None:
        raise SportSeasonsSchemaError("pageProps.schoolContext.sportSeasons is required")
    if not isinstance(sport_seasons, list):
        raise SportSeasonsSchemaError("pageProps.schoolContext.sportSeasons must be a list")

    return sport_seasons
