from __future__ import annotations

import math

import pytest

from input_parser import process_orders


def test_db_load(material_db: dict[str, dict[str, object]], material_row_count: int) -> None:
    assert len(material_db) == material_row_count


def test_T01_pallet_conversion(
    material_db: dict[str, dict[str, object]],
    first_material: dict[str, object],
    first_material_key: str,
) -> None:
    quantity = int(first_material["팔레트당적재수"]) + 1
    result = process_orders(material_db, [{"material_key": first_material_key, "quantity": quantity}])
    expected = math.ceil(quantity / int(first_material["팔레트당적재수"]))
    assert result["items"][0]["pallet_count"] == expected


def test_total_weight(
    material_db: dict[str, dict[str, object]],
    first_material: dict[str, object],
    first_material_key: str,
) -> None:
    quantity = min(40, max(1, int(first_material["팔레트당적재수"])))
    result = process_orders(material_db, [{"material_key": first_material_key, "quantity": quantity}])
    expected = quantity * float(first_material["낱장무게(kg)"])
    assert result["items"][0]["total_weight_kg"] == pytest.approx(expected)


def test_invalid_material(material_db: dict[str, dict[str, object]]) -> None:

    with pytest.raises(ValueError):
        process_orders(
            material_db,
            [{"material_key": "없는_자재_키", "quantity": 1}],
        )


def test_multi_order(material_db: dict[str, dict[str, object]], first_material_key: str) -> None:
    result = process_orders(
        material_db,
        [
            {"material_key": first_material_key, "quantity": 1},
            {"material_key": first_material_key, "quantity": 2},
        ],
    )

    assert len(result["items"]) == 2
