from __future__ import annotations

import json
from pathlib import Path


def test_main_normal(first_material_key: str, feasible_quantity: int) -> None:
    from conftest import OUTPUT_DIR, run_main_cli

    result_json = OUTPUT_DIR / "result.json"
    if result_json.exists():
        result_json.unlink()

    completed = run_main_cli(first_material_key, feasible_quantity)

    assert completed.returncode == 0
    assert result_json.exists()
    payload = json.loads(result_json.read_text(encoding="utf-8"))
    assert payload["차량"]


def test_main_no_feasible(first_material_key: str, infeasible_quantity: int) -> None:
    from conftest import run_main_cli

    completed = run_main_cli(first_material_key, infeasible_quantity)

    assert completed.returncode == 1
    assert "적재 불가 - 분할 배차 필요" in completed.stdout


def test_full_regression(
    first_material_key: str,
    feasible_quantity: int,
    material_db: dict[str, dict[str, object]],
    vehicle_db: list[dict[str, object]],
) -> None:
    from conftest import OUTPUT_DIR, run_main_cli, run_pipeline

    result_json = OUTPUT_DIR / "result.json"
    completed = run_main_cli(first_material_key, feasible_quantity)
    expected = run_pipeline(
        material_db,
        vehicle_db,
        [{"material_key": first_material_key, "quantity": feasible_quantity}],
    )

    assert completed.returncode == 0
    assert result_json.exists()
    payload = json.loads(result_json.read_text(encoding="utf-8"))
    assert payload["차량"] == expected["selection"]["selected_vehicle"]["vehicle_name"]
