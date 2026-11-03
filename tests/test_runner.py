import json
import subprocess
import sys
from pathlib import Path
import run_monitor
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_MONITOR = PROJECT_ROOT / "run_monitor.py"


def test_count_must_be_positive():
    result = subprocess.run(
        [
            sys.executable,
            str(RUN_MONITOR),
            "--count",
            "0",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "--count must be at least 1" in result.stderr


def test_interval_must_be_positive():
    result = subprocess.run(
        [
            sys.executable,
            str(RUN_MONITOR),
            "--interval",
            "0",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "--interval must be at least 1 second" in result.stderr


def test_count_runs_and_appends_history(tmp_path):
    output_file = tmp_path / "custom-report.json"
    history_file = PROJECT_ROOT / "reports" / "history.jsonl"

    previous_lines = (
        len(history_file.read_text(encoding="utf-8").splitlines())
        if history_file.exists()
        else 0
    )

    result = subprocess.run(
        [
            sys.executable,
            str(RUN_MONITOR),
            "--url",
            "https://example.com",
            "--interval",
            "1",
            "--count",
            "2",
            "--output",
            str(output_file),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert output_file.exists()

    new_lines = history_file.read_text(
        encoding="utf-8"
    ).splitlines()[previous_lines:]

    assert len(new_lines) == 2

    records = [json.loads(line) for line in new_lines]
    assert [record["run_number"] for record in records] == [1, 2]
    
def test_load_targets_from_config(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    config_file = config_dir / "targets.json"
    config_file.write_text(
        json.dumps({
            "targets": [
                "https://example.com",
                "https://httpbin.org/status/200",
            ],
            "response_time_threshold_ms": 1500,
        }),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    targets, threshold = run_monitor.load_targets()

    assert targets == [
        "https://example.com",
        "https://httpbin.org/status/200",
    ]

    assert threshold == 1500


def test_load_targets_rejects_empty_list(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    (config_dir / "targets.json").write_text(
        json.dumps({"targets": []}),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="non-empty targets list"):
        run_monitor.load_targets()


def test_load_targets_rejects_invalid_url(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    (config_dir / "targets.json").write_text(
        json.dumps({"targets": ["not-a-url"]}),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="valid HTTP or HTTPS URL"):
        run_monitor.load_targets()    
        

def test_get_healthy_proxies_excludes_unhealthy():
    proxies = [
        "http://healthy-proxy:8080",
        "http://unhealthy-proxy:8080",
    ]

    results = [
        {"healthy": True},
        {"healthy": False},
    ]

    assert run_monitor.get_healthy_proxies(
        proxies,
        results,
    ) == ["http://healthy-proxy:8080"]