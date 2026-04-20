from __future__ import annotations

import math

import pytest

from bin_packing import filter_feasible_vehicles
from input_parser import process_orders
from vehicle_selector import select_optimal_vehicle


def test_ortools_import() -> None:
    from ortools.linear_solver import pywraplp

    assert pywraplp.Solver.CreateSolver("SCIP") is not None


def test_single_vehicle(
    material_db: dict[str, dict[str, object]],
    vehicle_db: list[dict[str, object]],
    first_material_key: str,
    feasible_quantity: int,
) -> None:
    order_result = process_orders(material_db, [{"material_key": first_material_key, "quantity": feasible_quantity}])
    result = select_optimal_vehicle(vehicle_db, order_result["items"])
    expected = min(vehicle_db, key=lambda vehicle: int(vehicle["freight_cost_krw"]))

    assert result["selected_vehicle"]["vehicle_name"] == expected["vehicle_name"]
    assert result["total_freight_krw"] == int(expected["freight_cost_krw"])
    assert sum(result["vehicle_counts"].values()) == 1


def test_no_feasible_vehicle() -> None:
    with pytest.raises(ValueError):
        select_optimal_vehicle([])


def test_multi_vehicle(
    material_db: dict[str, dict[str, object]],
    vehicle_db: list[dict[str, object]],
    first_material_key: str,
    infeasible_quantity: int,
) -> None:
    heavy_order = process_orders(material_db, [{"material_key": first_material_key, "quantity": infeasible_quantity}])
    result = select_optimal_vehicle(vehicle_db, heavy_order["items"])
    assert sum(result["vehicle_counts"].values()) >= 2
    assigned_pallets = sum(len(allocation["assigned_pallets"]) for allocation in result["vehicle_allocations"])
    assert assigned_pallets == heavy_order["items"][0]["pallet_count"]


def test_min_cost(
    material_db: dict[str, dict[str, object]],
    vehicle_db: list[dict[str, object]],
    first_material_key: str,
    infeasible_quantity: int,
) -> None:
    heavy_order = process_orders(material_db, [{"material_key": first_material_key, "quantity": infeasible_quantity}])
    result = select_optimal_vehicle(vehicle_db, heavy_order["items"])
    max_vehicle = max(vehicle_db, key=lambda vehicle: float(vehicle["max_weight_kg"]))
    max_vehicle_count = math.ceil(
        heavy_order["total_weight_kg"] / float(max_vehicle["max_weight_kg"])
    )
    upper_bound_cost = max_vehicle_count * int(max_vehicle["freight_cost_krw"])
    assert result["total_freight_krw"] <= upper_bound_cost


def test_T01_T02_regression(
    material_db: dict[str, dict[str, object]],
    vehicle_db: list[dict[str, object]],
    first_material: dict[str, object],
    first_material_key: str,
    infeasible_quantity: int,
) -> None:
    quantity = int(first_material["팔레트당적재수"]) + 1
    order = process_orders(material_db, [{"material_key": first_material_key, "quantity": quantity}])
    assert order["items"][0]["pallet_count"] >= 2

    heavy_order = process_orders(material_db, [{"material_key": first_material_key, "quantity": infeasible_quantity}])
    feasible = filter_feasible_vehicles(heavy_order["items"], vehicle_db)
    assert feasible == []
