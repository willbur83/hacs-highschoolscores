"""Injectable transport for MaxPreps HTTP fetches."""

from __future__ import annotations

from typing import Protocol


class Transport(Protocol):
    """Fetch MaxPreps HTML by absolute URL."""

    def fetch(self, url: str) -> str:
        """Return the response body for ``url``."""
