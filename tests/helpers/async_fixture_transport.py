"""Async fixture-backed transport for MaxPreps client tests."""

from __future__ import annotations

from tests.helpers.fixture_transport import FixtureTransport, FixtureUrlNotMappedError

__all__ = ["AsyncFixtureTransport", "FixtureUrlNotMappedError"]


class AsyncFixtureTransport:
    """Async wrapper around :class:`FixtureTransport` for Slice 2+ tests."""

    def __init__(self) -> None:
        self._sync = FixtureTransport()

    @property
    def requested_urls(self) -> list[str]:
        return self._sync.requested_urls

    async def fetch(self, url: str) -> str:
        return self._sync.fetch(url)
