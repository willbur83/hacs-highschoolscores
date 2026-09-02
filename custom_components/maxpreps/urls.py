"""MaxPreps client URL construction."""

from __future__ import annotations

from urllib.parse import urlencode, urljoin

_SEARCH_BASE = "https://www.maxpreps.com/search/"


def build_search_url(query: str) -> str:
    """Build the researched school search URL for ``query``."""
    params = urlencode({"q": query.lower(), "q2": query})
    return f"{_SEARCH_BASE}?{params}"


def build_schedule_url(team_canonical_url: str) -> str:
    """Safely join ``team_canonical_url`` with the established ``schedule/`` child."""
    base = team_canonical_url if team_canonical_url.endswith("/") else f"{team_canonical_url}/"
    return urljoin(base, "schedule/")
