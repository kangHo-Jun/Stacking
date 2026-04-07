from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from input_parser import load_material_db, process_orders


DATA_PATH = ROOT_DIR / "data" / "자재정보.csv"
TARGET_KEY = "석고보드_일반_900x1800_12.5"


def test_db_load() -> None:
    material_db = load_material_db(DATA_PATH)
    assert len(material_db) >= 10


def test_T01_pallet_conversion() -> None:
    material_db = load_material_db(DATA_PATH)
    result = process_orders(
        material_db,
        [{"material_key": TARGET_KEY, "quantity": 50}],
    )

    assert result["items"][0]["pallet_count"] == 2


def test_total_weight() -> None:
    material_db = load_material_db(DATA_PATH)
    result = process_orders(
        material_db,
        [{"material_key": TARGET_KEY, "quantity": 40}],
    )

    assert result["items"][0]["total_weight_kg"] == pytest.approx(380.0)


def test_invalid_material() -> None:
    material_db = load_material_db(DATA_PATH)

    with pytest.raises(ValueError):
        process_orders(
            material_db,
            [{"material_key": "없는_자재_키", "quantity": 1}],
        )


def test_multi_order() -> None:
    material_db = load_material_db(DATA_PATH)
    result = process_orders(
        material_db,
        [
            {"material_key": TARGET_KEY, "quantity": 40},
            {"material_key": "석고보드_방수_900x1800_12.5", "quantity": 10},
        ],
    )

    assert len(result["items"]) == 2
