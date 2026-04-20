from __future__ import annotations

from risk_evaluator import evaluate_risk


def test_T02_overweight() -> None:
    result = evaluate_risk({"weight_ratio_pct": 101.0})
    assert result["final_level"] == "Critical"


def test_T03_axle() -> None:
    result = evaluate_risk({"axle_overload_critical": True})
    assert result["final_level"] == "Critical"


def test_T04_front_rear() -> None:
    result = evaluate_risk({"front_rear_deviation_pct": 35.0})
    assert result["final_level"] == "Critical"


def test_T05_left_right() -> None:
    result = evaluate_risk({"left_right_deviation_pct": 15.0})
    assert result["category_levels"]["left_right_deviation"] == "Caution"
    assert result["final_level"] == "Caution"


def test_top_below_bottom() -> None:
    result = evaluate_risk({"top_below_bottom_violation": True})
    assert result["category_levels"]["loading_position"] == "Danger"
    assert result["final_level"] == "Danger"


def test_T07_all_safe() -> None:
    result = evaluate_risk(
        {
            "weight_ratio_pct": 70.0,
            "axle_overload_critical": False,
            "volume_ratio_pct": 60.0,
            "front_rear_deviation_pct": 8.0,
            "left_right_deviation_pct": 5.0,
            "top_share_pct": 20.0,
            "top_below_bottom_violation": False,
        }
    )
    assert result["final_level"] == "Safe"
