from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from bin_packing import filter_feasible_vehicles, load_vehicle_db
from input_parser import load_material_db, process_orders
from loader import plan_loading
from report_generator import generate_report
from risk_evaluator import evaluate_risk
from vehicle_selector import select_optimal_vehicle


MATERIAL_PATH = ROOT_DIR / "data" / "자재정보.csv"
VEHICLE_PATH = ROOT_DIR / "data" / "차량정보.csv"
TARGET_KEY = "석고보드_일반_900x1800_12.5"


def _run_safe_pipeline(output_dir: Path) -> Path:
    material_db = load_material_db(MATERIAL_PATH)
    vehicles = load_vehicle_db(VEHICLE_PATH)
    order_result = process_orders(
        material_db,
        [{"material_key": TARGET_KEY, "quantity": 50}],
    )
    feasible = filter_feasible_vehicles(order_result["items"], vehicles)
    selection_result = select_optimal_vehicle(feasible)
    load_result = plan_loading(selection_result["selected_vehicle"], order_result["items"])
    risk_result = evaluate_risk(load_result)
    paths = generate_report(order_result, selection_result, load_result, risk_result, output_dir)
    return paths["json_path"]


def test_T07_json_generated(tmp_path: Path) -> None:
    json_path = _run_safe_pipeline(tmp_path / "output")
    assert json_path.exists()


def test_T07_json_structure(tmp_path: Path) -> None:
    json_path = _run_safe_pipeline(tmp_path / "output")
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert set(payload.keys()) == {
        "차량",
        "총운임",
        "총중량",
        "팔레트수",
        "위험도",
        "현장매뉴얼",
        "편차",
        "혼적위반",
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
        "mix_group_violation": False,
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


def test_full_regression(tmp_path: Path) -> None:
    json_path = _run_safe_pipeline(tmp_path / "output")
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert payload["차량"] == "1톤_트럭"
    assert payload["위험도"] == "Safe"
    assert payload["항목별위험도"]["과적"] == "Safe"
