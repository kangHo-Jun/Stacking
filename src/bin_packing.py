from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from loader import plan_loading


def _parse_float(value: str, default: float = 0.0) -> float:
    cleaned = value.strip()
    return float(cleaned) if cleaned else default


def _parse_int(value: str, default: int = 0) -> int:
    cleaned = value.strip()
    return int(float(cleaned)) if cleaned else default


def load_vehicle_db(csv_path: str | Path) -> list[dict[str, object]]:
    path = Path(csv_path)
    vehicles: list[dict[str, object]] = []

    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            length_mm = _parse_float(row["적재함길이(mm)"])
            width_mm = _parse_float(row["적재함너비(mm)"])
            height_mm = _parse_float(row["적재함높이(mm)"])
            cargo_volume_m3 = (length_mm * width_mm * height_mm) / 1_000_000_000

            vehicles.append(
                {
                    "vehicle_name": row["차량명"].strip(),
                    "max_weight_kg": _parse_float(row["최대적재중량(kg)"]),
                    "cargo_length_mm": length_mm,
                    "cargo_width_mm": width_mm,
                    "cargo_height_mm": height_mm,
                    "cargo_volume_m3": cargo_volume_m3,
                    "axles": _parse_int(row["축수"], default=1),
                    "freight_cost_krw": _parse_int(row["운임(원)"], default=0),
                }
            )

    return vehicles


def evaluate_vehicle_feasibility(
    order_items: Iterable[dict[str, object]],
    vehicles: Iterable[dict[str, object]],
) -> list[dict[str, object]]:
    items = list(order_items)
    total_weight_kg = sum(float(item.get("total_weight_kg", 0.0)) for item in items)
    total_volume_m3 = sum(float(item.get("total_volume_m3", 0.0)) for item in items)
    evaluations: list[dict[str, object]] = []

    for vehicle in vehicles:
        max_weight_kg = float(vehicle["max_weight_kg"])
        cargo_volume_m3 = float(vehicle["cargo_volume_m3"])
        weight_ratio = total_weight_kg / max_weight_kg if max_weight_kg else float("inf")
        volume_ratio = total_volume_m3 / cargo_volume_m3 if cargo_volume_m3 else float("inf")

        reasons: list[str] = []
        if total_weight_kg > max_weight_kg:
            reasons.append("총 중량이 차량 최대적재중량을 초과합니다.")
        if total_volume_m3 > cargo_volume_m3:
            reasons.append("총 부피가 적재함 부피를 초과합니다.")
            
        # V10.2 Geometric & Stability Pre-Check
        if not reasons:
            try:
                load_result = plan_loading(vehicle, order_items)
                if load_result.get("unplaced"):
                    reasons.append(f"기하학적 배치 불가 (미배치 {len(load_result['unplaced'])}개 스택)")
                
                # V10.2.6 Dynamic Stability Check
                if load_result.get("dynamic_cog_pct", 0.0) > 60.0:
                    reasons.append(f"안정성 미달 (동적 COG {load_result['dynamic_cog_pct']:.1f}% > 60%)")
            except Exception as e:
                reasons.append(f"배치 엔진 오류: {str(e)}")

        evaluations.append(
            {
                "vehicle_name": vehicle["vehicle_name"],
                "feasible": not reasons,
                "reason": "적재 가능" if not reasons else " ".join(reasons),
                "freight_cost_krw": int(vehicle["freight_cost_krw"]),
                "max_weight_kg": max_weight_kg,
                "cargo_length_mm": float(vehicle["cargo_length_mm"]),
                "cargo_width_mm": float(vehicle["cargo_width_mm"]),
                "cargo_height_mm": float(vehicle["cargo_height_mm"]),
                "cargo_volume_m3": cargo_volume_m3,
                "axles": int(vehicle["axles"]),
                "weight_ratio": weight_ratio,
                "volume_ratio": volume_ratio,
                "total_weight_kg": total_weight_kg,
                "total_volume_m3": total_volume_m3,
            }
        )

    return evaluations


def filter_feasible_vehicles(
    order_items: Iterable[dict[str, object]],
    vehicles: Iterable[dict[str, object]],
) -> list[dict[str, object]]:
    evaluations = evaluate_vehicle_feasibility(order_items, vehicles)
    return [vehicle for vehicle in evaluations if vehicle["feasible"]]
