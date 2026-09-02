#!/usr/bin/env python3
"""Generic HTTP capture helper for MaxPreps feasibility exploration (Slice 00+).

Usage:
    python scripts/explore/capture.py <url> [--slice SLICE] [--notes NOTES]

Fetches a single URL with conservative rate limiting, caches the raw response
under captures/private/, and writes a sanitized JSON sidecar suitable for
inspection or later promotion to tests/fixtures/maxpreps/.

This module is intentionally generic — no MaxPreps-specific parsing or client.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

try:
    import httpx
except ImportError:  # pragma: no cover - exploration environments without pip/venv
    httpx = None  # type: ignore[assignment,misc]

REPO_ROOT = Path(__file__).resolve().parents[2]
PRIVATE_CACHE_DIR = REPO_ROOT / "captures" / "private"
MIN_REQUEST_INTERVAL_S = 2.0

_SENSITIVE_REQUEST_HEADERS = frozenset(
    h.lower()
    for h in (
        "authorization",
        "cookie",
        "x-api-key",
        "x-auth-token",
        "proxy-authorization",
    )
)
_SENSITIVE_RESPONSE_HEADERS = frozenset(
    h.lower()
    for h in (
        "set-cookie",
        "set-cookie2",
    )
)
_REDACT_PATTERNS = (
  (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[IP_REDACTED]"),
  (re.compile(r"/(?:home|Users)/[^\s\"'<>]+"), "[PATH_REDACTED]"),
  (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[EMAIL_REDACTED]"),
)


def _cache_key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def _cache_paths(url: str) -> tuple[Path, Path]:
    parsed = urlparse(url)
    host = parsed.netloc.replace(":", "_") or "unknown-host"
    key = _cache_key(url)
    base = PRIVATE_CACHE_DIR / host / key
    return base.with_suffix(".raw"), base.with_suffix(".json")


def _redact_text(text: str) -> str:
    for pattern, replacement in _REDACT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _sanitize_body(body: bytes, content_type: str | None) -> str:
    charset = "utf-8"
    if content_type:
        match = re.search(r"charset=([^\s;]+)", content_type, re.IGNORECASE)
        if match:
            charset = match.group(1).strip("\"'")
    try:
        text = body.decode(charset, errors="replace")
    except LookupError:
        text = body.decode("utf-8", errors="replace")
    return _redact_text(text)


def _filter_headers(headers, deny: frozenset[str]) -> dict[str, str]:
    return {
        k: v
        for k, v in headers.items()
        if k.lower() not in deny
    }


def _fetch_with_urllib(url: str) -> tuple[int, dict[str, str], bytes]:
    """GET *url* using stdlib when httpx is unavailable."""
    import urllib.error
    import urllib.request

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "hacs-highschoolscores-explore/0.1"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status_code = resp.status
            response_headers = {k: v for k, v in resp.headers.items()}
            content = resp.read()
    except urllib.error.HTTPError as exc:
        status_code = exc.code
        response_headers = {k: v for k, v in exc.headers.items()}
        content = exc.read()
    return status_code, response_headers, content


def capture(
    url: str,
    *,
    slice_id: str = "",
    notes: str = "",
    client: httpx.Client | None = None,
) -> dict:
    """GET *url*, cache raw bytes, return sanitized capture metadata."""
    raw_path, meta_path = _cache_paths(url)

    if meta_path.exists() and raw_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))

    time.sleep(MIN_REQUEST_INTERVAL_S)

    if client is not None:
        response = client.get(url)
        status_code = response.status_code
        content = response.content
        content_type = response.headers.get("content-type")
        request_headers = _filter_headers(
            response.request.headers, _SENSITIVE_REQUEST_HEADERS
        )
        response_headers = _filter_headers(
            response.headers, _SENSITIVE_RESPONSE_HEADERS
        )
    elif httpx is not None:
        with httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "hacs-highschoolscores-explore/0.1"},
        ) as http_client:
            response = http_client.get(url)
            status_code = response.status_code
            content = response.content
            content_type = response.headers.get("content-type")
            request_headers = _filter_headers(
                response.request.headers, _SENSITIVE_REQUEST_HEADERS
            )
            response_headers = _filter_headers(
                response.headers, _SENSITIVE_RESPONSE_HEADERS
            )
    else:
        status_code, raw_response_headers, content = _fetch_with_urllib(url)
        content_type = raw_response_headers.get("Content-Type") or raw_response_headers.get(
            "content-type"
        )
        request_headers = {"User-Agent": "hacs-highschoolscores-explore/0.1"}
        response_headers = _filter_headers(
            raw_response_headers, _SENSITIVE_RESPONSE_HEADERS
        )

    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(content)

    capture_doc = {
        "url": url,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "slice": slice_id,
        "notes": notes,
        "status_code": status_code,
        "content_type": content_type,
        "bytes": len(content),
        "cache": "miss",
        "request_headers": request_headers,
        "response_headers": response_headers,
        "body": _sanitize_body(content, content_type),
        "raw_path": str(raw_path.relative_to(REPO_ROOT)),
    }

    meta_path.write_text(
        json.dumps(capture_doc, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return capture_doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="URL to fetch (GET)")
    parser.add_argument("--slice", default="", help="Slice label for the Request Log")
    parser.add_argument("--notes", default="", help="Optional notes for the Request Log")
    args = parser.parse_args(argv)

    doc = capture(args.url, slice_id=args.slice, notes=args.notes)
    print(json.dumps(doc, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
