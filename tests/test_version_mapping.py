"""§7.1 version-syntax evidence — hassfest-equivalent AwesomeVersion + PEP 440.

Re-runs the candidate matrix so the Slice 3 mapping cannot silently rot.
Uses the same AwesomeVersion ensure_strategy list as hassfest verify_version
(home-assistant/core script/hassfest/manifest.py, HA 2026.9.0).
"""

from __future__ import annotations

import json
from importlib.metadata import version as pkg_version
from pathlib import Path

import pytest
from awesomeversion import AwesomeVersion, AwesomeVersionStrategy
from packaging.version import Version

HASSFEST_STRATEGIES = [
    AwesomeVersionStrategy.CALVER,
    AwesomeVersionStrategy.SEMVER,
    AwesomeVersionStrategy.SIMPLEVER,
    AwesomeVersionStrategy.BUILDVER,
    AwesomeVersionStrategy.PEP440,
]

CANDIDATES = (
    "v0.1.0-beta.1",
    "0.1.0-beta.1",
    "0.1.0b1",
    "v0.1.0b1",
    "v0.1.0",
    "0.1.0",
)

# Locked mapping for Slice 4/6 (see docs/PHASE5_PLAN.md Slice 3 Implementation Notes).
FIRST_BETA_TAG = "v0.1.0-beta.1"
FIRST_BETA_MANIFEST = "0.1.0-beta.1"
FIRST_STABLE_TAG = "v0.1.0"
FIRST_STABLE_MANIFEST = "0.1.0"


def _hassfest_accept(value: str) -> AwesomeVersion:
    """Mirror hassfest verify_version acceptance."""
    return AwesomeVersion(value, ensure_strategy=HASSFEST_STRATEGIES)


def test_all_candidates_pass_hassfest_equivalent() -> None:
    """Every §7.1 candidate is accepted by hassfest-equivalent AwesomeVersion."""
    for candidate in CANDIDATES:
        av = _hassfest_accept(candidate)
        assert str(av)


def test_beta_tag_and_manifest_compare_equal() -> None:
    """Slice 4 may compare first-beta tag to manifest with AwesomeVersion."""
    tag_av = _hassfest_accept(FIRST_BETA_TAG)
    manifest_av = _hassfest_accept(FIRST_BETA_MANIFEST)
    assert tag_av == manifest_av


def test_beta_tag_not_equal_pep440_canonical_manifest() -> None:
    """Do not put 0.1.0b1 in manifest when the git tag is v0.1.0-beta.1."""
    tag_av = _hassfest_accept(FIRST_BETA_TAG)
    pep_manifest_av = _hassfest_accept("0.1.0b1")
    assert tag_av != pep_manifest_av


def test_stable_tag_and_manifest_compare_equal() -> None:
    tag_av = _hassfest_accept(FIRST_STABLE_TAG)
    manifest_av = _hassfest_accept(FIRST_STABLE_MANIFEST)
    assert tag_av == manifest_av


def test_naive_removeprefix_matches_locked_beta_pair() -> None:
    assert FIRST_BETA_TAG.removeprefix("v") == FIRST_BETA_MANIFEST


def test_naive_removeprefix_matches_locked_stable_pair() -> None:
    assert FIRST_STABLE_TAG.removeprefix("v") == FIRST_STABLE_MANIFEST


def test_pep440_beta_candidates_are_prerelease() -> None:
    for candidate in ("0.1.0-beta.1", "0.1.0b1", "v0.1.0-beta.1", "v0.1.0b1"):
        pep_input = candidate.removeprefix("v")
        assert Version(pep_input).is_prerelease
        assert Version(pep_input).public == "0.1.0b1"


def test_pep440_stable_candidates_not_prerelease() -> None:
    for candidate in ("0.1.0", "v0.1.0"):
        assert not Version(candidate.removeprefix("v")).is_prerelease


def test_current_manifest_matches_locked_first_beta() -> None:
    """Tree manifest must match FIRST_BETA_MANIFEST (not PEP440 0.1.0b1)."""
    manifest_path = (
        Path(__file__).resolve().parent.parent
        / "custom_components"
        / "high_school_sports_scores"
        / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["version"] == FIRST_BETA_MANIFEST
    assert manifest["version"] != "0.1.0b1"


@pytest.mark.parametrize("candidate", CANDIDATES)
def test_candidate_hassfest_and_pep440_accept(candidate: str) -> None:
    _hassfest_accept(candidate)
    Version(candidate.removeprefix("v"))


def test_awesomeversion_package_version_recorded() -> None:
    """Pin evidence: record awesomeversion version used by HA 2026.9.0 dependency tree."""
    av_ver = pkg_version("awesomeversion")
    assert av_ver  # e.g. 25.8.0 when homeassistant==2026.9.0 is installed
