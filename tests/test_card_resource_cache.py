"""Cache-buster and loader rendering. These tests do not import Home Assistant."""

from __future__ import annotations

import hashlib
from pathlib import Path

from custom_components.high_school_sports_scores.frontend_register import (
    CARD_TAG,
    IMMUTABLE_CACHE_CONTROL,
    NO_STORE_CACHE_CONTROL,
    REVALIDATE_CACHE_CONTROL,
    bundle_cache_control,
    bundle_content_hash,
    card_bundle_url,
    card_loader_url,
    card_resource_paths,
    if_none_match,
    js_string_literal,
    render_card_loader_script,
    resource_path_from_url,
    resource_query_value,
    resource_version_from_url,
)


def test_bundle_content_hash_tracks_bytes(tmp_path: Path) -> None:
    first = tmp_path / "a.js"
    second = tmp_path / "b.js"
    first.write_bytes(b"one")
    second.write_bytes(b"two")

    assert bundle_content_hash(first) == hashlib.sha256(b"one").hexdigest()[:16]
    assert bundle_content_hash(first) != bundle_content_hash(second)
    assert bundle_content_hash(first) == bundle_content_hash(first)


def test_card_urls_include_version_hash_and_boot() -> None:
    assert card_bundle_url("0.1.0-beta.13", "abc123") == (
        "/high_school_sports_scores/high-school-sports-scores-card.js?v=0.1.0-beta.13&h=abc123"
    )
    assert card_loader_url("0.1.0-beta.13") == (
        "/high_school_sports_scores/high-school-sports-scores-card-loader.js?v=0.1.0-beta.13"
    )
    assert card_loader_url("0.1.0-beta.13", "deadbeef") == (
        "/high_school_sports_scores/high-school-sports-scores-card-loader.js"
        "?v=0.1.0-beta.13&b=deadbeef"
    )


def test_resource_query_parsing() -> None:
    url = card_bundle_url("1.2.3", "abc123")
    assert resource_path_from_url(url) == (
        "/high_school_sports_scores/high-school-sports-scores-card.js"
    )
    assert resource_version_from_url(url) == "1.2.3"
    assert resource_query_value(url, "h") == "abc123"
    assert resource_version_from_url(resource_path_from_url(url)) is None


def test_card_resource_paths_include_legacy_bundles() -> None:
    paths = card_resource_paths()
    assert "/high_school_sports_scores/high-school-sports-scores-card.js" in paths
    assert "/high_school_sports_scores/high-school-sports-scores-card.module.js" in paths
    assert "/high_school_sports_scores/high-school-sports-scores-card-loader.js" in paths


def test_bundle_cache_control_is_immutable_only_for_matching_hash() -> None:
    assert (
        bundle_cache_control(request_hash="abc123", current_hash="abc123")
        == IMMUTABLE_CACHE_CONTROL
    )
    assert (
        bundle_cache_control(request_hash="stale", current_hash="abc123")
        == REVALIDATE_CACHE_CONTROL
    )
    assert bundle_cache_control(request_hash=None, current_hash="abc123") == REVALIDATE_CACHE_CONTROL
    assert NO_STORE_CACHE_CONTROL == "no-store"


def test_if_none_match_accepts_this_strong_etag_only() -> None:
    assert if_none_match('"abc123"', "abc123")
    assert if_none_match("abc123", "abc123")
    assert if_none_match('W/"abc123", "abc123"', "abc123")
    assert if_none_match("*", "abc123")
    assert not if_none_match('"other"', "abc123")
    assert not if_none_match(None, "abc123")
    assert not if_none_match('W/"abc123"', "abc123")


def test_loader_script_points_at_the_hashed_bundle_and_is_diagnosable() -> None:
    bundle = card_bundle_url("0.1.0-beta.13", "abc123")
    script = render_card_loader_script("0.1.0-beta.13", bundle)

    assert "@@" not in script
    assert "0.1.0-beta.13" in script
    assert "abc123" in script
    assert "high-school-sports-scores-card.js" in script
    assert CARD_TAG in script
    assert "console.info" in script
    assert "console.error" in script
    assert "did not load" in script
    assert "clear the browser cache" in script
    assert "customElements.define" in script
    assert "&r=" in script or '?r="' in script or "r=" in script


def test_cached_loader_template_is_not_reread(monkeypatch) -> None:
    """Once the template is cached, rendering does not touch the file."""
    import custom_components.high_school_sports_scores.frontend_register as frontend_register

    frontend_register._loader_template = frontend_register._LOADER_TEMPLATE_PATH.read_text(
        encoding="utf-8"
    )

    def fail_read(*_args, **_kwargs):
        raise AssertionError("template was read after it was cached")

    monkeypatch.setattr(Path, "read_text", fail_read)
    script = render_card_loader_script("0.1.0-beta.13", card_bundle_url("0.1.0-beta.13", "abc"))
    assert "0.1.0-beta.13" in script
    assert "did not load" in script
    frontend_register._loader_template = None


def test_loader_script_escapes_markup() -> None:
    script = render_card_loader_script('1.0</script><img src=x onerror=alert(1)>', "https://example.test/a?b=1&c=2")

    assert "<script" not in script
    assert "<img" not in script
    assert "\\u003c" in script
    assert "\\u0026" in script
    assert js_string_literal('a&b<c>') == "a\\u0026b\\u003cc\\u003e"
