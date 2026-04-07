from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from bin_packing import filter_feasible_vehicles, load_vehicle_db
from input_parser import load_material_db, process_orders
from vehicle_selector import select_optimal_vehicle


MATERIAL_PATH = ROOT_DIR / "data" / "자재정보.csv"
VEHICLE_PATH = ROOT_DIR / "data" / "차량정보.csv"
TARGET_KEY = "석고보드_일반_900x1800_12.5"


def test_ortools_import() -> None:
    from ortools.linear_solver import pywraplp

    assert pywraplp.Solver.CreateSolver("SCIP") is not None


def test_T03_select_cheapest() -> None:
    material_db = load_material_db(MATERIAL_PATH)
    vehicles = load_vehicle_db(VEHICLE_PATH)
    order_result = process_orders(
        material_db,
        [{"material_key": TARGET_KEY, "quantity": 40}],
    )
    feasible = filter_feasible_vehicles(order_result["items"], vehicles)

    result = select_optimal_vehicle(feasible)

    assert len(feasible) > 1
    assert result["selected_vehicle"]["vehicle_name"] == "1톤_트럭"
    assert result["total_freight_krw"] == 50000


def test_no_feasible_vehicle() -> None:
    with pytest.raises(ValueError):
        select_optimal_vehicle([])


def test_T01_T02_regression() -> None:
    material_db = load_material_db(MATERIAL_PATH)
    vehicles = load_vehicle_db(VEHICLE_PATH)

    order_50 = process_orders(
        material_db,
        [{"material_key": TARGET_KEY, "quantity": 50}],
    )
    assert order_50["items"][0]["pallet_count"] == 2

    order_127 = process_orders(
        material_db,
        [{"material_key": TARGET_KEY, "quantity": 127}],
    )
    feasible = filter_feasible_vehicles(order_127["items"], vehicles)
    one_ton_names = {vehicle["vehicle_name"] for vehicle in feasible}

    assert order_127["total_weight_kg"] >= 1200
    assert "1톤_트럭" not in one_ton_names
