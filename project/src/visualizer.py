from __future__ import annotations

import math
from typing import Iterable


SVG_WIDTH = 920
SVG_HEIGHT = 280
FLOOR_SLOT_LENGTH_MM = 1200.0
FLOOR_LANES = 2


def _unit_priority(unit_type: str) -> int:
    return 0 if unit_type == "pallet" else 1


def _floor_color(unit_type: str, layer: int) -> str:
    if unit_type == "sheet":
        return "#16a34a"
    return "#1d4ed8" if layer == 1 else "#60a5fa"


def _escape_svg(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _layout_items(vehicle: dict[str, object], load_items: Iterable[dict[str, object]]) -> tuple[list[dict[str, object]], int]:
    items = sorted(
        [dict(item) for item in load_items],
        key=lambda item: (
            -float(item.get("weight_kg", 0.0)),
            _unit_priority(str(item.get("unit_type", "pallet"))),
            str(item.get("material_key", "")),
        ),
    )

    cargo_length_mm = max(float(vehicle.get("cargo_length_mm", 0.0)), FLOOR_SLOT_LENGTH_MM)
    cargo_width_mm = max(float(vehicle.get("cargo_width_mm", 0.0)), 2000.0)
    columns_per_layer = max(1, int(cargo_length_mm // FLOOR_SLOT_LENGTH_MM))
    slots_per_layer = max(1, columns_per_layer * FLOOR_LANES)
    slot_length_mm = cargo_length_mm / columns_per_layer
    lane_width_mm = cargo_width_mm / FLOOR_LANES

    visual_items: list[dict[str, object]] = []
    for index, item in enumerate(items):
        layer = index // slots_per_layer + 1
        slot_index = index % slots_per_layer
        column = slot_index // FLOOR_LANES
        lane = slot_index % FLOOR_LANES
        x = round(column * slot_length_mm, 1)
        y = round(lane * lane_width_mm, 1)
        weight = round(float(item.get("weight_kg", 0.0)), 1)
        unit_type = str(item.get("unit_type", "pallet"))
        visual_items.append(
            {
                "order": index + 1,
                "material": str(item.get("material_name") or item.get("material_key", "")),
                "unit": unit_type,
                "qty": int(item.get("qty", 1)),
                "weight": weight,
                "x": x,
                "y": y,
                "layer": layer,
                "color": _floor_color(unit_type, layer),
                "opacity": 0.7 if unit_type == "sheet" else 0.95,
            }
        )

    return visual_items, slots_per_layer


def _build_floor_plan_svg(vehicle: dict[str, object], items: list[dict[str, object]]) -> str:
    cargo_length_mm = max(float(vehicle.get("cargo_length_mm", 0.0)), FLOOR_SLOT_LENGTH_MM)
    cargo_width_mm = max(float(vehicle.get("cargo_width_mm", 0.0)), 2000.0)
    scale_x = (SVG_WIDTH - 110) / cargo_length_mm
    scale_y = (SVG_HEIGHT - 96) / cargo_width_mm
    parts = [
        f'<svg viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="적재 평면도">',
        '<rect x="46" y="34" width="820" height="196" rx="26" fill="#f8fbff" stroke="#d8e4f5" stroke-width="2"/>',
        '<text x="48" y="24" fill="#1e293b" font-size="16" font-weight="700">평면도</text>',
        '<text x="52" y="252" fill="#64748b" font-size="13" font-weight="600">전방</text>',
        '<text x="816" y="252" fill="#64748b" font-size="13" font-weight="600">후방</text>',
        '<line x1="88" y1="246" x2="810" y2="246" stroke="#94a3b8" stroke-width="2"/>',
        '<polygon points="810,246 798,240 798,252" fill="#94a3b8"/>',
        '<rect x="664" y="10" width="14" height="14" rx="4" fill="#1d4ed8"/><text x="684" y="22" fill="#475569" font-size="12">1층</text>',
        '<rect x="728" y="10" width="14" height="14" rx="4" fill="#60a5fa"/><text x="748" y="22" fill="#475569" font-size="12">2층</text>',
        '<rect x="792" y="10" width="14" height="14" rx="4" fill="#16a34a"/><text x="812" y="22" fill="#475569" font-size="12">낱장</text>',
    ]
    for item in items:
        rect_x = 60 + float(item["x"]) * scale_x
        rect_y = 44 + float(item["y"]) * scale_y
        rect_width = max(46, cargo_length_mm * 0.14 * scale_x)
        rect_height = max(38, (cargo_width_mm / FLOOR_LANES) * 0.74 * scale_y)
        dash = ' stroke-dasharray="8 6"' if item["unit"] == "sheet" else ""
        parts.append(
            f'<rect x="{rect_x:.1f}" y="{rect_y:.1f}" width="{rect_width:.1f}" height="{rect_height:.1f}" '
            f'rx="12" fill="{item["color"]}" fill-opacity="{item["opacity"]}" stroke="{item["color"]}" stroke-width="2"{dash}/>'
        )
        parts.append(
            f'<text x="{rect_x + rect_width / 2:.1f}" y="{rect_y + rect_height / 2 + 5:.1f}" fill="white" font-size="13" text-anchor="middle" font-weight="700">{int(item["order"])}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _build_side_view_svg(vehicle: dict[str, object], items: list[dict[str, object]]) -> str:
    cargo_length_mm = max(float(vehicle.get("cargo_length_mm", 0.0)), FLOOR_SLOT_LENGTH_MM)
    max_layer = max((int(item["layer"]) for item in items), default=1)
    layer_count = max(max_layer, 2)
    scale_x = (SVG_WIDTH - 120) / cargo_length_mm
    inner_top = 28
    inner_bottom = SVG_HEIGHT - 24
    floor_y = inner_bottom - 16
    layer_height = 72
    parts = [
        f'<svg viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="적재 측면도">',
        '<rect x="46" y="34" width="820" height="196" rx="26" fill="#fbfdff" stroke="#d8e4f5" stroke-width="2"/>',
        '<text x="48" y="24" fill="#1e293b" font-size="16" font-weight="700">측면도</text>',
        f'<line x1="86" y1="{floor_y}" x2="840" y2="{floor_y}" stroke="#1e293b" stroke-width="5"/>',
    ]
    for layer in range(layer_count):
        label = f"{layer_count - layer}층"
        label_y = floor_y - layer * layer_height - 18
        guide_y = floor_y - layer * layer_height
        parts.append(f'<text x="56" y="{label_y:.1f}" fill="#64748b" font-size="13" font-weight="700">{label}</text>')
        parts.append(f'<line x1="86" y1="{guide_y:.1f}" x2="840" y2="{guide_y:.1f}" stroke="#d8e4f5" stroke-dasharray="5 5"/>')
    for item in items:
        rect_x = 96 + float(item["x"]) * scale_x
        rect_width = max(46, cargo_length_mm * 0.14 * scale_x)
        rect_height = 36 if item["unit"] == "sheet" else 42
        base_y = floor_y - rect_height
        rect_y = base_y - ((int(item["layer"]) - 1) * layer_height)
        dash = ' stroke-dasharray="8 6"' if item["unit"] == "sheet" else ""
        parts.append(
            f'<rect x="{rect_x:.1f}" y="{rect_y:.1f}" width="{rect_width:.1f}" height="{rect_height:.1f}" '
            f'rx="10" fill="{item["color"]}" fill-opacity="{item["opacity"]}" stroke="{item["color"]}" stroke-width="2"{dash}/>'
        )
        parts.append(
            f'<text x="{rect_x + rect_width / 2:.1f}" y="{rect_y + rect_height / 2 + 5:.1f}" fill="white" font-size="12" text-anchor="middle" font-weight="700">{int(item["order"])}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _build_weight_map_svg(vehicle: dict[str, object], items: list[dict[str, object]]) -> str:
    zone_names = ["앞-왼쪽", "앞-오른쪽", "뒤-왼쪽", "뒤-오른쪽"]
    zone_weights = [0.0, 0.0, 0.0, 0.0]
    cargo_length_mm = max(float(vehicle.get("cargo_length_mm", 0.0)), FLOOR_SLOT_LENGTH_MM)
    cargo_width_mm = max(float(vehicle.get("cargo_width_mm", 0.0)), 2000.0)
    total_weight = sum(float(item["weight"]) for item in items) or 1.0

    for item in items:
        front = 0 if float(item["x"]) < cargo_length_mm / 2 else 2
        right = 1 if float(item["y"]) >= cargo_width_mm / 2 else 0
        zone_weights[front + right] += float(item["weight"])

    front_weight = zone_weights[0] + zone_weights[1]
    rear_weight = zone_weights[2] + zone_weights[3]
    left_weight = zone_weights[0] + zone_weights[2]
    right_weight = zone_weights[1] + zone_weights[3]
    front_rear_deviation = abs(front_weight - rear_weight) / total_weight * 100
    left_right_deviation = abs(left_weight - right_weight) / total_weight * 100
    deviation = max(front_rear_deviation, left_right_deviation)
    risk_level = "Safe"
    if deviation > 30:
        risk_level = "Critical"
    elif deviation > 20:
        risk_level = "Danger"
    elif deviation > 10:
        risk_level = "Caution"

    risk_color = {
        "Safe": "#48BB78",
        "Caution": "#EAB308",
        "Danger": "#EF4444",
        "Critical": "#B91C1C",
    }[risk_level]
    bubble_centers = [
        (120, 92),
        (300, 92),
        (120, 196),
        (300, 196),
    ]
    fills = ["#1d4ed8", "#3b82f6", "#93c5fd", "#dbeafe"]
    parts = [
        f'<svg viewBox="0 0 420 280" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="중량 분포">',
        '<rect x="14" y="18" width="392" height="246" rx="24" fill="#fbfdff" stroke="#d8e4f5" stroke-width="2"/>',
        '<text x="18" y="16" fill="#1e293b" font-size="16" font-weight="700">버블맵</text>',
        '<text x="58" y="36" fill="#475569" font-size="12" font-weight="700">← 운전석(전방)</text>',
        '<text x="300" y="238" fill="#475569" font-size="12" font-weight="700">후방 →</text>',
        '<rect x="56" y="42" width="308" height="184" rx="24" fill="#f8fbff" stroke="#bfdbfe" stroke-width="2"/>',
        '<line x1="210" y1="50" x2="210" y2="218" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="6 6"/>',
        '<line x1="64" y1="138" x2="356" y2="138" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="6 6"/>',
    ]
    for index, zone_name in enumerate(zone_names):
        ratio = zone_weights[index] / total_weight
        pct = round(zone_weights[index] / total_weight * 100)
        radius = max(15.0, math.sqrt(ratio) * 55)
        cx, cy = bubble_centers[index]
        fill = fills[min(int((1 - ratio) * (len(fills) - 1)), len(fills) - 1)] if ratio < 1 else fills[0]
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{radius:.1f}" fill="{fill}" stroke="#1e3a8a" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{cx}" y="{cy - 10:.1f}" fill="white" font-size="13" font-weight="700" text-anchor="middle">{zone_name}</text>'
        )
        parts.append(
            f'<text x="{cx}" y="{cy + 12:.1f}" fill="white" font-size="22" font-weight="700" text-anchor="middle">{pct}%</text>'
        )
        parts.append(
            f'<text x="{cx}" y="{cy + 30:.1f}" fill="rgba(255,255,255,.92)" font-size="11" text-anchor="middle">{zone_weights[index]:.0f}kg</text>'
        )
    parts.append(
        f'<text x="64" y="250" fill="#475569" font-size="12">전후편차 {front_rear_deviation:.1f}%</text>'
    )
    parts.append(
        f'<text x="176" y="250" fill="#475569" font-size="12">좌우편차 {left_right_deviation:.1f}%</text>'
    )
    parts.append(
        f'<rect x="300" y="236" width="74" height="24" rx="12" fill="{risk_color}"/>'
    )
    parts.append(
        f'<text x="337" y="252" fill="white" font-size="12" text-anchor="middle" font-weight="700">{risk_level}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def build_vehicle_visualization(vehicle: dict[str, object], load_items: Iterable[dict[str, object]]) -> dict[str, object]:
    visual_items, slots_per_layer = _layout_items(vehicle, load_items)
    return {
        "floor_plan": _build_floor_plan_svg(vehicle, visual_items),
        "side_view": _build_side_view_svg(vehicle, visual_items),
        "weight_map": _build_weight_map_svg(vehicle, visual_items),
        "items": visual_items,
        "slots_per_layer": slots_per_layer,
        "vehicle": {
            "name": vehicle.get("vehicle_name", ""),
            "length_mm": float(vehicle.get("cargo_length_mm", 0.0)),
            "width_mm": float(vehicle.get("cargo_width_mm", 0.0)),
            "height_mm": float(vehicle.get("cargo_height_mm", 0.0)),
        },
    }


def build_fleet_visualizations(fleet_load_result: dict[str, object]) -> dict[str, dict[str, object]]:
    visualizations: dict[str, dict[str, object]] = {}
    for vehicle_result in fleet_load_result.get("vehicle_results", []):
        vehicle = vehicle_result["vehicle"]
        instance_id = str(vehicle.get("instance_id") or vehicle.get("vehicle_name", "vehicle"))
        visualizations[instance_id] = build_vehicle_visualization(
            vehicle,
            vehicle_result["load_result"].get("placements", []),
        )
    return visualizations
