from __future__ import annotations

import sys

from input_parser import process_orders
from loader import plan_fleet_loading
from vehicle_selector import select_optimal_vehicle
from visualizer import build_vehicle_visualization


def _sample_vehicle() -> dict[str, object]:
    return {
        "vehicle_name": "시각화_테스트차량",
        "cargo_length_mm": 3600.0,
        "cargo_width_mm": 1800.0,
        "cargo_height_mm": 1800.0,
    }


def _sample_items() -> list[dict[str, object]]:
    return [
        {"material_name": "중량팔레트", "material_key": "중량팔레트", "weight_kg": 1200.0, "qty": 160, "unit_type": "pallet", "vertical_zone": "bottom"},
        {"material_name": "경량팔레트", "material_key": "경량팔레트", "weight_kg": 900.0, "qty": 160, "unit_type": "pallet", "vertical_zone": "bottom"},
        {"material_name": "낱장묶음", "material_key": "낱장묶음", "weight_kg": 320.0, "qty": 24, "unit_type": "sheet", "vertical_zone": "top"},
        {"material_name": "낱장추가", "material_key": "낱장추가", "weight_kg": 180.0, "qty": 12, "unit_type": "sheet", "vertical_zone": "top"},
        {"material_name": "보조팔레트", "material_key": "보조팔레트", "weight_kg": 850.0, "qty": 160, "unit_type": "pallet", "vertical_zone": "bottom"},
        {"material_name": "후순위낱장", "material_key": "후순위낱장", "weight_kg": 90.0, "qty": 8, "unit_type": "sheet", "vertical_zone": "top"},
        {"material_name": "상층팔레트", "material_key": "상층팔레트", "weight_kg": 700.0, "qty": 160, "unit_type": "pallet", "vertical_zone": "top"},
    ]


def test_floor_plan_svg() -> None:
    # build_vehicle_visualization now expects (vehicle, load_result_dict)
    load_result = {"placements": _sample_items(), "floor_grid": {"cols": 4, "rows": 2}}
    visualization = build_vehicle_visualization(_sample_vehicle(), load_result)
    assert visualization["floor_plan"].startswith("<svg")
    assert "평면도" in visualization["floor_plan"]


def test_pallet_order() -> None:
    load_result = {"placements": _sample_items(), "floor_grid": {"cols": 4, "rows": 2}}
    visualization = build_vehicle_visualization(_sample_vehicle(), load_result)
    items = visualization["items"]

    assert items[0]["material"] == "중량팔레트"
    assert items[0]["unit"] == "pallet"
    assert items[1]["weight"] >= items[2]["weight"]


def test_layer_assigned() -> None:
    load_result = {"placements": _sample_items(), "floor_grid": {"cols": 4, "rows": 2}}
    visualization = build_vehicle_visualization(_sample_vehicle(), load_result)
    items = visualization["items"]
    # Ensure items have 'layer' key (pre-processed by build_vehicle_visualization)
    layers = {item["layer"] for item in items}

    assert 1 in layers
    assert 2 in layers


def test_unit_type() -> None:
    load_result = {"placements": _sample_items(), "floor_grid": {"cols": 4, "rows": 2}}
    visualization = build_vehicle_visualization(_sample_vehicle(), load_result)
    items = visualization["items"]
    units = {item["unit"] for item in items}

    assert units == {"pallet", "sheet"}


def test_full_regression(
    material_db: dict[str, dict[str, object]],
    vehicle_db: list[dict[str, object]],
    first_material_key: str,
) -> None:
    sys.path.insert(0, "src")
    import app as webapp

    order_result = process_orders(
        material_db,
        [{"material_key": first_material_key, "quantity": max(1, int(material_db[first_material_key]["팔레트당적재수"]) + 5)}],
    )
    selection_result = select_optimal_vehicle(vehicle_db, order_result["items"])
    fleet_load_result = plan_fleet_loading(selection_result)
    visualizations = webapp.build_fleet_visualizations(fleet_load_result)
    client = webapp.app.test_client()
    response = client.post(
        "/run",
        data={"material_key": [first_material_key], "quantity[]": ["10"]},
    )
    payload = response.get_json()

    assert visualizations
    assert response.status_code == 200
    assert payload is not None
    # '시각화SVG' is still kept for backward compatibility test
    assert "시각화SVG" in payload
    # New JSON keys for Canvas engine
    assert "packed_items" in payload
    assert "팔레트목록" in payload
