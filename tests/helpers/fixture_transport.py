"""Fixture-backed transport for MaxPreps client tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tests.helpers.fixtures import (
    FIXTURES_ROOT,
    load_schedule_page_props,
    load_search_page_props,
    load_sport_seasons,
    wrap_page_props_in_html,
)
from custom_components.maxpreps.urls import build_search_url

_BLANK_HTML = (
    "<!DOCTYPE html><html><head><title>Test</title></head><body></body></html>"
)


class FixtureUrlNotMappedError(LookupError):
    """Raised when a test requests a URL with no committed fixture mapping."""


class FixtureTransport:
    """Map committed fixture ``source_url`` values to synthetic Next.js HTML."""

    def __init__(self) -> None:
        self.requested_urls: list[str] = []
        self._url_to_html = _build_fixture_url_map()

    def fetch(self, url: str) -> str:
        self.requested_urls.append(url)
        try:
            return self._url_to_html[url]
        except KeyError as exc:
            raise FixtureUrlNotMappedError(f"No fixture mapped for URL: {url}") from exc


def _build_fixture_url_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for fixture_path in sorted(FIXTURES_ROOT.rglob("*.json")):
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        source_url = fixture.get("source_url")
        if not isinstance(source_url, str) or not source_url:
            continue
        mapping[source_url] = _html_for_fixture(fixture_path, fixture)
    _apply_search_url_overrides(mapping)
    return mapping


def _apply_search_url_overrides(mapping: dict[str, str]) -> None:
    """Map client-built search URLs (Slice 10 saint retry and qualifier cases)."""
    empty_search_html = wrap_page_props_in_html({"initialSchoolResults": None})

    st_edward_fixture = FIXTURES_ROOT / "st-edward" / "search-st-edward.json"
    st_edward_html = wrap_page_props_in_html(load_search_page_props(st_edward_fixture))

    pike_county_fixture = FIXTURES_ROOT / "pike-county" / "search-pike-county.json"
    pike_county_html = wrap_page_props_in_html(load_search_page_props(pike_county_fixture))

    mapping[build_search_url("Saint Edward")] = empty_search_html
    mapping[build_search_url("St. Edward")] = st_edward_html
    mapping[build_search_url("Centennial High School")] = empty_search_html
    mapping[build_search_url("Mount Saint Joseph")] = empty_search_html
    mapping[build_search_url("Pike County")] = pike_county_html


def _html_for_fixture(fixture_path: Path, fixture: dict[str, Any]) -> str:
    name = fixture_path.name
    if name.startswith("search-"):
        return wrap_page_props_in_html(load_search_page_props(fixture_path))

    if name.startswith("sport-seasons-"):
        page_props = {"schoolContext": {"sportSeasons": load_sport_seasons(fixture_path)}}
        return wrap_page_props_in_html(page_props)

    if "schedule" in name:
        page_props = load_schedule_page_props(fixture_path)
        if page_props is None:
            return _BLANK_HTML
        return wrap_page_props_in_html(page_props)

    raise ValueError(f"Unsupported fixture type for URL mapping: {fixture_path}")
