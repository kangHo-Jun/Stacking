from __future__ import annotations

import json
from pathlib import Path

from bin_packing import filter_feasible_vehicles
from input_parser import process_orders
from loader import plan_loading
from report_generator import generate_report
from risk_evaluator import evaluate_risk
from vehicle_selector import select_optimal_vehicle


def _run_pipeline_to_report(
    output_dir: Path,
    material_db: dict[str, dict[str, object]],
    vehicle_db: list[dict[str, object]],
    material_key: str,
    quantity: int,
) -> tuple[Path, dict[str, object]]:
    order_result = process_orders(material_db, [{"material_key": material_key, "quantity": quantity}])
    feasible = filter_feasible_vehicles(order_result["items"], vehicle_db)
    selection_result = select_optimal_vehicle(feasible)
    load_result = plan_loading(selection_result["selected_vehicle"], order_result["items"])
    risk_result = evaluate_risk(load_result)
    paths = generate_report(order_result, selection_result, load_result, risk_result, output_dir)
    return paths["json_path"], {
        "order_result": order_result,
        "selection_result": selection_result,
        "load_result": load_result,
        "risk_result": risk_result,
    }


def test_T07_json_generated(
    tmp_path: Path,
    material_db: dict[str, dict[str, object]],
    vehicle_db: list[dict[str, object]],
    first_material_key: str,
    feasible_quantity: int,
) -> None:
    json_path, _ = _run_pipeline_to_report(tmp_path / "output", material_db, vehicle_db, first_material_key, feasible_quantity)
    assert json_path.exists()


def test_T07_json_structure(
    tmp_path: Path,
    material_db: dict[str, dict[str, object]],
    vehicle_db: list[dict[str, object]],
    first_material_key: str,
    feasible_quantity: int,
) -> None:
    json_path, _ = _run_pipeline_to_report(tmp_path / "output", material_db, vehicle_db, first_material_key, feasible_quantity)
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert set(payload.keys()) == {
        "차량",
        "총운임",
        "총중량",
        "팔레트수",
        "위험도",
        "현장매뉴얼",
        "편차",
        "축중초과",
        "항목별위험도",
    }


def test_report_critical(tmp_path: Path) -> None:
    order_result = {
        "items": [{"material_key": "heavy", "pallet_count": 1}],
        "total_weight_kg": 12000.0,
    }
    selection_result = {
        "selected_vehicle": {"vehicle_name": "1톤_트럭"},
        "total_freight_krw": 50000,
    }
    load_result = {
        "front_rear_deviation_pct": 35.0,
        "left_right_deviation_pct": 0.0,
        "top_share_pct": 0.0,
        "axle_overload_critical": True,
    }
    risk_result = evaluate_risk(
        {
            "weight_ratio_pct": 101.0,
            "axle_overload_critical": True,
            "front_rear_deviation_pct": 35.0,
        }
    )

    paths = generate_report(order_result, selection_result, load_result, risk_result, tmp_path / "output")
    payload = json.loads(paths["json_path"].read_text(encoding="utf-8"))

    assert "즉시 중단" in payload["현장매뉴얼"]


def test_full_regression(
    tmp_path: Path,
    material_db: dict[str, dict[str, object]],
    vehicle_db: list[dict[str, object]],
    first_material_key: str,
    feasible_quantity: int,
) -> None:
    json_path, result = _run_pipeline_to_report(tmp_path / "output", material_db, vehicle_db, first_material_key, feasible_quantity)
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert payload["차량"] == result["selection_result"]["selected_vehicle"]["vehicle_name"]
    assert payload["위험도"] == result["risk_result"]["final_level"]
    assert payload["항목별위험도"]["과적"] == result["risk_result"]["category_levels"]["overweight_risk"]
