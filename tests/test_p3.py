from __future__ import annotations

import pytest

from bin_packing import filter_feasible_vehicles
from input_parser import process_orders
from vehicle_selector import select_optimal_vehicle


def test_ortools_import() -> None:
    from ortools.linear_solver import pywraplp

    assert pywraplp.Solver.CreateSolver("SCIP") is not None


def test_T03_select_cheapest(
    material_db: dict[str, dict[str, object]],
    vehicle_db: list[dict[str, object]],
    first_material_key: str,
    feasible_quantity: int,
) -> None:
    order_result = process_orders(material_db, [{"material_key": first_material_key, "quantity": feasible_quantity}])
    feasible = filter_feasible_vehicles(order_result["items"], vehicle_db)

    result = select_optimal_vehicle(feasible)
    expected = min(feasible, key=lambda vehicle: int(vehicle["freight_cost_krw"]))

    assert result["selected_vehicle"]["vehicle_name"] == expected["vehicle_name"]
    assert result["total_freight_krw"] == int(expected["freight_cost_krw"])


def test_no_feasible_vehicle() -> None:
    with pytest.raises(ValueError):
        select_optimal_vehicle([])


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
