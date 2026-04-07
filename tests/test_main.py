from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
MAIN_PATH = ROOT_DIR / "src" / "main.py"
OUTPUT_DIR = ROOT_DIR / "output"


def test_main_normal() -> None:
    result_json = OUTPUT_DIR / "result.json"
    if result_json.exists():
        result_json.unlink()

    completed = subprocess.run(
        [sys.executable, str(MAIN_PATH)],
        input="석고보드_일반_900x1800_12.5\n50\n\n",
        text=True,
        capture_output=True,
        cwd=ROOT_DIR,
        check=False,
    )

    assert completed.returncode == 0
    assert result_json.exists()
    payload = json.loads(result_json.read_text(encoding="utf-8"))
    assert payload["위험도"] == "Safe"


def test_main_no_feasible() -> None:
    completed = subprocess.run(
        [sys.executable, str(MAIN_PATH)],
        input="석고보드_일반_900x1800_12.5\n9999\n\n",
        text=True,
        capture_output=True,
        cwd=ROOT_DIR,
        check=False,
    )

    assert completed.returncode == 1
    assert "적재 불가 - 분할 배차 필요" in completed.stdout


def test_full_regression() -> None:
    result_json = OUTPUT_DIR / "result.json"
    completed = subprocess.run(
        [sys.executable, str(MAIN_PATH)],
        input="석고보드_일반_900x1800_12.5\n50\n\n",
        text=True,
        capture_output=True,
        cwd=ROOT_DIR,
        check=False,
    )

    assert completed.returncode == 0
    assert result_json.exists()
