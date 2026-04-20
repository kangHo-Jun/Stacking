from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Iterable

try:
    from src.sheets_client import load_vehicle_sheet
except ImportError:
    from sheets_client import load_vehicle_sheet


def _parse_float(value: str, default: float = 0.0) -> float:
    cleaned = value.strip()
    return float(cleaned) if cleaned else default


def _parse_int(value: str, default: int = 0) -> int:
    cleaned = value.strip()
    return int(float(cleaned)) if cleaned else default


def _infer_freight_cost(max_weight_kg: float, known_cost_rows: list[tuple[float, int]]) -> int:
    same_weight_costs = [cost for weight, cost in known_cost_rows if weight == max_weight_kg]
    if same_weight_costs:
        return max(same_weight_costs)

    ordered = sorted(known_cost_rows, key=lambda item: item[0])
    lower = None
    upper = None
    for weight, cost in ordered:
        if weight < max_weight_kg:
            lower = (weight, cost)
        elif weight > max_weight_kg and upper is None:
            upper = (weight, cost)
            break

    if lower and upper:
        lower_weight, lower_cost = lower
        upper_weight, upper_cost = upper
        ratio = (max_weight_kg - lower_weight) / (upper_weight - lower_weight)
        return int(round(lower_cost + ratio * (upper_cost - lower_cost)))
    if lower:
        lower_weight, lower_cost = lower
        return int(round(lower_cost * (max_weight_kg / lower_weight)))
    if upper:
        upper_weight, upper_cost = upper
        return int(round(upper_cost * (max_weight_kg / upper_weight)))
    return 0


def load_vehicle_db(csv_path: str | Path) -> list[dict[str, object]]:
    use_sheets = os.environ.get("USE_SHEETS", "").strip().lower() == "true"
    rows: list[dict[str, object]]

    if use_sheets:
        rows = load_vehicle_sheet()
    else:
        path = Path(csv_path)
        with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            rows = list(csv.DictReader(csv_file))

    known_cost_rows = [
        (_parse_float(str(row["최대적재중량(kg)"])), _parse_int(str(row["운임(원)"])))
        for row in rows
        if str(row["운임(원)"]).strip()
    ]

    vehicles: list[dict[str, object]] = []
    for row in rows:
            length_mm = _parse_float(str(row["적재함길이(mm)"]))
            width_mm = _parse_float(str(row["적재함너비(mm)"]))
            height_mm = _parse_float(str(row["적재함높이(mm)"]))
            cargo_volume_m3 = (length_mm * width_mm * height_mm) / 1_000_000_000
            max_weight_kg = _parse_float(str(row["최대적재중량(kg)"]))
            freight_cost_krw = (
                _parse_int(str(row["운임(원)"]))
                if str(row["운임(원)"]).strip()
                else _infer_freight_cost(max_weight_kg, known_cost_rows)
            )

            vehicles.append(
                {
                    "vehicle_name": str(row["차량명"]).strip(),
                    "max_weight_kg": max_weight_kg,
                    "cargo_length_mm": length_mm,
                    "cargo_width_mm": width_mm,
                    "cargo_height_mm": height_mm,
                    "cargo_volume_m3": cargo_volume_m3,
                    "axles": _parse_int(str(row["축수"]), default=1),
                    "freight_cost_krw": freight_cost_krw,
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
