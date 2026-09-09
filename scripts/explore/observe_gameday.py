#!/usr/bin/env python3
"""Owner-run game-day observation helper for Spike H (Phase 3 Slice 12).

Research-only: samples public MaxPreps schedule pages on a narrow, bounded window
(5–10 minute interval) and appends compact JSONL observations under
``captures/private/``. This is **not** production polling and is not wired into
Home Assistant.

Example (requires explicit approval and bounded window):

    python3 scripts/explore/observe_gameday.py \\
        --i-approve-live-observation \\
        --target centennial \\
        --start 2026-09-12T18:00:00-04:00 \\
        --end 2026-09-12T22:00:00-04:00 \\
        --interval 600

Preset targets (none active by default; select with ``--target`` or ``--url``):

- ``centennial`` — Centennial (Roswell, GA) varsity football schedule
- ``bainbridge`` — Bainbridge (GA) varsity football schedule
- ``pike`` — Pike County (GA) varsity football schedule
- ``st_edward`` — St. Edward (OH) varsity football schedule
- ``pensacola`` — Pensacola (FL) varsity football schedule (optional non-Eastern)

Output: ``captures/private/observe_gameday/<run-id>/observations.jsonl``

Without ``--i-approve-live-observation`` the script exits immediately and performs
zero HTTP requests.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_SCRIPTS_EXPLORE = Path(__file__).resolve().parent
if str(_SCRIPTS_EXPLORE) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_EXPLORE))

from capture import FetchResult, fetch_url  # noqa: E402

from custom_components.maxpreps.exceptions import ContestSchemaError  # noqa: E402
from custom_components.maxpreps.parsing.contests import (  # noqa: E402
    IDX_CANONICAL_URL,
    IDX_CONTEST_ID,
    IDX_CONTEST_STATE,
    IDX_CURRENT_TEAM,
    IDX_DATE,
    IDX_HAS_RESULT,
    IDX_LOCATION,
    IDX_OPPONENT_TEAM,
    IDX_STATUS_MESSAGE,
    PART_IDX_RESULT,
    PART_IDX_SCORE,
    decode_contest_row,
    validate_contests_shape,
)
from custom_components.maxpreps.parsing.next_data import extract_page_props  # noqa: E402

OBSERVE_OUTPUT_ROOT = REPO_ROOT / "captures" / "private" / "observe_gameday"
MIN_INTERVAL_SECONDS = 300
MAX_INTERVAL_SECONDS = 600
TERMINAL_HTTP_STATUSES = frozenset({403, 429})

# Documented example/preset schedule URLs — not polled unless explicitly selected.
PRESET_TARGETS: dict[str, str] = {
    "centennial": "https://www.maxpreps.com/ga/roswell/centennial-knights/football/schedule/",
    "bainbridge": "https://www.maxpreps.com/ga/bainbridge/bainbridge-bearcats/football/schedule/",
    "pike": "https://www.maxpreps.com/ga/zebulon/pike-county-pirates/football/schedule/",
    "st_edward": "https://www.maxpreps.com/oh/lakewood/st-edward-eagles/football/schedule/",
    "pensacola": "https://www.maxpreps.com/fl/pensacola/pensacola-tigers/football/schedule/",
}

_FEATURED_COMPARE_FIELDS: tuple[tuple[str, int], ...] = (
    ("location", IDX_LOCATION),
    ("date", IDX_DATE),
    ("contestState", IDX_CONTEST_STATE),
    ("canonicalUrl", IDX_CANONICAL_URL),
)


class ObservationConfigError(ValueError):
    """Invalid observation configuration."""


@dataclass(frozen=True)
class ObservationTarget:
    """One schedule URL to observe."""

    label: str
    url: str


@dataclass(frozen=True)
class ObservationConfig:
    """Validated, bounded observation run."""

    targets: tuple[ObservationTarget, ...]
    start_utc: datetime
    end_utc: datetime
    interval_seconds: int
    output_path: Path


def parse_iso_timestamp(value: str, field_name: str) -> datetime:
    """Parse a timezone-aware ISO-8601 timestamp and normalize to UTC."""
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ObservationConfigError(
            f"{field_name} must be a timezone-aware ISO-8601 timestamp"
        ) from exc
    if parsed.tzinfo is None:
        raise ObservationConfigError(
            f"{field_name} must include a timezone offset (naive timestamps are rejected)"
        )
    return parsed.astimezone(timezone.utc)


def validate_interval_seconds(interval_seconds: int) -> int:
    if interval_seconds < MIN_INTERVAL_SECONDS or interval_seconds > MAX_INTERVAL_SECONDS:
        raise ObservationConfigError(
            f"--interval must be between {MIN_INTERVAL_SECONDS} and "
            f"{MAX_INTERVAL_SECONDS} seconds (5–10 minutes inclusive)"
        )
    return interval_seconds


def build_targets(
    preset_labels: list[str],
    explicit_urls: list[str],
) -> tuple[ObservationTarget, ...]:
    if not preset_labels and not explicit_urls:
        raise ObservationConfigError(
            "Select at least one schedule with --target <name> and/or --url <schedule-url>"
        )

    targets: list[ObservationTarget] = []
    seen_urls: set[str] = set()

    for label in preset_labels:
        key = label.strip().lower()
        if key not in PRESET_TARGETS:
            known = ", ".join(sorted(PRESET_TARGETS))
            raise ObservationConfigError(
                f"Unknown --target {label!r}; known presets: {known}"
            )
        url = PRESET_TARGETS[key]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        targets.append(ObservationTarget(label=key, url=url))

    for index, url in enumerate(explicit_urls, start=1):
        cleaned = url.strip()
        if not cleaned:
            raise ObservationConfigError("--url values must be non-empty")
        if cleaned in seen_urls:
            continue
        seen_urls.add(cleaned)
        targets.append(ObservationTarget(label=f"url-{index}", url=cleaned))

    return tuple(targets)


def build_observation_config(
    *,
    preset_labels: list[str],
    explicit_urls: list[str],
    start: str,
    end: str,
    interval_seconds: int,
    output_path: Path | None = None,
) -> ObservationConfig:
    if not start.strip() or not end.strip():
        raise ObservationConfigError("--start and --end are required (bounded window)")

    start_utc = parse_iso_timestamp(start, "--start")
    end_utc = parse_iso_timestamp(end, "--end")
    if end_utc <= start_utc:
        raise ObservationConfigError("--end must be after --start")

    interval = validate_interval_seconds(interval_seconds)
    targets = build_targets(preset_labels, explicit_urls)

    if output_path is None:
        run_id = start_utc.strftime("%Y%m%dT%H%M%SZ")
        output_path = OBSERVE_OUTPUT_ROOT / run_id / "observations.jsonl"

    if not str(output_path.resolve()).startswith(str(OBSERVE_OUTPUT_ROOT.resolve())):
        raise ObservationConfigError(
            f"Output must stay under {OBSERVE_OUTPUT_ROOT.relative_to(REPO_ROOT)}/"
        )

    return ObservationConfig(
        targets=targets,
        start_utc=start_utc,
        end_utc=end_utc,
        interval_seconds=interval,
        output_path=output_path,
    )


def _find_contest_row(contests: list[Any], contest_id: str) -> list[Any] | None:
    for row in contests:
        if (
            isinstance(row, list)
            and len(row) > IDX_CONTEST_ID
            and row[IDX_CONTEST_ID] == contest_id
        ):
            return row
    return None


def _score_fields_from_row(row: list[Any]) -> dict[str, Any]:
    has_result = row[IDX_HAS_RESULT]
    team_score: int | None = None
    opponent_score: int | None = None
    result: str | None = None
    if has_result:
        team_score = row[IDX_CURRENT_TEAM][PART_IDX_SCORE]
        opponent_score = row[IDX_OPPONENT_TEAM][PART_IDX_SCORE]
        result = row[IDX_CURRENT_TEAM][PART_IDX_RESULT]
    return {
        "has_result": has_result,
        "team_score": team_score,
        "opponent_score": opponent_score,
        "result": result,
    }


def extract_contest_observations(
    page_props: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, str | None]:
    """Return contest rows, optional featured summary, and optional parse error."""
    contests = page_props.get("contests")
    featured = page_props.get("featuredGameData")

    team_context = page_props.get("teamContext")
    if not isinstance(team_context, dict):
        return [], None, "teamContext missing or not an object"
    data = team_context.get("data")
    if not isinstance(data, dict):
        return [], None, "teamContext.data missing or not an object"
    school_id = data.get("teamId")
    if not isinstance(school_id, str) or not school_id.strip():
        return [], None, "teamContext.data.teamId missing"

    try:
        validate_contests_shape(contests)
    except ContestSchemaError as exc:
        return [], None, str(exc)

    observations: list[dict[str, Any]] = []
    for row in contests:
        raw_datetime = row[IDX_DATE]
        scores = _score_fields_from_row(row)
        contest_obs: dict[str, Any] = {
            "contest_id": row[IDX_CONTEST_ID],
            "provider_datetime": raw_datetime,
            "contest_state": row[IDX_CONTEST_STATE],
            "status_message": row[IDX_STATUS_MESSAGE],
            **scores,
        }
        try:
            game = decode_contest_row(row, school_id.strip())
            contest_obs["decoded_status"] = game.status.value
        except ContestSchemaError:
            contest_obs["decoded_status"] = None
        observations.append(contest_obs)

    featured_summary = _featured_summary(contests, featured)
    return observations, featured_summary, None


def _featured_summary(
    contests: list[Any],
    featured: Any,
) -> dict[str, Any] | None:
    if featured is None:
        return None
    if not isinstance(featured, dict):
        return {"error": "featuredGameData is not an object"}

    featured_id = featured.get("contestId")
    summary: dict[str, Any] = {
        "contest_id": featured_id,
        "provider_datetime": featured.get("date"),
        "contest_state": featured.get("contestState"),
    }

    if not isinstance(featured_id, str) or not featured_id:
        summary["error"] = "featuredGameData missing contestId"
        return summary

    match_row = _find_contest_row(contests, featured_id)
    if match_row is None:
        summary["missing_from_contests"] = True
        return summary

    disagreements: dict[str, dict[str, Any]] = {}
    for featured_key, row_index in _FEATURED_COMPARE_FIELDS:
        featured_value = featured.get(featured_key)
        row_value = match_row[row_index]
        if featured_value != row_value:
            disagreements[featured_key] = {
                "featured": featured_value,
                "contests": row_value,
            }
    if disagreements:
        summary["disagreements"] = disagreements
    return summary


def build_poll_record(
    *,
    captured_at_utc: datetime,
    target: ObservationTarget,
    http_status: int,
    page_props: dict[str, Any] | None,
    parse_error: str | None = None,
    terminal: bool = False,
    stop_reason: str | None = None,
) -> dict[str, Any]:
    """Build one compact JSONL observation record."""
    if captured_at_utc.tzinfo is None:
        raise ValueError("captured_at_utc must be timezone-aware")

    record: dict[str, Any] = {
        "captured_at_utc": captured_at_utc.astimezone(timezone.utc).isoformat(),
        "target": target.label,
        "schedule_url": target.url,
        "http_status": http_status,
    }
    if terminal:
        record["terminal"] = True
    if stop_reason is not None:
        record["stop_reason"] = stop_reason

    if http_status != 200:
        return record

    if page_props is None:
        record["parse_error"] = parse_error or "missing pageProps"
        return record

    contests, featured, schema_error = extract_contest_observations(page_props)
    if schema_error is not None:
        record["parse_error"] = schema_error
        return record

    record["contests"] = contests
    if featured is not None:
        record["featured_game"] = featured
    return record


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
        handle.write("\n")


def run_observation(
    config: ObservationConfig,
    *,
    fetch_fn: Callable[[str], FetchResult] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    now_fn: Callable[[], datetime] | None = None,
) -> int:
    """Execute a bounded observation loop. Returns process exit code."""
    if now_fn is None:
        now_fn = lambda: datetime.now(timezone.utc)

    if fetch_fn is None:
        def _default_fetch(url: str) -> FetchResult:
            return fetch_url(url, rate_limit=True)

        fetch_fn = _default_fetch

    if now_fn() >= config.end_utc:
        return 0

    if now_fn() < config.start_utc:
        sleep_fn((config.start_utc - now_fn()).total_seconds())

    while now_fn() < config.end_utc:
        for target in config.targets:
            captured_at = now_fn()
            fetch = fetch_fn(target.url)
            page_props: dict[str, Any] | None = None
            parse_error: str | None = None

            if fetch.status_code == 200:
                try:
                    html = fetch.content.decode("utf-8", errors="replace")
                    page_props = extract_page_props(html)
                except Exception as exc:  # noqa: BLE001 - research log must continue
                    parse_error = str(exc)

            record = build_poll_record(
                captured_at_utc=captured_at,
                target=target,
                http_status=fetch.status_code,
                page_props=page_props,
                parse_error=parse_error,
            )

            if fetch.status_code in TERMINAL_HTTP_STATUSES:
                record["terminal"] = True
                record["stop_reason"] = f"http_{fetch.status_code}"
                append_jsonl(config.output_path, record)
                return 3

            append_jsonl(config.output_path, record)

        if now_fn() >= config.end_utc:
            break

        remaining = (config.end_utc - now_fn()).total_seconds()
        if remaining <= 0:
            break
        sleep_fn(min(config.interval_seconds, remaining))

    return 0


def build_argument_parser() -> argparse.ArgumentParser:
    preset_help = ", ".join(sorted(PRESET_TARGETS))
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--i-approve-live-observation",
        action="store_true",
        help="Required gate before any live MaxPreps HTTP (research-only)",
    )
    parser.add_argument(
        "--target",
        action="append",
        default=[],
        metavar="NAME",
        help=f"Preset schedule target to observe (may repeat). Known: {preset_help}",
    )
    parser.add_argument(
        "--url",
        action="append",
        default=[],
        metavar="SCHEDULE_URL",
        help="Explicit varsity schedule URL to observe (may repeat)",
    )
    parser.add_argument(
        "--start",
        required=True,
        help="Window start as timezone-aware ISO-8601 (normalized to UTC)",
    )
    parser.add_argument(
        "--end",
        required=True,
        help="Window end as timezone-aware ISO-8601 (must be after --start)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        required=True,
        help=f"Seconds between poll rounds ({MIN_INTERVAL_SECONDS}–{MAX_INTERVAL_SECONDS})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Optional JSONL path under captures/private/observe_gameday/ "
            "(default: captures/private/observe_gameday/<start-utc>/observations.jsonl)"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        config = build_observation_config(
            preset_labels=args.target,
            explicit_urls=args.url,
            start=args.start,
            end=args.end,
            interval_seconds=args.interval,
            output_path=args.output,
        )
    except ObservationConfigError as exc:
        print(f"observe_gameday: {exc}", file=sys.stderr)
        return 1

    if not args.i_approve_live_observation:
        print(
            "observe_gameday: refusing live observation without "
            "--i-approve-live-observation (zero HTTP performed)",
            file=sys.stderr,
        )
        return 2

    return run_observation(config)


if __name__ == "__main__":
    sys.exit(main())
