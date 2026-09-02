"""Tests for the production async transport (Slice 2)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest

from custom_components.maxpreps.async_transport import AiohttpTransport
from custom_components.maxpreps.const import (
    MAX_RESPONSE_BYTES,
    USER_AGENT,
    VERSION,
)
from custom_components.maxpreps.exceptions import (
    TransportError,
    TransportHttpError,
    TransportInvalidResponseError,
    TransportResponseTooLargeError,
    TransportTimeoutError,
)
from custom_components.maxpreps.urls import build_search_url
from tests.helpers.async_fixture_transport import (
    AsyncFixtureTransport,
    FixtureUrlNotMappedError,
)
from tests.helpers.fixture_transport import FixtureTransport


class _FakeContent:
    def __init__(self, body: bytes) -> None:
        self._body = body

    async def iter_chunked(self, chunk_size: int) -> AsyncIterator[bytes]:
        for offset in range(0, len(self._body), chunk_size):
            yield self._body[offset : offset + chunk_size]


class _FakeResponse:
    def __init__(
        self,
        *,
        status: int = 200,
        body: bytes = b"",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self.headers = headers or {}
        self._body = body
        self.content = _FakeContent(body)
        self.charset = "utf-8"

    async def __aenter__(self) -> _FakeResponse:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class _FakeSession:
    def __init__(self, response: _FakeResponse | Exception) -> None:
        self._response = response
        self.call_count = 0
        self.requested_urls: list[str] = []
        self.requested_headers: list[dict[str, str] | None] = []
        self.headers: dict[str, str] = {"User-Agent": "Home Assistant/2026.9.0"}

    def get(self, url: str, headers: dict[str, str] | None = None) -> _FakeResponse:
        self.call_count += 1
        self.requested_urls.append(url)
        self.requested_headers.append(headers)
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


class _TimeoutSession:
    def __init__(self) -> None:
        self.call_count = 0
        self.headers: dict[str, str] = {"User-Agent": "Home Assistant/2026.9.0"}

    def get(self, url: str, headers: dict[str, str] | None = None) -> Any:
        self.call_count += 1

        class _SlowContext:
            async def __aenter__(self) -> None:
                await asyncio.sleep(3600)

            async def __aexit__(self, *args: object) -> None:
                return None

        return _SlowContext()


class _AiohttpClientError(Exception):
    """Stand-in for aiohttp.ClientError when aiohttp is not installed in [dev]."""


@pytest.mark.asyncio
async def test_async_fixture_transport_returns_mapped_html() -> None:
    sync = FixtureTransport()
    async_transport = AsyncFixtureTransport()
    url = build_search_url("Centennial")

    sync_html = sync.fetch(url)
    async_html = await async_transport.fetch(url)

    assert async_html == sync_html
    assert async_transport.requested_urls == [url]
    assert "<html" in async_html.lower()


@pytest.mark.asyncio
async def test_async_fixture_transport_raises_for_unknown_url() -> None:
    transport = AsyncFixtureTransport()
    with pytest.raises(FixtureUrlNotMappedError):
        await transport.fetch("https://www.maxpreps.com/unknown/")


@pytest.mark.asyncio
async def test_successful_fetch_returns_body_and_user_agent() -> None:
    body = b"<!DOCTYPE html><html><body>ok</body></html>"
    session = _FakeSession(
        _FakeResponse(
            body=body,
            headers={"Content-Type": "text/html; charset=utf-8"},
        )
    )
    original_headers = dict(session.headers)
    transport = AiohttpTransport(session)

    result = await transport.fetch("https://www.maxpreps.com/search/?q=test")

    assert result == body.decode("utf-8")
    assert session.call_count == 1
    assert session.requested_headers == [{"User-Agent": USER_AGENT}]
    assert session.headers == original_headers


@pytest.mark.asyncio
async def test_http_403_raises_without_retry() -> None:
    session = _FakeSession(_FakeResponse(status=403))
    transport = AiohttpTransport(session)

    with pytest.raises(TransportHttpError) as exc_info:
        await transport.fetch("https://www.maxpreps.com/forbidden/")

    assert exc_info.value.status_code == 403
    assert session.call_count == 1


@pytest.mark.asyncio
async def test_http_429_raises_without_retry() -> None:
    session = _FakeSession(_FakeResponse(status=429))
    transport = AiohttpTransport(session)

    with pytest.raises(TransportHttpError) as exc_info:
        await transport.fetch("https://www.maxpreps.com/rate-limited/")

    assert exc_info.value.status_code == 429
    assert session.call_count == 1


@pytest.mark.asyncio
async def test_http_500_raises_transport_http_error() -> None:
    session = _FakeSession(_FakeResponse(status=500))
    transport = AiohttpTransport(session)

    with pytest.raises(TransportHttpError) as exc_info:
        await transport.fetch("https://www.maxpreps.com/error/")

    assert exc_info.value.status_code == 500
    assert session.call_count == 1


@pytest.mark.asyncio
async def test_network_client_error_maps_to_transport_error_without_retry() -> None:
    network_error = _AiohttpClientError("connection refused")
    session = _FakeSession(network_error)
    transport = AiohttpTransport(session)

    with pytest.raises(TransportError) as exc_info:
        await transport.fetch("https://www.maxpreps.com/down/")

    assert not isinstance(exc_info.value, TransportHttpError)
    assert exc_info.value.__cause__ is network_error
    assert session.call_count == 1


@pytest.mark.asyncio
async def test_timeout_raises_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "custom_components.maxpreps.async_transport.REQUEST_TIMEOUT_SECONDS",
        0.01,
    )
    session = _TimeoutSession()
    transport = AiohttpTransport(session)

    with pytest.raises(TransportTimeoutError):
        await transport.fetch("https://www.maxpreps.com/slow/")

    assert session.call_count == 1


@pytest.mark.asyncio
async def test_oversized_content_length_rejects_before_body_read() -> None:
    session = _FakeSession(
        _FakeResponse(
            body=b"<!DOCTYPE html><html></html>",
            headers={
                "Content-Type": "text/html",
                "Content-Length": str(MAX_RESPONSE_BYTES + 1),
            },
        )
    )
    transport = AiohttpTransport(session)

    with pytest.raises(TransportResponseTooLargeError):
        await transport.fetch("https://www.maxpreps.com/huge/")

    assert session.call_count == 1


@pytest.mark.asyncio
async def test_oversized_streaming_body_rejects_without_returning_body() -> None:
    oversized = b"x" * (MAX_RESPONSE_BYTES + 1)
    session = _FakeSession(
        _FakeResponse(
            body=oversized,
            headers={"Content-Type": "text/html"},
        )
    )
    transport = AiohttpTransport(session)

    with pytest.raises(TransportResponseTooLargeError):
        await transport.fetch("https://www.maxpreps.com/huge-stream/")

    assert session.call_count == 1


@pytest.mark.asyncio
async def test_empty_body_raises_invalid_response() -> None:
    session = _FakeSession(
        _FakeResponse(
            body=b"",
            headers={"Content-Type": "text/html"},
        )
    )
    transport = AiohttpTransport(session)

    with pytest.raises(TransportInvalidResponseError):
        await transport.fetch("https://www.maxpreps.com/empty/")


@pytest.mark.asyncio
async def test_non_html_body_raises_invalid_response() -> None:
    session = _FakeSession(
        _FakeResponse(
            body=b'{"not": "html"}',
            headers={"Content-Type": "application/json"},
        )
    )
    transport = AiohttpTransport(session)

    with pytest.raises(TransportInvalidResponseError):
        await transport.fetch("https://www.maxpreps.com/json/")


@pytest.mark.asyncio
async def test_html_without_content_type_accepted_when_plausible() -> None:
    body = b"<!DOCTYPE html><html><body>ok</body></html>"
    session = _FakeSession(_FakeResponse(body=body, headers={}))
    transport = AiohttpTransport(session)

    result = await transport.fetch("https://www.maxpreps.com/no-content-type/")

    assert result == body.decode("utf-8")


def test_user_agent_version_matches_manifest() -> None:
    assert VERSION == "0.0.0"
    assert USER_AGENT == (
        "HomeAssistant-MaxPreps/0.0.0 "
        "(+https://github.com/willbur83/hacs-highschoolscores)"
    )
