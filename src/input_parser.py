from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Iterable


def _normalize_text(value: str) -> str:
    return value.strip()


def _parse_number(value: str) -> float | None:
    cleaned = _normalize_text(value)
    if cleaned in {"", "-", "—"}:
        return None
    return float(cleaned)


def _build_material_key(row: dict[str, str]) -> str:
    name = _normalize_text(row["자재명"])
    spec = _normalize_text(row["규격(mm)"])
    thickness = _normalize_text(row["두께(mm)"])
    return f"{name}_{spec}_{thickness}"


def _parse_spec_mm(spec: str) -> tuple[float, float] | None:
    cleaned = _normalize_text(spec)
    parts = cleaned.split("x")
    if len(parts) != 2:
        return None

    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None


def _calculate_unit_volume_m3(spec: str, thickness: str) -> float | None:
    dimensions = _parse_spec_mm(spec)
    thickness_mm = _parse_number(thickness)
    if dimensions is None or thickness_mm is None:
        return None

    width_mm, length_mm = dimensions
    return (width_mm * length_mm * thickness_mm) / 1_000_000_000


def load_material_db(csv_path: str | Path) -> dict[str, dict[str, object]]:
    path = Path(csv_path)
    material_db: dict[str, dict[str, object]] = {}

    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            key = _build_material_key(row)
            material_db[key] = {
                "key": key,
                "자재명": _normalize_text(row["자재명"]),
                "규격(mm)": _normalize_text(row["규격(mm)"]),
                "두께(mm)": _normalize_text(row["두께(mm)"]),
                "낱장무게(kg)": _parse_number(row["낱장무게(kg)"]),
                "낱장부피(m3)": _calculate_unit_volume_m3(
                    row["규격(mm)"],
                    row["두께(mm)"],
                ),
                "팔레트당적재수": int(float(_normalize_text(row["팔레트당적재수"]))),
                "팔레트무게(kg)": _parse_number(row["팔레트무게(kg)"]),
                "취급등급": _normalize_text(row["취급등급"]),
                "방향고정": _normalize_text(row["방향고정"]),
                "혼적불가그룹": _normalize_text(row["혼적불가그룹"]),
            }

    return material_db


def process_orders(
    material_db: dict[str, dict[str, object]],
    orders: Iterable[dict[str, object]],
) -> dict[str, object]:
    items: list[dict[str, object]] = []
    total_weight_kg = 0.0
    total_volume_m3 = 0.0

    for order in orders:
        material_key = str(order["material_key"])
        quantity = int(order["quantity"])

        if material_key not in material_db:
            raise ValueError(f"Unknown material key: {material_key}")

        material = material_db[material_key]
        pallet_capacity = int(material["팔레트당적재수"])
        unit_weight = material["낱장무게(kg)"]
        unit_volume_m3 = material["낱장부피(m3)"]
        if unit_weight is None:
            raise ValueError(f"Unit weight is missing for material: {material_key}")
        if unit_volume_m3 is None:
            raise ValueError(f"Unit volume is missing for material: {material_key}")

        pallet_count = math.ceil(quantity / pallet_capacity)
        item_weight_kg = float(unit_weight) * quantity
        item_volume_m3 = float(unit_volume_m3) * quantity
        total_weight_kg += item_weight_kg
        total_volume_m3 += item_volume_m3

        items.append(
            {
                "material_key": material_key,
                "quantity": quantity,
                "pallet_count": pallet_count,
                "total_weight_kg": item_weight_kg,
                "total_volume_m3": item_volume_m3,
                "mix_group": str(material["혼적불가그룹"]),
                "handling_grade": str(material["취급등급"]),
            }
        )

    return {
        "items": items,
        "total_weight_kg": total_weight_kg,
        "total_volume_m3": total_volume_m3,
    }
