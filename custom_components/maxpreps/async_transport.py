"""Production aiohttp transport for MaxPreps page fetches."""

from __future__ import annotations

import asyncio
from typing import Any

from custom_components.maxpreps.const import (
    MAX_RESPONSE_BYTES,
    REQUEST_TIMEOUT_SECONDS,
    USER_AGENT,
)
from custom_components.maxpreps.exceptions import (
    TransportError,
    TransportHttpError,
    TransportInvalidResponseError,
    TransportResponseTooLargeError,
    TransportTimeoutError,
)

_CHUNK_SIZE = 8192


class AiohttpTransport:
    """Fetch MaxPreps HTML through an injectable aiohttp client session."""

    def __init__(self, session: Any) -> None:
        self._session = session

    async def fetch(self, url: str) -> str:
        """Return validated HTML for ``url``."""
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                return await self._fetch_within_timeout(url)
        except TimeoutError as exc:
            raise TransportTimeoutError(
                f"Timed out fetching MaxPreps page: {url}"
            ) from exc

    async def _fetch_within_timeout(self, url: str) -> str:
        try:
            async with self._session.get(
                url,
                headers={"User-Agent": USER_AGENT},
            ) as response:
                return await self._read_response(url, response)
        except TransportError:
            raise
        except Exception as exc:
            raise TransportError(
                f"Network error fetching MaxPreps page: {url}"
            ) from exc

    async def _read_response(self, url: str, response: Any) -> str:
        status = response.status
        if status < 200 or status >= 300:
            raise TransportHttpError(
                f"HTTP {status} fetching MaxPreps page: {url}",
                status_code=status,
            )

        content_length = response.headers.get("Content-Length")
        if content_length is not None:
            try:
                if int(content_length) > MAX_RESPONSE_BYTES:
                    raise TransportResponseTooLargeError(
                        f"Content-Length exceeds {MAX_RESPONSE_BYTES} bytes: {url}"
                    )
            except ValueError:
                pass

        body = await _read_bounded_text(response, MAX_RESPONSE_BYTES)
        content_type = response.headers.get("Content-Type")
        if not _is_valid_html(body, content_type):
            raise TransportInvalidResponseError(
                f"Response is empty or not plausibly HTML: {url}"
            )
        return body


async def _read_bounded_text(response: Any, max_bytes: int) -> str:
    chunks: list[bytes] = []
    total = 0
    async for chunk in response.content.iter_chunked(_CHUNK_SIZE):
        total += len(chunk)
        if total > max_bytes:
            raise TransportResponseTooLargeError(
                f"Response body exceeds {max_bytes} bytes"
            )
        chunks.append(chunk)

    charset = getattr(response, "charset", None) or "utf-8"
    return b"".join(chunks).decode(charset, errors="replace")


def _is_valid_html(body: str, content_type: str | None) -> bool:
    if not body.strip():
        return False
    if content_type and "text/html" in content_type.lower():
        return True
    prefix = body.lstrip()[:500].lower()
    return prefix.startswith("<!doctype html") or prefix.startswith("<html")


__all__ = ["AiohttpTransport"]
