"""MaxPreps client URL construction."""

from __future__ import annotations

import re
from urllib.parse import urlencode, urljoin

_SEARCH_BASE = "https://www.maxpreps.com/search/"
_SAINT_PREFIX = re.compile(r"^Saint\s", re.IGNORECASE)


def build_search_url(query: str) -> str:
    """Build the researched school search URL for ``query``."""
    params = urlencode({"q": query.lower(), "q2": query})
    return f"{_SEARCH_BASE}?{params}"


def is_saint_retry_candidate(query: str) -> bool:
    """Return True when ``query`` begins with standalone ``Saint`` (Slice 16b retry)."""
    return bool(_SAINT_PREFIX.match(query))


def rewrite_saint_query(query: str) -> str:
    """Replace a leading ``Saint`` token with ``St.``; remainder unchanged."""
    return _SAINT_PREFIX.sub("St. ", query, count=1)


def build_schedule_url(team_canonical_url: str) -> str:
    """Safely join ``team_canonical_url`` with the established ``schedule/`` child."""
    base = team_canonical_url if team_canonical_url.endswith("/") else f"{team_canonical_url}/"
    return urljoin(base, "schedule/")
