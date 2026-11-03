import json
import subprocess
import sys
from pathlib import Path


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