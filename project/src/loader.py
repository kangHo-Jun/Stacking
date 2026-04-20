from __future__ import annotations

import math
from typing import Iterable


# 표준 팔레트 치수 (mm)
_PALLET_LONG_MM = 1800.0
_PALLET_SHORT_MM = 900.0


def _compute_floor_grid(
    cargo_length_mm: float,
    cargo_width_mm: float,
) -> tuple[int, int, float, float]:
    """실제 적재함 치수로 바닥 팔레트 배치 그리드 계산.

    Returns:
        (cols, rows, pallet_len_mm, pallet_wid_mm)
        — cols: 길이 방향 열 수, rows: 폭 방향 행 수
    """
    # 방향1: 1800mm 길이 방향
    cols1 = max(1, int(cargo_length_mm // _PALLET_LONG_MM))
    rows1 = max(1, int(cargo_width_mm // _PALLET_SHORT_MM))

    # 방향2: 900mm 길이 방향 (회전)
    cols2 = max(1, int(cargo_length_mm // _PALLET_SHORT_MM))
    rows2 = max(1, int(cargo_width_mm // _PALLET_LONG_MM))

    if cols2 * rows2 > cols1 * rows1:
        return cols2, rows2, _PALLET_SHORT_MM, _PALLET_LONG_MM
    return cols1, rows1, _PALLET_LONG_MM, _PALLET_SHORT_MM


def _deviation_ratio_percent(first_weight: float, second_weight: float, total_weight: float) -> float:
    if total_weight <= 0:
        return 0.0
    return abs(first_weight - second_weight) / total_weight * 100


def _make_pallets(order_items: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    pallets: list[dict[str, object]] = []

    for item in order_items:
        if "quantity" not in item or "pallet_capacity" not in item:
            pallet_count = max(int(item.get("pallet_count", 1)), 1)
            pallet_weight = float(item["total_weight_kg"]) / pallet_count
            pallet_volume = float(item.get("total_volume_m3", 0.0)) / pallet_count
            handling_grade = str(item.get("handling_grade", ""))
            preferred_position = str(item.get("preferred_position", "하단"))
            for pallet_index in range(pallet_count):
                pallets.append(
                    {
                        "material_key": item.get("material_key", ""),
                        "handling_grade": handling_grade,
                        "preferred_position": preferred_position,
                        "weight_kg": pallet_weight,
                        "volume_m3": pallet_volume,
                        "qty": 1,
                        "unit_type": "pallet",
                        "material_name": item.get("material_name", item.get("material_key", "")),
                        "sequence": pallet_index,
                    }
                )
            continue

        pallet_capacity = max(int(item.get("pallet_capacity", 1)), 1)
        quantity = max(int(item.get("quantity", 0)), 0)
        unit_weight = float(item["total_weight_kg"]) / max(quantity, 1)
        unit_volume = float(item.get("total_volume_m3", 0.0)) / max(quantity, 1)
        handling_grade = str(item.get("handling_grade", ""))
        preferred_position = str(item.get("preferred_position", "하단"))
        full_pallets = quantity // pallet_capacity
        remainder = quantity % pallet_capacity

        for pallet_index in range(full_pallets):
            pallets.append(
                {
                    "material_key": item.get("material_key", ""),
                    "handling_grade": handling_grade,
                    "preferred_position": preferred_position,
                    "weight_kg": unit_weight * pallet_capacity,
                    "volume_m3": unit_volume * pallet_capacity,
                    "qty": pallet_capacity,
                    "unit_type": "pallet",
                    "material_name": item.get("material_name", item.get("material_key", "")),
                    "sequence": pallet_index,
                }
            )
        if remainder:
            pallets.append(
                {
                    "material_key": item.get("material_key", ""),
                    "handling_grade": handling_grade,
                    "preferred_position": preferred_position,
                    "weight_kg": unit_weight * remainder,
                    "volume_m3": unit_volume * remainder,
                    "qty": remainder,
                    "unit_type": "sheet",
                    "material_name": item.get("material_name", item.get("material_key", "")),
                    "sequence": full_pallets,
                }
            )

    return pallets


def _plan_loading_from_pallets(selected_vehicle: dict[str, object], pallets: list[dict[str, object]]) -> dict[str, object]:
    ordered_pallets = sorted(
        pallets,
        key=lambda pallet: (
            0 if str(pallet.get("preferred_position", "하단")) == "하단" else 1,
            -float(pallet.get("weight_kg", 0.0)),
            0 if str(pallet.get("unit_type", "pallet")) == "pallet" else 1,
        ),
    )

    cargo_length_mm = float(selected_vehicle.get("cargo_length_mm", 10100.0))
    cargo_width_mm = float(selected_vehicle.get("cargo_width_mm", 2400.0))
    cols, rows, pallet_len, pallet_wid = _compute_floor_grid(cargo_length_mm, cargo_width_mm)
    slots_per_layer = cols * rows

    placements: list[dict[str, object]] = []

    for index, pallet in enumerate(ordered_pallets):
        # 바닥(1층) 슬롯 인덱스 — slots_per_layer 초과 시 2층
        floor_slot = index % slots_per_layer
        col = floor_slot // rows
        row = floor_slot % rows

        # 슬롯 중심 좌표
        x_mm = (col + 0.5) * pallet_len
        y_mm = (row + 0.5) * pallet_wid
        x_ratio = min(x_mm / cargo_length_mm, 1.0)

        longitudinal = "front" if col < math.ceil(cols / 2) else "rear"
        lateral = "left" if row < math.ceil(rows / 2) else "right"
        vertical = "bottom" if index < slots_per_layer else "top"

        placements.append(
            {
                **pallet,
                "longitudinal_zone": longitudinal,
                "lateral_zone": lateral,
                "vertical_zone": vertical,
                "x_ratio": x_ratio,
            }
        )

    total_weight = sum(pallet["weight_kg"] for pallet in placements)
    front_weight = sum(pallet["weight_kg"] for pallet in placements if pallet["longitudinal_zone"] == "front")
    rear_weight = total_weight - front_weight
    left_weight = sum(pallet["weight_kg"] for pallet in placements if pallet["lateral_zone"] == "left")
    right_weight = total_weight - left_weight
    top_weight = sum(pallet["weight_kg"] for pallet in placements if pallet["vertical_zone"] == "top")

    front_rear_deviation_pct = _deviation_ratio_percent(front_weight, rear_weight, total_weight)
    left_right_deviation_pct = _deviation_ratio_percent(left_weight, right_weight, total_weight)
    top_share_pct = (top_weight / total_weight * 100) if total_weight > 0 else 0.0

    axle_count = max(int(selected_vehicle.get("axles", 1)), 1)
    cargo_length_mm = float(selected_vehicle.get("cargo_length_mm", 0.0))
    axle_positions = [
        cargo_length_mm * ((index + 0.5) / axle_count)
        for index in range(axle_count)
    ]
    axle_loads = [0.0 for _ in range(axle_count)]

    for pallet in placements:
        pallet_x = float(pallet["x_ratio"]) * cargo_length_mm
        nearest_axle_index = min(
            range(axle_count),
            key=lambda index: abs(axle_positions[index] - pallet_x),
        )
        axle_loads[nearest_axle_index] += float(pallet["weight_kg"])

    axle_overload_critical = any(load > 10_000 for load in axle_loads)

    top_below_bottom_violation = any(
        str(pallet.get("preferred_position", "")) == "상단" and pallet["vertical_zone"] == "bottom"
        for pallet in placements
    ) and any(
        str(pallet.get("preferred_position", "")) == "하단" and pallet["vertical_zone"] == "top"
        for pallet in placements
    )
    max_weight_kg = float(selected_vehicle.get("max_weight_kg", 0.0))
    cargo_volume_m3 = float(selected_vehicle.get("cargo_volume_m3", 0.0))
    weight_ratio_pct = (total_weight / max_weight_kg * 100) if max_weight_kg > 0 else 0.0
    volume_ratio_pct = (sum(pallet["volume_m3"] for pallet in placements) / cargo_volume_m3 * 100) if cargo_volume_m3 > 0 else 0.0

    return {
        "selected_vehicle": selected_vehicle,
        "placements": placements,
        "total_weight_kg": total_weight,
        "front_rear_deviation_pct": front_rear_deviation_pct,
        "left_right_deviation_pct": left_right_deviation_pct,
        "top_share_pct": top_share_pct,
        "weight_ratio_pct": weight_ratio_pct,
        "volume_ratio_pct": volume_ratio_pct,
        "front_rear_critical": front_rear_deviation_pct >= 35.0,
        "axle_loads_kg": axle_loads,
        "axle_overload_critical": axle_overload_critical,
        "top_below_bottom_violation": top_below_bottom_violation,
        "slots_per_layer": slots_per_layer,
        "floor_grid": {"cols": cols, "rows": rows},
    }


def plan_loading(selected_vehicle: dict[str, object], order_items: Iterable[dict[str, object]]) -> dict[str, object]:
    return _plan_loading_from_pallets(selected_vehicle, _make_pallets(order_items))


def plan_fleet_loading(selection_result: dict[str, object]) -> dict[str, object]:
    vehicle_results: list[dict[str, object]] = []
    total_weight_kg = 0.0
    for allocation in selection_result.get("vehicle_allocations", []):
        vehicle = dict(allocation["vehicle"])
        pallets = list(allocation.get("assigned_pallets", []))
        load_result = _plan_loading_from_pallets(vehicle, pallets)
        vehicle_results.append(
            {
                "vehicle": vehicle,
                "assigned_pallets": pallets,
                "load_result": load_result,
            }
        )
        total_weight_kg += float(load_result["total_weight_kg"])

    return {
        "vehicle_results": vehicle_results,
        "vehicle_counts": dict(selection_result.get("vehicle_counts", {})),
        "total_weight_kg": total_weight_kg,
        "total_freight_krw": int(selection_result.get("total_freight_krw", 0)),
    }
