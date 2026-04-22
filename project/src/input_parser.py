from __future__ import annotations

import csv
import math
import os
from pathlib import Path
from typing import Iterable

try:
    from src.sheets_client import load_material_sheet
except ImportError:
    from sheets_client import load_material_sheet

DEFAULT_BOX_SPEC_MM = (1000.0, 1000.0)
DEFAULT_BOX_HEIGHT_MM = 500.0


def _normalize_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _parse_number(value: str) -> float | None:
    cleaned = _normalize_text(value)
    if cleaned in {"", "-", "—"}:
        return None
    return float(cleaned)


# 컬럼명 매핑: Google Sheets / CSV 변형 모두 지원
_COL_ALIASES: dict[str, list[str]] = {
    "규격(mm)": ["규격(mm)", "규격", "spec", "size", "사이즈"],
    "두께(mm)": ["두께(mm)", "두께", "thickness", "T"],
    "낱장무게(kg)": ["낱장무게(kg)", "낱장무게", "weight", "무게(kg)", "무게"],
    "팔레트당적재수": ["팔레트당적재수", "팔레트수", "pallet_qty", "qty"],
    "팔레트무게(kg)": ["팔레트무게(kg)", "팔레트무게", "pallet_weight"],
    "취급등급": ["취급등급", "등급", "grade"],
    "방향고정": ["방향고정", "고정", "fixed"],
    "적재위치": ["적재위치", "위치", "position"],
    "혼적그룹": ["혼적그룹", "혼적불가그룹", "mix_group", "group"],
}


def _get_col(row: dict, canonical: str, default: str = "") -> str:
    """컬럼명 별칭을 통해 안전하게 값을 가져옵니다."""
    for alias in _COL_ALIASES.get(canonical, [canonical]):
        if alias in row:
            return _normalize_text(row[alias])
    return default


def _build_material_key(row: dict[str, str]) -> str:
    name = _normalize_text(row["자재명"])
    # 구글 시트 신규 컬럼(가로/세로 분리) 우선, 구버전(규격) fallback
    if "가로(mm)" in row and "세로(mm)" in row:
        w = _normalize_text(row["가로(mm)"])
        l = _normalize_text(row["세로(mm)"])
        spec = f"{w}x{l}"
    else:
        spec = _get_col(row, "규격(mm)")
    thickness = _get_col(row, "두께(mm)")
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
    if dimensions is None:
        width_mm, length_mm = DEFAULT_BOX_SPEC_MM
        return (width_mm * length_mm * DEFAULT_BOX_HEIGHT_MM) / 1_000_000_000
    if thickness_mm is None:
        return None

    width_mm, length_mm = dimensions
    return (width_mm * length_mm * thickness_mm) / 1_000_000_000


def _resolve_spec_and_volume(row: dict) -> tuple[str, float | None]:
    """row에서 규격 문자열과 낱장부피(m3)를 계산해 반환합니다.
    구글 시트 신규(가로/세로 분리) 및 구버전(규격(mm) 단일) 양쪽 지원.
    """
    thickness_val = _get_col(row, "두께(mm)")
    thickness_mm = _parse_number(thickness_val)

    # ── 신규 방식: 가로(mm) + 세로(mm) 분리 컬럼 ──
    if "가로(mm)" in row and "세로(mm)" in row:
        w_raw = _normalize_text(row["가로(mm)"])
        l_raw = _normalize_text(row["세로(mm)"])
        spec_str = f"{w_raw}x{l_raw}"
        w = _parse_number(w_raw)
        l = _parse_number(l_raw)
        if w and l and thickness_mm:
            volume = (w * l * thickness_mm) / 1_000_000_000
        else:
            volume = None
        return spec_str, volume

    # ── 구버전 방식: 규격(mm) 단일 컬럼 ──
    spec_str = _get_col(row, "규격(mm)")
    volume = _calculate_unit_volume_m3(spec_str, thickness_val)
    return spec_str, volume


def load_material_db(csv_path: str | Path) -> dict[str, dict[str, object]]:
    material_db: dict[str, dict[str, object]] = {}
    use_sheets = os.environ.get("USE_SHEETS", "").strip().lower() == "true"

    if use_sheets:
        rows = load_material_sheet()
    else:
        path = Path(csv_path)
        with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            rows = list(csv.DictReader(csv_file))

    for row in rows:
        key = _build_material_key(row)
        spec_val, volume_val = _resolve_spec_and_volume(row)
        thickness_val = _get_col(row, "두께(mm)")
        pallet_qty_raw = _get_col(row, "팔레트당적재수", "1")
        material_db[key] = {
            "key": key,
            "자재명": _normalize_text(row["자재명"]),
            "규격(mm)": spec_val,
            "두께(mm)": thickness_val,
            "낱장무게(kg)": _parse_number(_get_col(row, "낱장무게(kg)")),
            "낱장부피(m3)": volume_val,
            "팔레트당적재수": int(float(pallet_qty_raw) if pallet_qty_raw else 1),
            "팔레트무게(kg)": _parse_number(_get_col(row, "팔레트무게(kg)")),
            "취급등급": _get_col(row, "취급등급", "B"),
            "방향고정": _get_col(row, "방향고정", "N"),
            "적재위치": _get_col(row, "적재위치", "하단"),
            "혼적불가그룹": _get_col(row, "혼적그룹", ""),
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
                "material_name": material["자재명"],
                "quantity": quantity,
                "pallet_count": pallet_count,
                "pallet_capacity": pallet_capacity,
                "total_weight_kg": item_weight_kg,
                "total_volume_m3": item_volume_m3,
                "handling_grade": str(material["취급등급"]),
                "preferred_position": str(material["적재위치"]),
                "direction_locked": str(material["방향고정"]),
                "mix_group": str(material.get("혼적불가그룹", "")),
            }
        )

    return {
        "items": items,
        "total_weight_kg": total_weight_kg,
        "total_volume_m3": total_volume_m3,
    }
