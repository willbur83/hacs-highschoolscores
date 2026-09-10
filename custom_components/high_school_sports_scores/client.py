"""MaxPreps client facade over an injectable transport."""

from __future__ import annotations

from custom_components.high_school_sports_scores.models import Schedule, School, TeamSeason
from custom_components.high_school_sports_scores.parsing.next_data import extract_page_props
from custom_components.high_school_sports_scores.parsing.schedule import parse_schedule_page_props
from custom_components.high_school_sports_scores.parsing.search import parse_search_page_props
from custom_components.high_school_sports_scores.parsing.sport_seasons import parse_sport_seasons
from custom_components.high_school_sports_scores.school_home import extract_sport_seasons
from custom_components.high_school_sports_scores.transport import Transport
from custom_components.high_school_sports_scores.urls import (
    build_schedule_url,
    build_search_url,
    is_saint_retry_candidate,
    rewrite_saint_query,
)


class MaxPrepsClient:
    """Fixture-driven MaxPreps client (Slice 9)."""

    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def search_schools(self, query: str) -> list[School]:
        """Search schools by short name."""
        schools = self._fetch_search_results(query)
        if schools:
            return schools

        if is_saint_retry_candidate(query):
            return self._fetch_search_results(rewrite_saint_query(query))

        return schools

    def _fetch_search_results(self, query: str) -> list[School]:
        html = self._transport.fetch(build_search_url(query))
        page_props = extract_page_props(html)
        return parse_search_page_props(page_props)

    def get_school_teams(self, school: School) -> list[TeamSeason]:
        """Return every team season row from the school home page."""
        html = self._transport.fetch(school.canonical_url)
        page_props = extract_page_props(html)
        rows = extract_sport_seasons(page_props)
        return parse_sport_seasons(rows)

    def get_schedule(self, team: TeamSeason) -> Schedule:
        """Fetch and decode the head-to-head schedule for ``team``."""
        html = self._transport.fetch(build_schedule_url(team.canonical_url))
        page_props = extract_page_props(html)
        return parse_schedule_page_props(page_props)
