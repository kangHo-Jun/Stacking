from __future__ import annotations

import csv
import math
import subprocess
import sys
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from bin_packing import filter_feasible_vehicles, load_vehicle_db
from input_parser import load_material_db, process_orders
from loader import plan_loading
from risk_evaluator import evaluate_risk
from vehicle_selector import select_optimal_vehicle


MATERIAL_PATH = ROOT_DIR / "data" / "자재정보.csv"
VEHICLE_PATH = ROOT_DIR / "data" / "차량정보.csv"
MAIN_PATH = ROOT_DIR / "src" / "main.py"
OUTPUT_DIR = ROOT_DIR / "output"


@pytest.fixture(scope="session")
def material_db() -> dict[str, dict[str, object]]:
    return load_material_db(MATERIAL_PATH)


@pytest.fixture(scope="session")
def vehicle_db() -> list[dict[str, object]]:
    return load_vehicle_db(VEHICLE_PATH)


@pytest.fixture(scope="session")
def first_material_key(material_db: dict[str, dict[str, object]]) -> str:
    return next(iter(material_db))


@pytest.fixture(scope="session")
def first_material(material_db: dict[str, dict[str, object]], first_material_key: str) -> dict[str, object]:
    return material_db[first_material_key]


@pytest.fixture(scope="session")
def material_row_count() -> int:
    with MATERIAL_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


@pytest.fixture(scope="session")
def vehicle_row_count() -> int:
    with VEHICLE_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


@pytest.fixture(scope="session")
def feasible_quantity() -> int:
    return 1


@pytest.fixture(scope="session")
def infeasible_quantity(first_material: dict[str, object], vehicle_db: list[dict[str, object]]) -> int:
    unit_weight = float(first_material["낱장무게(kg)"])
    max_weight = max(float(vehicle["max_weight_kg"]) for vehicle in vehicle_db)
    return math.floor(max_weight / unit_weight) + 1


def build_orders(material_key: str, quantities: list[int]) -> list[dict[str, object]]:
    return [{"material_key": material_key, "quantity": quantity} for quantity in quantities]


def run_pipeline(
    material_db: dict[str, dict[str, object]],
    vehicle_db: list[dict[str, object]],
    orders: list[dict[str, object]],
) -> dict[str, object]:
    order_result = process_orders(material_db, orders)
    feasible = filter_feasible_vehicles(order_result["items"], vehicle_db)
    result: dict[str, object] = {
        "order_result": order_result,
        "feasible": feasible,
    }
    if feasible:
        selection = select_optimal_vehicle(feasible)
        load = plan_loading(selection["selected_vehicle"], order_result["items"])
        risk = evaluate_risk(load)
        result.update(
            {
                "selection": selection,
                "load": load,
                "risk": risk,
            }
        )
    return result


def run_main_cli(material_key: str, quantity: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(MAIN_PATH)],
        input=f"{material_key}\n{quantity}\n\n",
        text=True,
        capture_output=True,
        cwd=ROOT_DIR,
        check=False,
    )
