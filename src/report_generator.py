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

    unplaced = load_result.get("unplaced", [])
    
    return {
        "차량": selected_vehicle["vehicle_name"],
        "총운임": int(selection_result["total_freight_krw"]),
        "총중량": float(order_result["total_weight_kg"]),
        "팔레트수": total_pallets,
        "레이어수": int(load_result.get("layer_count", 0)),
        "미배치": len(unplaced),
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
        "미배치목록": [u["material_key"] for u in unplaced],
        "비교근거": [
            {"차량": name, "사유": reason}
            for name, reason in selection_result.get("rejection_reasons", {}).items()
        ],
        "보정정보": {
            "단계": load_result.get("correction_stage", "Fix0"),
            "이동거리": f"+{load_result.get('shift_mm_applied', 0)}mm",
            "리스크개선": load_result.get("risk_resolved", "N"),
            "동적COG": f"{load_result.get('dynamic_cog_pct', 0.0):.1f}%"
        }
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


def generate_fleet_report(
    order_result: dict[str, object],
    selection_result: dict[str, object],
    fleet_load_result: dict[str, object],
    fleet_risk_result: dict[str, object],
    output_dir: str | Path,
) -> dict[str, Path]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    vehicle_sections = []
    for vehicle_risk in fleet_risk_result.get("vehicle_risks", []):
        load_result = vehicle_risk["load_result"]
        risk_result = vehicle_risk["risk_result"]
        vehicle_name = vehicle_risk["vehicle_name"]
        pallets = vehicle_risk.get("assigned_pallets", [])
        unplaced = load_result.get("unplaced", [])
        vehicle_sections.append(
            {
                "차량": vehicle_name,
                "인스턴스": vehicle_risk.get("instance_id"),
                "총중량": float(load_result["total_weight_kg"]),
                "팔레트수": len(pallets),
                "레이어수": int(load_result.get("layer_count", 0)),
                "미배치": len(unplaced),
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
                    for key, value in risk_result["category_levels"].items()
                },
                "팔레트순서": [
                    {
                        "key": p["material_key"],
                        "rotated": p.get("is_rotated", False),
                        "layer": p.get("layer_id", 0),
                        "coords": f"({p.get('x',0)}, {p.get('y',0)}, {p.get('z',0)})"
                    }
                    for p in load_result.get("placements", [])
                ],
                "미배치목록": [u["material_key"] for u in unplaced]
            }
        )

    vehicle_summary = ", ".join(
        f"{name} x{count}"
        for name, count in selection_result.get("vehicle_counts", {}).items()
    )
    payload = {
        "차량": vehicle_summary or selection_result["selected_vehicle"]["vehicle_name"],
        "총운임": int(selection_result["total_freight_krw"]),
        "총중량": float(order_result["total_weight_kg"]),
        "팔레트수": sum(int(item.get("pallet_count", 0)) for item in order_result["items"]),
        "위험도": fleet_risk_result["final_level"],
        "현장매뉴얼": fleet_risk_result["manual"],
        "편차": vehicle_sections[0]["편차"] if vehicle_sections else {"전후": 0.0, "좌우": 0.0, "상단비중": 0.0},
        "혼적위반": any(section["혼적위반"] for section in vehicle_sections),
        "축중초과": any(section["축중초과"] for section in vehicle_sections),
        "항목별위험도": vehicle_sections[0]["항목별위험도"] if vehicle_sections else {},
        "비교근거": [
            {"차량": name, "사유": reason}
            for name, reason in selection_result.get("rejection_reasons", {}).items()
        ],
        "차량별결과": vehicle_sections,
    }

    lines = [
        f"총 차량 조합: {payload['차량']}",
        f"총 운임: {payload['총운임']}원",
        f"총 중량: {payload['총중량']:.1f}kg",
        f"전체 위험도: {payload['위험도']}",
        f"현장 조치: {payload['현장매뉴얼']}",
        "",
    ]
    for section in vehicle_sections:
        lines.append(f"[{section['인스턴스'] or section['차량']}]")
        lines.append(f"차량명: {section['차량']}")
        lines.append(f"중량: {section['총중량']:.1f}kg")
        lines.append(f"팔레트: {section['팔레트수']}")
        lines.append(f"레이어: {section['레이어수']}")
        if section["미배치"] > 0:
            lines.append(f"미배치: {section['미배치']}개 ({', '.join(section['미배치목록'])})")
        lines.append(f"위험도: {section['위험도']}")
        lines.append("팔레트 배치/회전:")
        for index, p in enumerate(section["팔레트순서"], start=1):
            rotated_str = "(회전)" if p["rotated"] else ""
            lines.append(f"{index}. L{p['layer']} {p['key']} {p['coords']} {rotated_str}")
        lines.append(f"현장 조치: {section['현장매뉴얼']}")
        lines.append("")

    json_path = destination / "result.json"
    text_path = destination / "지시서.txt"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    text_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    return {
        "json_path": json_path,
        "instruction_path": text_path,
    }
