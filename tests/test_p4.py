from __future__ import annotations

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from bin_packing import filter_feasible_vehicles, load_vehicle_db
from input_parser import load_material_db, process_orders
from loader import plan_loading
from vehicle_selector import select_optimal_vehicle


MATERIAL_PATH = ROOT_DIR / "data" / "자재정보.csv"
VEHICLE_PATH = ROOT_DIR / "data" / "차량정보.csv"
TARGET_KEY = "석고보드_일반_900x1800_12.5"


def test_T03_axle_overload() -> None:
    trailer = {
        "vehicle_name": "25톤_트레일러",
        "cargo_length_mm": 12000.0,
        "axles": 2,
    }
    items = [
        {
            "material_key": "heavy_front",
            "pallet_count": 1,
            "total_weight_kg": 11000.0,
            "total_volume_m3": 1.0,
            "mix_group": "G2",
        }
    ]

    result = plan_loading(trailer, items)

    assert result["axle_overload_critical"] is True


def test_T04_front_rear_deviation() -> None:
    vehicle = {
        "vehicle_name": "5톤_윙바디",
        "cargo_length_mm": 6000.0,
        "axles": 2,
    }
    items = [
        {
            "material_key": "front_item",
            "pallet_count": 1,
            "total_weight_kg": 675.0,
            "total_volume_m3": 1.0,
            "mix_group": "G1",
        },
        {
            "material_key": "rear_item",
            "pallet_count": 1,
            "total_weight_kg": 325.0,
            "total_volume_m3": 1.0,
            "mix_group": "G2",
        },
    ]

    result = plan_loading(vehicle, items)

    assert result["front_rear_deviation_pct"] == 35.0
    assert result["front_rear_critical"] is True


def test_mix_group_violation() -> None:
    vehicle = {
        "vehicle_name": "5톤_윙바디",
        "cargo_length_mm": 6000.0,
        "axles": 2,
    }
    items = [
        {"material_key": "g1", "pallet_count": 1, "total_weight_kg": 100.0, "total_volume_m3": 1.0, "mix_group": "G1"},
        {"material_key": "g4", "pallet_count": 1, "total_weight_kg": 100.0, "total_volume_m3": 1.0, "mix_group": "G4"},
    ]

    result = plan_loading(vehicle, items)

    assert result["mix_group_violation"] is True


def test_mix_group_ok() -> None:
    vehicle = {
        "vehicle_name": "5톤_윙바디",
        "cargo_length_mm": 6000.0,
        "axles": 2,
    }
    items = [
        {"material_key": "g1", "pallet_count": 1, "total_weight_kg": 100.0, "total_volume_m3": 1.0, "mix_group": "G1"},
        {"material_key": "g2", "pallet_count": 1, "total_weight_kg": 100.0, "total_volume_m3": 1.0, "mix_group": "G2"},
    ]

    result = plan_loading(vehicle, items)

    assert result["mix_group_violation"] is False


def test_P1_P2_P3_regression() -> None:
    material_db = load_material_db(MATERIAL_PATH)
    vehicles = load_vehicle_db(VEHICLE_PATH)
    order_result = process_orders(
        material_db,
        [{"material_key": TARGET_KEY, "quantity": 40}],
    )
    feasible = filter_feasible_vehicles(order_result["items"], vehicles)
    selection = select_optimal_vehicle(feasible)

    assert order_result["items"][0]["pallet_count"] == 1
    assert len(feasible) >= 1
    assert selection["selected_vehicle"]["vehicle_name"] == "1톤_트럭"
