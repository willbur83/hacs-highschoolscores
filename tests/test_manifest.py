"""Manifest and domain constants for the MaxPreps integration."""

from __future__ import annotations

import json
from pathlib import Path

from custom_components.maxpreps.const import DOMAIN

MANIFEST_PATH = (
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "maxpreps"
    / "manifest.json"
)

REQUIRED_MANIFEST_KEYS = (
    "domain",
    "name",
    "version",
    "config_flow",
    "iot_class",
    "integration_type",
)


def test_domain_constant():
    """DOMAIN matches the integration package name."""
    assert DOMAIN == "maxpreps"


def test_manifest_required_keys():
    """manifest.json includes keys required for a custom integration."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for key in REQUIRED_MANIFEST_KEYS:
        assert key in manifest, f"missing manifest key: {key}"
    assert manifest["domain"] == DOMAIN
    assert manifest["version"] == "0.0.0"
