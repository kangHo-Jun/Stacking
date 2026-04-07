from __future__ import annotations

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from bin_packing import evaluate_vehicle_feasibility, filter_feasible_vehicles, load_vehicle_db
from input_parser import load_material_db, process_orders


MATERIAL_PATH = ROOT_DIR / "data" / "자재정보.csv"
VEHICLE_PATH = ROOT_DIR / "data" / "차량정보.csv"
TARGET_KEY = "석고보드_일반_900x1800_12.5"


def test_vehicle_db_load() -> None:
    vehicles = load_vehicle_db(VEHICLE_PATH)
    assert len(vehicles) == 6


def test_T02_overweight_critical() -> None:
    material_db = load_material_db(MATERIAL_PATH)
    vehicles = load_vehicle_db(VEHICLE_PATH)
    order_result = process_orders(
        material_db,
        [{"material_key": TARGET_KEY, "quantity": 127}],
    )

    evaluations = evaluate_vehicle_feasibility(order_result["items"], vehicles)
    one_ton = next(item for item in evaluations if item["vehicle_name"] == "1톤_트럭")

    assert order_result["total_weight_kg"] >= 1200
    assert one_ton["feasible"] is False


def test_feasible_vehicles_exist() -> None:
    material_db = load_material_db(MATERIAL_PATH)
    vehicles = load_vehicle_db(VEHICLE_PATH)
    order_result = process_orders(
        material_db,
        [{"material_key": TARGET_KEY, "quantity": 40}],
    )

    feasible = filter_feasible_vehicles(order_result["items"], vehicles)
    assert len(feasible) >= 1


def test_all_vehicles_infeasible() -> None:
    material_db = load_material_db(MATERIAL_PATH)
    vehicles = load_vehicle_db(VEHICLE_PATH)
    order_result = process_orders(
        material_db,
        [{"material_key": TARGET_KEY, "quantity": 9999}],
    )

    feasible = filter_feasible_vehicles(order_result["items"], vehicles)
    assert len(feasible) == 0


def test_T01_regression() -> None:
    material_db = load_material_db(MATERIAL_PATH)
    order_result = process_orders(
        material_db,
        [{"material_key": TARGET_KEY, "quantity": 50}],
    )

    assert order_result["items"][0]["pallet_count"] == 2
