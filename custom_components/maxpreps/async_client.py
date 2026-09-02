"""Async MaxPreps client facade over an injectable async transport."""

from __future__ import annotations

from custom_components.maxpreps.models import Schedule, School, TeamSeason
from custom_components.maxpreps.parsing.next_data import extract_page_props
from custom_components.maxpreps.parsing.schedule import parse_schedule_page_props
from custom_components.maxpreps.parsing.search import parse_search_page_props
from custom_components.maxpreps.parsing.sport_seasons import parse_sport_seasons
from custom_components.maxpreps.school_home import extract_sport_seasons
from custom_components.maxpreps.transport import AsyncTransport
from custom_components.maxpreps.urls import (
    build_schedule_url,
    build_search_url,
    is_saint_retry_candidate,
    rewrite_saint_query,
)


class AsyncMaxPrepsClient:
    """Async MaxPreps client that awaits transport fetch then existing parsers."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def search_schools(self, query: str) -> list[School]:
        """Search schools by short name."""
        schools = await self._fetch_search_results(query)
        if schools:
            return schools

        if is_saint_retry_candidate(query):
            return await self._fetch_search_results(rewrite_saint_query(query))

        return schools

    async def _fetch_search_results(self, query: str) -> list[School]:
        html = await self._transport.fetch(build_search_url(query))
        page_props = extract_page_props(html)
        return parse_search_page_props(page_props)

    async def get_school_teams(self, school: School) -> list[TeamSeason]:
        """Return every team season row from the school home page."""
        html = await self._transport.fetch(school.canonical_url)
        page_props = extract_page_props(html)
        rows = extract_sport_seasons(page_props)
        return parse_sport_seasons(rows)

    async def get_schedule(self, team: TeamSeason) -> Schedule:
        """Fetch and decode the head-to-head schedule for ``team``."""
        html = await self._transport.fetch(build_schedule_url(team.canonical_url))
        page_props = extract_page_props(html)
        return parse_schedule_page_props(page_props)
