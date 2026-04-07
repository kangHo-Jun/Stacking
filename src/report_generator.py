from __future__ import annotations

import json
from pathlib import Path


RISK_LABELS = {
    "overweight_risk": "과적",
    "axle_limit": "축중",
    "space_utilization": "공간",
    "front_rear_deviation": "전후편차",
    "left_right_deviation": "좌우편차",
    "top_share": "상단비중",
    "fragile_bottom_pressure": "취약자재",
}


def _build_report_payload(
    order_result: dict[str, object],
    selection_result: dict[str, object],
    load_result: dict[str, object],
    risk_result: dict[str, object],
) -> dict[str, object]:
    selected_vehicle = dict(selection_result["selected_vehicle"])
    category_levels = dict(risk_result["category_levels"])
    total_pallets = sum(int(item.get("pallet_count", 0)) for item in order_result["items"])

    return {
        "차량": selected_vehicle["vehicle_name"],
        "총운임": int(selection_result["total_freight_krw"]),
        "총중량": float(order_result["total_weight_kg"]),
        "팔레트수": total_pallets,
        "위험도": risk_result["final_level"],
        "현장매뉴얼": risk_result["manual"],
        "편차": {
            "전후": float(load_result["front_rear_deviation_pct"]),
            "좌우": float(load_result["left_right_deviation_pct"]),
            "상단비중": float(load_result["top_share_pct"]),
        },
        "혼적위반": bool(load_result["mix_group_violation"]),
        "축중초과": bool(load_result["axle_overload_critical"]),
        "항목별위험도": {
            RISK_LABELS[key]: value
            for key, value in category_levels.items()
        },
    }


def _build_instruction_text(
    order_result: dict[str, object],
    selection_result: dict[str, object],
    risk_result: dict[str, object],
) -> str:
    vehicle_name = selection_result["selected_vehicle"]["vehicle_name"]
    total_weight = float(order_result["total_weight_kg"])
    lines = [
        f"차량명: {vehicle_name}",
        f"총중량: {total_weight:.1f}kg",
        "팔레트 순서:",
    ]

    pallet_sequence = 1
    for item in order_result["items"]:
        pallet_count = int(item.get("pallet_count", 0))
        for _ in range(pallet_count):
            lines.append(f"{pallet_sequence}. {item['material_key']}")
            pallet_sequence += 1

    lines.extend(
        [
            f"위험도: {risk_result['final_level']}",
            f"현장 조치: {risk_result['manual']}",
        ]
    )
    return "\n".join(lines) + "\n"


def generate_report(
    order_result: dict[str, object],
    selection_result: dict[str, object],
    load_result: dict[str, object],
    risk_result: dict[str, object],
    output_dir: str | Path,
) -> dict[str, Path]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    payload = _build_report_payload(order_result, selection_result, load_result, risk_result)
    instruction_text = _build_instruction_text(order_result, selection_result, risk_result)

    json_path = destination / "result.json"
    text_path = destination / "지시서.txt"

    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    text_path.write_text(instruction_text, encoding="utf-8")

    return {
        "json_path": json_path,
        "instruction_path": text_path,
    }
