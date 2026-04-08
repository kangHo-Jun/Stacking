from __future__ import annotations

import math

from bin_packing import evaluate_vehicle_feasibility, filter_feasible_vehicles, load_vehicle_db
from input_parser import process_orders


def test_vehicle_db_load(vehicle_db: list[dict[str, object]], vehicle_row_count: int) -> None:
    assert len(vehicle_db) == vehicle_row_count


def test_T02_overweight_critical(
    material_db: dict[str, dict[str, object]],
    vehicle_db: list[dict[str, object]],
    first_material: dict[str, object],
    first_material_key: str,
) -> None:
    lightest_vehicle = min(vehicle_db, key=lambda vehicle: float(vehicle["max_weight_kg"]))
    quantity = math.floor(float(lightest_vehicle["max_weight_kg"]) / float(first_material["낱장무게(kg)"])) + 1
    order_result = process_orders(material_db, [{"material_key": first_material_key, "quantity": quantity}])
    evaluations = evaluate_vehicle_feasibility(order_result["items"], vehicle_db)
    target = next(item for item in evaluations if item["vehicle_name"] == lightest_vehicle["vehicle_name"])
    assert order_result["total_weight_kg"] > float(lightest_vehicle["max_weight_kg"])
    assert target["feasible"] is False


def test_feasible_vehicles_exist(
    material_db: dict[str, dict[str, object]],
    vehicle_db: list[dict[str, object]],
    first_material_key: str,
    feasible_quantity: int,
) -> None:
    order_result = process_orders(material_db, [{"material_key": first_material_key, "quantity": feasible_quantity}])
    feasible = filter_feasible_vehicles(order_result["items"], vehicle_db)
    assert len(feasible) >= 1


def test_all_vehicles_infeasible(
    material_db: dict[str, dict[str, object]],
    vehicle_db: list[dict[str, object]],
    first_material_key: str,
    infeasible_quantity: int,
) -> None:
    order_result = process_orders(material_db, [{"material_key": first_material_key, "quantity": infeasible_quantity}])
    feasible = filter_feasible_vehicles(order_result["items"], vehicle_db)
    assert len(feasible) == 0


def test_T01_regression(
    material_db: dict[str, dict[str, object]],
    first_material: dict[str, object],
    first_material_key: str,
) -> None:
    quantity = int(first_material["팔레트당적재수"]) + 1
    order_result = process_orders(material_db, [{"material_key": first_material_key, "quantity": quantity}])
    expected = math.ceil(quantity / int(first_material["팔레트당적재수"]))
    assert order_result["items"][0]["pallet_count"] == expected
