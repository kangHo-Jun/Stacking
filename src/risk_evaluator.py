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


def evaluate_risk(load_result: dict[str, object]) -> dict[str, object]:
    weight_ratio_pct = float(load_result.get("weight_ratio_pct", 0.0))
    volume_ratio_pct = float(load_result.get("volume_ratio_pct", 0.0))
    front_rear_deviation_pct = float(load_result.get("front_rear_deviation_pct", 0.0))
    left_right_deviation_pct = float(load_result.get("left_right_deviation_pct", 0.0))
    top_share_pct = float(load_result.get("top_share_pct", 0.0))
    axle_overload_critical = bool(load_result.get("axle_overload_critical", False))
    fragile_bottom_pressure = bool(load_result.get("fragile_bottom_pressure", False))

    category_levels = {
        "overweight_risk": _weight_level(weight_ratio_pct),
        "axle_limit": "Critical" if axle_overload_critical else "Safe",
        "space_utilization": _space_level(volume_ratio_pct),
        "front_rear_deviation": _deviation_level(front_rear_deviation_pct),
        "left_right_deviation": _deviation_level(left_right_deviation_pct),
        "top_share": _top_share_level(top_share_pct),
        "fragile_bottom_pressure": "Danger" if fragile_bottom_pressure else "Safe",
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
