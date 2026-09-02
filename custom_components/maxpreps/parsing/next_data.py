"""Extract Next.js pageProps from MaxPreps HTML documents."""

from __future__ import annotations

import json
import re
from typing import Any

from custom_components.maxpreps.exceptions import MalformedNextDataError, NextDataNotFoundError

_NEXT_DATA_SCRIPT = re.compile(
    r'<script[^>]*\bid=["\']__NEXT_DATA__["\'][^>]*>(?P<payload>.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)


def extract_page_props(html: str) -> dict[str, Any]:
    """Return ``props.pageProps`` from a Next.js HTML document."""
    match = _NEXT_DATA_SCRIPT.search(html)
    if match is None:
        raise NextDataNotFoundError("__NEXT_DATA__ script tag not found")

    raw_payload = match.group("payload").strip()
    try:
        next_data = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise MalformedNextDataError("Invalid JSON in __NEXT_DATA__") from exc

    try:
        page_props = next_data["props"]["pageProps"]
    except (KeyError, TypeError) as exc:
        raise NextDataNotFoundError("props.pageProps not found in __NEXT_DATA__") from exc

    if not isinstance(page_props, dict):
        raise NextDataNotFoundError("props.pageProps is not an object")

    return page_props
