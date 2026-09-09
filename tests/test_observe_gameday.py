"""Tests for the Slice 12 game-day observation script (fixtures only, no live HTTP)."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_EXPLORE = REPO_ROOT / "scripts" / "explore"


def _load_observe_gameday():
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    if str(SCRIPTS_EXPLORE) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_EXPLORE))
    module_name = "observe_gameday"
    spec = importlib.util.spec_from_file_location(
        module_name,
        SCRIPTS_EXPLORE / "observe_gameday.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


observe = _load_observe_gameday()
FetchResult = observe.FetchResult

from tests.helpers.fixtures import load_schedule_page_props  # noqa: E402


def _wrap_page_props_html(page_props: dict) -> bytes:
    payload = json.dumps({"props": {"pageProps": page_props}})
    html = f'<html><script id="__NEXT_DATA__" type="application/json">{payload}</script></html>'
    return html.encode("utf-8")


def _config_output_path(tmp_path: Path) -> Path:
    return observe.OBSERVE_OUTPUT_ROOT / "pytest-runs" / tmp_path.name / "observations.jsonl"


def _valid_config_kwargs(tmp_path: Path) -> dict:
    start = datetime(2026, 9, 12, 22, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    output_path = _config_output_path(tmp_path)
    return {
        "preset_labels": ["centennial"],
        "explicit_urls": [],
        "start": start.isoformat(),
        "end": end.isoformat(),
        "interval_seconds": 600,
        "output_path": output_path,
    }


@pytest.fixture(autouse=True)
def _clear_observe_test_output(tmp_path):
    path = _config_output_path(tmp_path)
    if path.exists():
        path.unlink()
    yield


def _make_config(tmp_path: Path, **overrides):
    kwargs = _valid_config_kwargs(tmp_path)
    kwargs.update(overrides)
    return observe.build_observation_config(**kwargs)


def test_main_without_approval_performs_zero_http(tmp_path, monkeypatch):
    fetch_calls: list[str] = []

    def _fake_fetch(url: str) -> FetchResult:
        fetch_calls.append(url)
        return FetchResult(200, b"", None, {}, {})

    monkeypatch.setattr(observe, "run_observation", lambda config: 0)
    monkeypatch.setattr(observe, "fetch_url", _fake_fetch)

    start = "2026-09-12T22:00:00+00:00"
    end = "2026-09-12T23:00:00+00:00"
    exit_code = observe.main(
        [
            "--target",
            "centennial",
            "--start",
            start,
            "--end",
            end,
            "--interval",
            "600",
        ]
    )

    assert exit_code == 2
    assert fetch_calls == []


def test_invalid_interval_rejected_before_fetch(tmp_path):
    with pytest.raises(observe.ObservationConfigError, match="5–10 minutes"):
        _make_config(tmp_path, interval_seconds=120)


def test_end_before_start_rejected_before_fetch(tmp_path):
    with pytest.raises(observe.ObservationConfigError, match="after --start"):
        _make_config(
            tmp_path,
            start="2026-09-12T23:00:00+00:00",
            end="2026-09-12T22:00:00+00:00",
        )


def test_naive_timestamp_rejected_before_fetch(tmp_path):
    with pytest.raises(observe.ObservationConfigError, match="timezone offset"):
        _make_config(
            tmp_path,
            start="2026-09-12T22:00:00",
            end="2026-09-12T23:00:00+00:00",
        )


def test_no_targets_rejected_before_fetch(tmp_path):
    with pytest.raises(observe.ObservationConfigError, match="at least one schedule"):
        _make_config(tmp_path, preset_labels=[])


def test_http_403_stops_entire_run_without_polling_other_targets(tmp_path):
    config = _make_config(
        tmp_path,
        preset_labels=["centennial", "bainbridge"],
    )
    calls: list[str] = []

    def fetch_fn(url: str) -> FetchResult:
        calls.append(url)
        return FetchResult(403, b"blocked", "text/html", {}, {})

    clock = {"now": config.start_utc}

    def now_fn() -> datetime:
        return clock["now"]

    exit_code = observe.run_observation(
        config,
        fetch_fn=fetch_fn,
        sleep_fn=lambda _seconds: None,
        now_fn=now_fn,
    )

    assert exit_code == 3
    assert len(calls) == 1
    lines = _config_output_path(tmp_path).read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["http_status"] == 403
    assert record["terminal"] is True
    assert record["stop_reason"] == "http_403"


def test_http_429_stops_entire_run(tmp_path):
    config = _make_config(tmp_path)
    exit_code = observe.run_observation(
        config,
        fetch_fn=lambda _url: FetchResult(429, b"", None, {}, {}),
        sleep_fn=lambda _seconds: None,
        now_fn=lambda: config.start_utc,
    )
    assert exit_code == 3
    record = json.loads(
        _config_output_path(tmp_path).read_text(encoding="utf-8").strip()
    )
    assert record["http_status"] == 429
    assert record["terminal"] is True


def test_synthetic_schedule_records_raw_contest_state(tmp_path):
    page_props = load_schedule_page_props("centennial/schedule-26-27.json")
    html = _wrap_page_props_html(page_props)
    config = _make_config(tmp_path)
    clock = {"now": config.start_utc}

    observe.run_observation(
        config,
        fetch_fn=lambda _url: FetchResult(200, html, "text/html", {}, {}),
        sleep_fn=lambda seconds: clock.__setitem__(
            "now", clock["now"] + timedelta(seconds=seconds)
        ),
        now_fn=lambda: clock["now"],
    )

    record = json.loads(
        _config_output_path(tmp_path).read_text(encoding="utf-8").strip().splitlines()[0]
    )
    scheduled_rows = [
        row for row in record["contests"] if row["contest_state"] == 2
    ]
    assert scheduled_rows
    assert scheduled_rows[0]["provider_datetime"] == "2026-09-04T19:30:00"
    assert "featured_game" in record


def test_observation_has_utc_capture_and_naive_provider_datetime_without_latency(tmp_path):
    page_props = load_schedule_page_props("centennial/schedule-26-27.json")
    captured = datetime(2026, 9, 12, 22, 15, 30, tzinfo=timezone.utc)
    target = observe.ObservationTarget("centennial", "https://example.com/schedule/")

    record = observe.build_poll_record(
        captured_at_utc=captured,
        target=target,
        http_status=200,
        page_props=page_props,
    )
    assert record["captured_at_utc"].endswith("+00:00")
    parsed_capture = datetime.fromisoformat(record["captured_at_utc"])
    assert parsed_capture.tzinfo is not None
    assert parsed_capture.utcoffset() == timedelta(0)

    sample = next(row for row in record["contests"] if row["contest_id"])
    assert "T" in sample["provider_datetime"]
    assert "+" not in sample["provider_datetime"]
    assert "Z" not in sample["provider_datetime"]

    forbidden_latency_keys = {
        "kickoff_latency",
        "minutes_after_kickoff",
        "latency_seconds",
        "provider_to_capture_delta",
    }
    assert forbidden_latency_keys.isdisjoint(record.keys())
    for row in record["contests"]:
        assert forbidden_latency_keys.isdisjoint(row.keys())


def test_observation_loop_uses_mocked_sleep_without_real_wait(tmp_path):
    page_props = load_schedule_page_props("centennial/schedule-26-27.json")
    html = _wrap_page_props_html(page_props)
    start = datetime(2026, 9, 12, 22, 0, tzinfo=timezone.utc)
    end = start + timedelta(minutes=20)
    config = observe.build_observation_config(
        preset_labels=["centennial"],
        explicit_urls=[],
        start=start.isoformat(),
        end=end.isoformat(),
        interval_seconds=600,
        output_path=_config_output_path(tmp_path),
    )

    clock_state = {"now": start}
    slept: list[float] = []
    fetch_count = 0

    def fetch_fn(_url: str) -> FetchResult:
        nonlocal fetch_count
        fetch_count += 1
        return FetchResult(200, html, "text/html", {}, {})

    def sleep_fn(seconds: float) -> None:
        slept.append(seconds)
        clock_state["now"] = clock_state["now"] + timedelta(seconds=seconds)

    exit_code = observe.run_observation(
        config,
        fetch_fn=fetch_fn,
        sleep_fn=sleep_fn,
        now_fn=lambda: clock_state["now"],
    )

    assert exit_code == 0
    assert fetch_count == 2
    assert slept == [600.0, 600.0]
    assert len(_config_output_path(tmp_path).read_text().strip().splitlines()) == 2
