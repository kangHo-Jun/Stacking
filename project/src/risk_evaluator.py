from __future__ import annotations


LEVEL_ORDER = {
    "Safe": 0,
    "Caution": 1,
    "Danger": 2,
    "Critical": 3,
}


def _highest_level(levels: list[str]) -> str:
    return max(levels, key=lambda level: LEVEL_ORDER[level])


def _weight_level(weight_ratio_pct: float) -> str:
    if weight_ratio_pct <= 85:
        return "Safe"
    if weight_ratio_pct < 95:
        return "Caution"
    if weight_ratio_pct <= 100:
        return "Danger"
    return "Critical"


def _space_level(volume_ratio_pct: float) -> str:
    if volume_ratio_pct <= 70:
        return "Safe"
    if volume_ratio_pct <= 95:
        return "Caution"
    return "Danger"


def _deviation_level(deviation_pct: float) -> str:
    if deviation_pct <= 10:
        return "Safe"
    if deviation_pct <= 20:
        return "Caution"
    if deviation_pct <= 30:
        return "Danger"
    return "Critical"


def _top_share_level(top_share_pct: float) -> str:
    if top_share_pct <= 40:
        return "Safe"
    if top_share_pct <= 60:
        return "Caution"
    return "Danger"


def _has_mix_group_violation(assigned_pallets: list[dict]) -> bool:
    """같은 차량에 서로 다른 혼적그룹이 섞여 있으면 True."""
    groups = {str(p.get("mix_group", "")) for p in assigned_pallets if str(p.get("mix_group", ""))}
    return len(groups) > 1


def evaluate_risk(load_result: dict[str, object]) -> dict[str, object]:
    weight_ratio_pct = float(load_result.get("weight_ratio_pct", 0.0))
    volume_ratio_pct = float(load_result.get("volume_ratio_pct", 0.0))
    front_rear_deviation_pct = float(load_result.get("front_rear_deviation_pct", 0.0))
    left_right_deviation_pct = float(load_result.get("left_right_deviation_pct", 0.0))
    top_share_pct = float(load_result.get("top_share_pct", 0.0))
    front_rear_critical = bool(load_result.get("front_rear_critical", False))
    axle_overload_critical = bool(load_result.get("axle_overload_critical", False))
    top_below_bottom_violation = bool(load_result.get("top_below_bottom_violation", False))
    fragile_bottom_pressure = bool(load_result.get("fragile_bottom_pressure", False))
    mix_group_violation = bool(load_result.get("mix_group_violation", False))
    stack_limit_exceeded = bool(load_result.get("stack_limit_exceeded", False))

    category_levels = {
        "overweight_risk": _weight_level(weight_ratio_pct),
        "axle_limit": "Critical" if axle_overload_critical else "Safe",
        "space_utilization": _space_level(volume_ratio_pct),
        "front_rear_deviation": "Critical" if front_rear_critical else _deviation_level(front_rear_deviation_pct),
        "left_right_deviation": _deviation_level(left_right_deviation_pct),
        "top_share": _top_share_level(top_share_pct),
        "fragile_bottom_pressure": "Danger" if fragile_bottom_pressure else "Safe",
        "mix_group_violation": "Danger" if mix_group_violation else "Safe",
        "stack_limit_exceeded": "Caution" if stack_limit_exceeded else "Safe",
    }
    final_level = _highest_level(list(category_levels.values()))
    manual = {
        "Safe": "표준 결속 및 상차 사진 촬영 후 출고",
        "Caution": "주의 수준입니다. 편차와 공간 사용률을 재확인하고 필요 시 재배치 후 출고하십시오.",
        "Danger": "위험 수준입니다. 상단 적재 또는 취약 자재 압박을 해소한 뒤 재검토하십시오.",
        "Critical": "즉시 중단 후 과적, 축중, 편차 문제를 먼저 해소하십시오.",
    }[final_level]

    return {
        "category_levels": category_levels,
        "final_level": final_level,
        "manual": manual,
    }


def evaluate_fleet_risk(fleet_load_result: dict[str, object]) -> dict[str, object]:
    vehicle_risks: list[dict[str, object]] = []
    levels: list[str] = []

    for vehicle_result in fleet_load_result.get("vehicle_results", []):
        assigned_pallets = vehicle_result.get("assigned_pallets", [])
        load_result = dict(vehicle_result["load_result"])
        load_result["mix_group_violation"] = _has_mix_group_violation(assigned_pallets)
        risk = evaluate_risk(load_result)

        vehicle_risks.append(
            {
                "vehicle": vehicle_result["vehicle"],
                "risk": risk,
                "load_result": load_result,
                "assigned_pallets": assigned_pallets,
            }
        )
        levels.append(risk["final_level"])

    final_level = _highest_level(levels) if levels else "Safe"
    manual = {
        "Safe": "표준 결속 및 상차 사진 촬영 후 출고",
        "Caution": "주의 수준입니다. 편차와 공간 사용률을 재확인하고 필요 시 재배치 후 출고하십시오.",
        "Danger": "위험 수준입니다. 상단 적재 또는 취약 자재 압박을 해소한 뒤 재검토하십시오.",
        "Critical": "즉시 중단 후 과적, 축중, 편차 문제를 먼저 해소하십시오.",
    }[final_level]

    return {
        "vehicle_risks": vehicle_risks,
        "final_level": final_level,
        "manual": manual,
    }
