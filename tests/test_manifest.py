"""Manifest and domain constants for the High School Sports Scores integration."""

from __future__ import annotations

import json
from pathlib import Path

from custom_components.high_school_sports_scores.const import DOMAIN

MANIFEST_PATH = (
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "high_school_sports_scores"
    / "manifest.json"
)

REQUIRED_MANIFEST_KEYS = (
    "domain",
    "name",
    "version",
    "config_flow",
    "iot_class",
    "integration_type",
    "issue_tracker",
    "documentation",
    "codeowners",
)

BRAND_ICON_PATH = (
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "high_school_sports_scores"
    / "brand"
    / "icon.png"
)


def test_domain_constant():
    """DOMAIN matches the integration package name."""
    assert DOMAIN == "high_school_sports_scores"


def test_manifest_required_keys():
    """manifest.json includes keys required for a custom integration."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for key in REQUIRED_MANIFEST_KEYS:
        assert key in manifest, f"missing manifest key: {key}"
    assert manifest["domain"] == DOMAIN
    assert manifest["version"] == "0.1.0-beta.2"


def test_version_constant_matches_manifest():
    """Integration VERSION constant stays aligned with manifest.json."""
    from custom_components.high_school_sports_scores.const import VERSION

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert VERSION == manifest["version"]


def test_brand_icon_exists():
    """HA 2026.3+ custom-integration brand icon is present on disk."""
    assert BRAND_ICON_PATH.is_file(), f"missing brand icon: {BRAND_ICON_PATH}"
