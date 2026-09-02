"""Test-only fixture loaders for inconsistently wrapped research JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIXTURES_ROOT = Path(__file__).resolve().parent.parent / "fixtures" / "maxpreps"


def load_fixture(path: Path | str) -> dict[str, Any]:
    """Load a committed MaxPreps research fixture file."""
    fixture_path = Path(path)
    if not fixture_path.is_absolute():
        fixture_path = FIXTURES_ROOT / fixture_path
    with fixture_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_search_page_props(path: Path | str) -> dict[str, Any]:
    """Unwrap search fixture envelope to ``pageProps``."""
    return load_fixture(path)["pageProps"]


def load_schedule_page_props(path: Path | str) -> dict[str, Any] | None:
    """Unwrap schedule fixture envelope to ``pageProps`` (may be ``None``)."""
    return load_fixture(path).get("pageProps")


def load_sport_seasons(path: Path | str) -> list[dict[str, Any]]:
    """Unwrap sport-seasons fixture envelope to the ``sportSeasons`` list."""
    fixture = load_fixture(path)
    if "schoolContext" in fixture:
        return fixture["schoolContext"]["sportSeasons"]
    return fixture["sportSeasons"]


def wrap_page_props_in_html(page_props: dict[str, Any]) -> str:
    """Wrap ``pageProps`` in a synthetic Next.js HTML document for extractor tests."""
    next_data = json.dumps({"props": {"pageProps": page_props}}, separators=(",", ":"))
    return (
        "<!DOCTYPE html><html><head><title>Test</title></head><body>"
        f'<script id="__NEXT_DATA__" type="application/json">{next_data}</script>'
        "</body></html>"
    )
