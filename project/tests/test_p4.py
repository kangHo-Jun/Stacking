from __future__ import annotations

from bin_packing import filter_feasible_vehicles
from input_parser import process_orders
from loader import plan_loading
from vehicle_selector import select_optimal_vehicle


def test_T03_axle_overload(vehicle_db: list[dict[str, object]]) -> None:
    trailer_ref = max(vehicle_db, key=lambda vehicle: float(vehicle["max_weight_kg"]))
    trailer = {
        "vehicle_name": trailer_ref["vehicle_name"],
        "cargo_length_mm": float(trailer_ref["cargo_length_mm"]),
        "axles": 2,
    }
    items = [
        {
            "material_key": "heavy_front",
            "pallet_count": 1,
            "total_weight_kg": 11000.0,
            "total_volume_m3": 1.0,
            "preferred_position": "하단",
        }
    ]

    result = plan_loading(trailer, items)

    assert result["axle_overload_critical"] is True


def test_T04_front_rear_deviation(vehicle_db: list[dict[str, object]]) -> None:
    vehicle = {
        "vehicle_name": "test_split_truck",
        "cargo_length_mm": 1800.0,
        "cargo_width_mm": 900.0,
        "axles": 2,
    }
    total_weight = 1000.0
    front_weight = total_weight * (1 + 0.35) / 2
    rear_weight = total_weight - front_weight
    items = [
        {
            "material_key": "front_item",
            "pallet_count": 1,
            "total_weight_kg": front_weight,
            "total_volume_m3": 1.0,
            "preferred_position": "하단",
        },
        {
            "material_key": "rear_item",
            "pallet_count": 1,
            "total_weight_kg": rear_weight,
            "total_volume_m3": 1.0,
            "preferred_position": "하단",
        },
    ]

    result = plan_loading(vehicle, items)

    assert result["front_rear_deviation_pct"] == 35.0
    assert result["front_rear_critical"] is True


def test_bottom_first(vehicle_db: list[dict[str, object]]) -> None:
    vehicle_ref = vehicle_db[0]
    vehicle = {
        "vehicle_name": vehicle_ref["vehicle_name"],
        "cargo_length_mm": float(vehicle_ref["cargo_length_mm"]),
        "axles": int(vehicle_ref["axles"]),
    }
    items = [
        {"material_key": "top_item", "pallet_count": 1, "total_weight_kg": 100.0, "total_volume_m3": 1.0, "preferred_position": "상단"},
        {"material_key": "bottom_item", "pallet_count": 1, "total_weight_kg": 150.0, "total_volume_m3": 1.0, "preferred_position": "하단"},
    ]

    result = plan_loading(vehicle, items)

    assert result["placements"][0]["preferred_position"] == "하단"


def test_top_last(vehicle_db: list[dict[str, object]]) -> None:
    vehicle_ref = vehicle_db[0]
    vehicle = {
        "vehicle_name": vehicle_ref["vehicle_name"],
        "cargo_length_mm": float(vehicle_ref["cargo_length_mm"]),
        "axles": int(vehicle_ref["axles"]),
    }
    items = [
        {"material_key": "top_item", "pallet_count": 1, "total_weight_kg": 100.0, "total_volume_m3": 1.0, "preferred_position": "상단"},
        {"material_key": "bottom_item", "pallet_count": 2, "total_weight_kg": 300.0, "total_volume_m3": 2.0, "preferred_position": "하단"},
    ]

    result = plan_loading(vehicle, items)

    assert result["placements"][-1]["preferred_position"] == "상단"


def test_P1_P2_P3_regression(
    material_db: dict[str, dict[str, object]],
    vehicle_db: list[dict[str, object]],
    first_material_key: str,
    feasible_quantity: int,
) -> None:
    order_result = process_orders(material_db, [{"material_key": first_material_key, "quantity": feasible_quantity}])
    feasible = filter_feasible_vehicles(order_result["items"], vehicle_db)
    selection = select_optimal_vehicle(feasible)

    assert order_result["items"][0]["pallet_count"] == 1
    assert selection["selected_vehicle"]["vehicle_name"] == min(
        feasible,
        key=lambda vehicle: int(vehicle["freight_cost_krw"]),
    )["vehicle_name"]
