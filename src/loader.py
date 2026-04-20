from __future__ import annotations

import math
from typing import List, Dict, Any, Iterable
from exceptions import LoadingFailedError
from utils.logger import dispatch_logger


MIX_CONFLICTS = {
    frozenset({"G1", "G4"}),
    frozenset({"G1", "G3"}),
}


def _deviation_ratio_percent(first_weight: float, second_weight: float, total_weight: float) -> float:
    if total_weight <= 0:
        return 0.0
    return abs(first_weight - second_weight) / total_weight * 100

FRICTION_MAP = {
    "석고보드": 0.4,
    "아이소핑크": 0.3,
    "단열재": 0.3
}


class PackingEngine:
    """V10.2.2 Refined Layer-based BFD Packing Engine."""

    def __init__(self, vehicle_w: float, vehicle_l: float, vehicle_h: float, forbidden_zones: list[tuple[float, float, float, float]] | None = None):
        self.vehicle_w = vehicle_w
        self.vehicle_l = vehicle_l
        self.vehicle_h = vehicle_h
        self.layers: list[dict[str, Any]] = []
        self.initial_forbidden = forbidden_zones or []

    def _can_mix(self, group1: str, current_groups: set[str]) -> bool:
        if not group1:
            return True
        for group2 in current_groups:
            if not group2:
                continue
            if frozenset({group1, group2}) in MIX_CONFLICTS:
                return False
        return True

    def pack(self, items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        # Step 1: Pre-Process (Sorting)
        # 하차그룹 규칙:
        #   - dg > 0: 숫자가 작을수록 전방(먼저 실음, 나중에 하차)
        #             숫자가 클수록 후방 입구(나중에 실음, 먼저 하차)
        #   - dg = 0: 순서 무관 → 제약 있는 자재 이후에 배치
        # BFD는 y=0(전방)부터 채우므로 먼저 정렬된 아이템이 전방에 배치됨
        # → dg ASC 정렬: 작은 번호 전방, 큰 번호 후방, dg=0 최후방

        def sort_key(x):
            dg = int(x.get("delivery_group", 0))
            dg_order = dg if dg > 0 else 10_000  # dg=0(순서 무관)은 제약 그룹 이후
            return (
                dg_order,
                not x.get("is_dead_space", False),
                x.get("priority", 3),
                -(float(x.get("width_mm", 0)) * float(x.get("length_mm", 0))),
            )

        sorted_items = sorted(items, key=sort_key)

        placements: list[dict[str, Any]] = []
        unplaced: list[dict[str, Any]] = []

        for item in sorted_items:
            placed = False
            item_w = float(item.get("width_mm", 0))
            item_l = float(item.get("length_mm", 0))
            item_h = float(item.get("height_mm", 0))

            # Mandatory 2-way orientation test
            orientations = [(item_w, item_l)]
            if item_w != item_l:
                orientations.append((item_l, item_w))

            for w, l in orientations:
                if w > self.vehicle_w or l > self.vehicle_l:
                    continue

                # Try existing layers
                for layer_idx, layer in enumerate(self.layers):
                    if not self._can_mix(item.get("mix_group", ""), layer["groups"]):
                        continue
                    
                    if layer["z"] + item_h > self.vehicle_h:
                        continue

                    # Try BFD in this layer
                    pos = self._find_first_fit(layer, w, l)
                    if pos:
                        x, y = pos
                        placements.append({
                            **item,
                            "x": x,
                            "y": y,
                            "z": layer["z"],
                            "placed_w": w,
                            "placed_l": l,
                            "layer_id": layer_idx,
                            "is_rotated": w != item_w
                        })
                        layer["groups"].add(item.get("mix_group", ""))
                        layer["max_h"] = max(layer["max_h"], item_h)
                        placed = True
                        break
                
                if placed:
                    break
            
            # Create new layer if not placed
            if not placed:
                current_z = sum(l["max_h"] for l in self.layers)
                if current_z + item_h <= self.vehicle_h:
                    # Pick best orientation for new layer (the one that fits)
                    best_w, best_l = orientations[0]
                    for w, l in orientations:
                        if w <= self.vehicle_w and l <= self.vehicle_l:
                            best_w, best_l = w, l
                            break

                    new_layer = {
                        "z": current_z,
                        "max_h": item_h,
                        "groups": {item.get("mix_group", "")},
                        "items": [],
                        "occupied_rects": list(self.initial_forbidden)
                    }
                    pos = self._find_first_fit(new_layer, best_w, best_l)
                    if pos:
                        x, y = pos
                        placements.append({
                            **item,
                            "x": x,
                            "y": y,
                            "z": current_z,
                            "placed_w": best_w,
                            "placed_l": best_l,
                            "layer_id": len(self.layers),
                            "is_rotated": best_w != item_w
                        })
                        self.layers.append(new_layer)
                        placed = True

            if not placed:
                unplaced.append(item)

        return placements, unplaced

    def _find_first_fit(self, layer: dict[str, Any], w: float, l: float) -> tuple[float, float] | None:
        possible_points = [(0, 0)]
        for (ex, ey, ew, el) in layer["occupied_rects"]:
            possible_points.append((ex + ew, ey))
            possible_points.append((ex, ey + el))

        possible_points.sort(key=lambda p: (p[1], p[0]))

        for x, y in possible_points:
            if x + w <= self.vehicle_w and y + l <= self.vehicle_l:
                overlap = False
                for (ex, ey, ew, el) in layer["occupied_rects"]:
                    if not (x + w <= ex or x >= ex + ew or y + l <= ey or y >= ey + el):
                        overlap = True
                        break
                if not overlap:
                    layer["occupied_rects"].append((x, y, w, l))
                    return x, y
        return None


def _make_stacks(order_items: Iterable[dict[str, Any]], material_db: dict[str, Any]) -> list[dict[str, Any]]:
    """V10.2.2: Pallet items -> aggregated Stacks based on stack_limit."""
    stacks: list[dict[str, Any]] = []
    
    for order in order_items:
        mat_key = order["material_key"]
        mat = material_db.get(mat_key, {})
        
        items_per_pallet = int(mat.get("팔레트당적재수", 1))
        stack_limit_raw = int(mat.get("stack_limit", 0))
        total_qty = order["quantity"]

        # 1. Total pallets needed
        num_pallets = math.ceil(total_qty / items_per_pallet)

        # 2. stack_limit=0 → 제한 없음: 1팔레트=1스택으로 분리 (BFD가 수직 배치 결정)
        #    stack_limit=N → N팔레트씩 묶어서 스택 생성
        stack_limit_pallets = stack_limit_raw if stack_limit_raw > 0 else 1

        # 3. Group pallets into stacks
        num_stacks = math.ceil(num_pallets / stack_limit_pallets)
        
        pallet_w = float(mat.get("width_mm", 1000.0))
        pallet_l = float(mat.get("length_mm", 1000.0))
        unit_thickness = float(mat.get("thickness_mm", 10.0))
        # Pallet unit height = unit_thickness * items_per_pallet
        pallet_unit_h = unit_thickness * items_per_pallet
        
        for i in range(num_stacks):
            pallets_in_this_stack = stack_limit_pallets if i < num_stacks - 1 else (num_pallets % stack_limit_pallets or stack_limit_pallets)
            
            stack_h = pallet_unit_h * pallets_in_this_stack
            # Weight is also per pallet * num_pallets
            pallet_weight = float(mat.get("팔레트무게(kg)", 0.0)) or (float(mat.get("낱장무게(kg)", 0.0)) * items_per_pallet)
            stack_weight = pallet_weight * pallets_in_this_stack
            stack_volume = (pallet_w * pallet_l * stack_h) / 1_000_000_000

            stacks.append({
                "material_key": mat_key,
                "width_mm": pallet_w,
                "length_mm": pallet_l,
                "height_mm": stack_h,
                "weight_kg": stack_weight,
                "volume_m3": stack_volume,
                "mix_group": mat.get("mix_group", ""),
                "handling_grade": mat.get("취급등급", ""),
                "priority": mat.get("priority", 3),
                "is_dead_space": mat.get("is_dead_space", False),
                "delivery_group": mat.get("delivery_group", 0),
                "num_pallets": pallets_in_this_stack,
                "stack_limit": stack_limit_raw,
                "unit_thickness_mm": unit_thickness,
                "sheets_per_pallet": items_per_pallet,
                "is_upper_layer": False,
            })
            
    return stacks


def _plan_loading_from_stacks(selected_vehicle: dict[str, Any], stacks: list[dict[str, Any]]) -> dict[str, Any]:
    truck_h = float(selected_vehicle["cargo_height_mm"])
    engine = PackingEngine(
        float(selected_vehicle["cargo_width_mm"]),
        float(selected_vehicle["cargo_length_mm"]),
        truck_h,
    )

    placements, unplaced = engine.pack(stacks)

    # ── 상층 자동 분할 (Upper Layer Auto-Split) ──────────────────
    # 미배치 스택이 있고 수직 여유가 있으면, 자재별 잔여 장수 전체를
    # 상층 높이에 맞는 팔레트로 재생성하여 배치
    upper_layer_split_applied = False
    if unplaced and placements:
        current_max_h = max(p["z"] + p["height_mm"] for p in placements)
        avail_top_h = truck_h - current_max_h

        if avail_top_h > 0:
            # 자재별로 미배치 팔레트 묶기
            unplaced_by_mat: dict[str, list[dict[str, Any]]] = {}
            other_unplaced: list[dict[str, Any]] = []

            for item in unplaced:
                unit_thick = float(item.get("unit_thickness_mm", 0))
                sheets_per = int(item.get("sheets_per_pallet", 0))
                if unit_thick > 0 and sheets_per > 0 and avail_top_h >= unit_thick:
                    unplaced_by_mat.setdefault(item["material_key"], []).append(item)
                else:
                    other_unplaced.append(item)

            split_items: list[dict[str, Any]] = []

            for mat_key, mat_items in unplaced_by_mat.items():
                unit_thick = float(mat_items[0].get("unit_thickness_mm", 0))
                sheets_per = int(mat_items[0].get("sheets_per_pallet", 0))
                top_sheets = min(math.floor(avail_top_h / unit_thick), sheets_per)

                if top_sheets <= 0:
                    other_unplaced.extend(mat_items)
                    continue

                # 미배치 팔레트 전체 장수 합산 → 올바른 수의 상층 팔레트 생성
                total_remaining_sheets = sum(
                    item.get("num_pallets", 1) * sheets_per for item in mat_items
                )
                n_upper_pallets = math.ceil(total_remaining_sheets / top_sheets)
                unit_pallet_wt = mat_items[0]["weight_kg"] / max(mat_items[0].get("num_pallets", 1), 1)
                sheets_left = total_remaining_sheets

                for _ in range(n_upper_pallets):
                    s = min(top_sheets, sheets_left)
                    split_items.append({
                        **mat_items[0],
                        "height_mm": unit_thick * s,
                        "weight_kg": unit_pallet_wt * (s / sheets_per),
                        "num_pallets": 1,
                        "is_upper_layer": True,
                    })
                    sheets_left -= s

            if split_items:
                new_placements, remaining = engine.pack(split_items)
                placements.extend(new_placements)
                unplaced = remaining + other_unplaced
                upper_layer_split_applied = bool(new_placements)
    # ─────────────────────────────────────────────────────────────

    truck_l = float(selected_vehicle["cargo_length_mm"])
    truck_w = float(selected_vehicle["cargo_width_mm"])
    
    # --- V10.2.3 Centering Logic ---
    y_offset = 0.0
    x_offset = 0.0
    if placements:
        max_y_used = max(p["y"] + p["placed_l"] for p in placements)
        y_offset = (truck_l - max_y_used) / 2
        
        max_x_used = max(p["x"] + p["placed_w"] for p in placements)
        x_offset = (truck_w - max_x_used) / 2
    # -------------------------------

    processed_placements = []
    for p in placements:
        # Apply Centering Offsets
        p["y"] += y_offset
        p["x"] += x_offset
        
        # Zones for risk evaluation
        longitudinal = "front" if (p["y"] + p["placed_l"]/2) < truck_l / 2 else "rear"
        lateral = "left" if (p["x"] + p["placed_w"]/2) < truck_w / 2 else "right"
        vertical = "bottom" if p["z"] == 0 else "top"
        
        # x_ratio along Length
        x_ratio = (p["y"] + p["placed_l"]/2) / truck_l

        processed_placements.append({
            **p,
            "longitudinal_zone": longitudinal,
            "lateral_zone": lateral,
            "vertical_zone": vertical,
            "x_ratio": x_ratio,
        })

    total_weight = sum(p["weight_kg"] for p in processed_placements)
    front_weight = sum(p["weight_kg"] for p in processed_placements if p["longitudinal_zone"] == "front")
    rear_weight = total_weight - front_weight
    left_weight = sum(p["weight_kg"] for p in processed_placements if p["lateral_zone"] == "left")
    right_weight = total_weight - left_weight
    top_weight = sum(p["weight_kg"] for p in processed_placements if p["vertical_zone"] == "top")

    front_rear_deviation_pct = _deviation_ratio_percent(front_weight, rear_weight, total_weight)
    left_right_deviation_pct = _deviation_ratio_percent(left_weight, right_weight, total_weight)
    top_share_pct = (top_weight / total_weight * 100) if total_weight > 0 else 0.0

    axle_count = max(int(selected_vehicle.get("axles", 1)), 1)
    
    # Use front/rear pos if provided, otherwise equal spacing
    f_pos = float(selected_vehicle.get("front_axle_pos_mm", 500.0))
    r_pos = float(selected_vehicle.get("rear_axle_pos_mm", truck_l - 500.0))
    
    if axle_count == 2:
        axle_positions = [f_pos, r_pos]
    else:
        # Interpolate for more axles
        axle_positions = [f_pos + (r_pos - f_pos) * (i / (axle_count - 1)) for i in range(axle_count)]
    
    axle_loads = [0.0 for _ in range(axle_count)]

    for p in processed_placements:
        pallet_y_abs = p["x_ratio"] * truck_l
        nearest_axle_index = min(range(axle_count), key=lambda idx: abs(axle_positions[idx] - pallet_y_abs))
        axle_loads[nearest_axle_index] += float(p["weight_kg"])

    axle_overload_critical = any(load > 10_000 for load in axle_loads)
    mix_groups = {str(p["mix_group"]) for p in processed_placements if p["mix_group"]}
    mix_group_violation = any(conflict.issubset(mix_groups) for conflict in MIX_CONFLICTS)
    # stack_limit > 0인 스택 중 num_pallets가 한도를 초과한 경우 감지
    stack_limit_exceeded = any(
        int(p.get("stack_limit", 0)) > 0 and int(p.get("num_pallets", 0)) > int(p.get("stack_limit", 0))
        for p in processed_placements
    )
    
    fragile_bottom_pressure = any(
        p["handling_grade"] == "A" and p["vertical_zone"] == "bottom" and top_weight > 0
        for p in processed_placements
    )

    max_weight_kg = float(selected_vehicle.get("max_weight_kg", 0.0))
    cargo_volume_m3 = float(selected_vehicle.get("cargo_volume_m3", 0.0))
    weight_ratio_pct = (total_weight / max_weight_kg * 100) if max_weight_kg > 0 else 0.0
    volume_ratio_pct = (sum(p["volume_m3"] for p in processed_placements) / cargo_volume_m3 * 100) if cargo_volume_m3 > 0 else 0.0

    total_weight_mm_y = sum(p["weight_kg"] * (p["y"] + p["placed_l"]/2) for p in processed_placements)
    total_weight_mm_x = sum(p["weight_kg"] * (p["x"] + p["placed_w"]/2) for p in processed_placements)
    
    cog_pct_y = (total_weight_mm_y / (total_weight * truck_l) * 100) if total_weight > 0 else 50.0
    cog_pct_x = (total_weight_mm_x / (total_weight * truck_w) * 100) if total_weight > 0 else 50.0
    
    # --- V10.2.6 Auto-Correction Pipeline ---
    original_cog_y = cog_pct_y
    correction_level = 0
    shift_mm_applied = 0.0
    
    def calculate_dynamic_risk(cog_y):
        fl_pct = 100 - cog_y
        return fl_pct + 12.0 # 12% Brake Shift
    
    # Initial Assessment
    dynamic_front_load_pct = calculate_dynamic_risk(cog_pct_y)
    
    if dynamic_front_load_pct > 60:
        # Stage 1: Global Rear Shift (Fix 1)
        target_cog_y = 52.0
        if cog_pct_y < target_cog_y:
            actual_center_y = total_weight_mm_y / total_weight if total_weight > 0 else 0
            required_shift = (target_cog_y / 100.0 * truck_l) - actual_center_y
            if not processed_placements:
                available_space = 0
            else:
                max_y_end = max(p["y"] + p["placed_l"] for p in processed_placements)
                available_space = truck_l - max_y_end
            
            final_shift = min(required_shift, available_space)
            if final_shift > 0:
                for p in processed_placements:
                    p["y"] += final_shift
                    p["longitudinal_zone"] = "front" if (p["y"] + p["placed_l"]/2) < truck_l / 2 else "rear"
                    p["x_ratio"] = (p["y"] + p["placed_l"]/2) / truck_l
                
                shift_mm_applied += final_shift
                correction_level = 1
                if total_weight > 0:
                    total_weight_mm_y = sum(p["weight_kg"] * (p["y"] + p["placed_l"]/2) for p in processed_placements)
                    cog_pct_y = (total_weight_mm_y / (total_weight * truck_l) * 100)
                dynamic_front_load_pct = calculate_dynamic_risk(cog_pct_y)

        # Stage 2: Heavy Rear Repacking (Fix 2) - Approximation
        if dynamic_front_load_pct > 60:
            # We sort heavy items in placements and move them as far back as possible within their zones
            sorted_placements = sorted(processed_placements, key=lambda p: p["weight_kg"], reverse=True)
            for p in sorted_placements:
                if p["longitudinal_zone"] == "front":
                    # Try to find a slot in current layer that is further back
                    # For V10.2.6 simple fix, we just swap positions of a heavy font item with a light rear item
                    light_rear_items = [lp for lp in processed_placements if lp["longitudinal_zone"] == "rear" and lp["weight_kg"] < p["weight_kg"]]
                    if light_rear_items:
                        target = min(light_rear_items, key=lambda x: x["weight_kg"])
                        # Swap Y positions
                        p["y"], target["y"] = target["y"], p["y"]
                        p["longitudinal_zone"], target["longitudinal_zone"] = target["longitudinal_zone"], p["longitudinal_zone"]
                        correction_level = 2
                        break
            
            # Recalculate after Fix 2
            if total_weight > 0:
                total_weight_mm_y = sum(p["weight_kg"] * (p["y"] + p["placed_l"]/2) for p in processed_placements)
                cog_pct_y = (total_weight_mm_y / (total_weight * truck_l) * 100)
            dynamic_front_load_pct = calculate_dynamic_risk(cog_pct_y)

        # Stage 3: Layer Priority Swap (Fix 3)
        if dynamic_front_load_pct > 60:
            if len(engine.layers) > 1:
                # Group placements by layer
                layers_data = []
                for i in range(len(engine.layers)):
                    layer_p = [p for p in processed_placements if p["layer_id"] == i]
                    if layer_p:
                        avg_y = sum(p["y"] for p in layer_p) / len(layer_p)
                        layers_data.append({"id": i, "items": layer_p, "avg_y": avg_y})
                
                if len(layers_data) > 1:
                    # Sort layers by average Y (front layers first)
                    layers_data.sort(key=lambda x: x["avg_y"])
                    # If the front layer is heavier than the rear one, swap their Y blocks
                    front_total_w = sum(p["weight_kg"] for p in layers_data[0]["items"])
                    rear_total_w = sum(p["weight_kg"] for p in layers_data[-1]["items"])
                    if front_total_w > rear_total_w:
                        # Swap all Y coordinates between these two layers
                        # Note: This is an approximation assuming they have similar footprints
                        # For now, we'll just flag it and perform a logical shift
                        for p_f, p_r in zip(layers_data[0]["items"], layers_data[-1]["items"]):
                            p_f["y"], p_r["y"] = p_r["y"], p_f["y"]
                        correction_level = 3
            
            # Recalculate after Fix 3
            if total_weight > 0:
                total_weight_mm_y = sum(p["weight_kg"] * (p["y"] + p["placed_l"]/2) for p in processed_placements)
                cog_pct_y = (total_weight_mm_y / (total_weight * truck_l) * 100)
            dynamic_front_load_pct = calculate_dynamic_risk(cog_pct_y)

    risk_resolved = dynamic_front_load_pct <= 60
    # V10.2.6 Update: Only Safe/Caution allowed for dispatch
    dispatch_allowed = dynamic_front_load_pct <= 60
    
    # Correction Stage Mapping
    correction_stage = "None"
    if correction_level == 1: correction_stage = "Fix1"
    elif correction_level == 2: correction_stage = "Fix2"
    elif correction_level == 3: correction_stage = "Fix3"
    
    # Final Metrics Update
    front_weight = sum(p["weight_kg"] for p in processed_placements if p["longitudinal_zone"] == "front")
    rear_weight = total_weight - front_weight
    front_rear_deviation_pct = _deviation_ratio_percent(front_weight, rear_weight, total_weight)
    
    # Re-calculate score and risk after potential correction
    balance_score = max(0, 100 - (front_rear_deviation_pct + left_right_deviation_pct))

    # --- V10.2.4 Dynamic Stability Logic ---
    # Heuristic: min friction among items
    mat_names = {p["material_key"].split()[0] for p in processed_placements}
    min_mu = 0.4
    for name in mat_names:
        for k, v in FRICTION_MAP.items():
            if k in name:
                min_mu = min(min_mu, v)
    
    # Simple approx shift ratio (12% of length)
    expected_shift_pct = 12.0 # Fixed ratio as per user request
    expected_shift_mm = truck_l * (expected_shift_pct / 100.0)
    
    # Map to User's COG system: Rear = 0, Front = 100
    front_load_pct = 100 - cog_pct_y
    dynamic_front_load_pct = front_load_pct + expected_shift_pct
    
    braking_risk_level = "Safe"
    if dynamic_front_load_pct > 65: braking_risk_level = "Critical"
    elif dynamic_front_load_pct > 60: braking_risk_level = "Danger"
    elif dynamic_front_load_pct > 55: braking_risk_level = "Caution"
    # --------------------------------------

    return {
        "selected_vehicle": selected_vehicle,
        "placements": processed_placements,
        "unplaced": unplaced,
        "total_weight_kg": total_weight,
        "front_rear_deviation_pct": front_rear_deviation_pct,
        "left_right_deviation_pct": left_right_deviation_pct,
        "cog_pct_y": cog_pct_y,
        "cog_pct_x": cog_pct_x,
        "front_load_pct": front_load_pct,
        "original_cog_y": original_cog_y,
        "dynamic_cog_pct": dynamic_front_load_pct,
        "expected_shift_mm": expected_shift_mm,
        "shift_mm_applied": shift_mm_applied,
        "correction_stage": correction_stage,
        "correction_level": correction_level,
        "risk_resolved": "Y" if risk_resolved else "N",
        "dispatch_allowed": dispatch_allowed,
        "braking_risk_level": braking_risk_level,
        "balance_score": balance_score,
        "front_rear_ratio": f"{front_weight/1000:.1f}t : {rear_weight/1000:.1f}t",
        "top_share_pct": top_share_pct,
        "weight_ratio_pct": weight_ratio_pct,
        "volume_ratio_pct": volume_ratio_pct,
        "front_rear_critical": front_rear_deviation_pct >= 25.0, # Tightened from 35.0
        "axle_loads_kg": axle_loads,
        "axle_overload_critical": axle_overload_critical,
        "mix_group_violation": mix_group_violation,
        "fragile_bottom_pressure": fragile_bottom_pressure,
        "stack_limit_exceeded": stack_limit_exceeded,
        "upper_layer_split_applied": upper_layer_split_applied,
        "layer_count": len(engine.layers)
    }
    
    # Log successful loading
    dispatch_logger.log_attempt(
        input_items={"stacks_count": len(stacks), "vehicle": selected_vehicle["vehicle_name"]},
        selection_result={"status": "LoadingPlanned"},
        loading_result=final_result
    )
    
    return final_result


def plan_loading(selected_vehicle: dict[str, Any], order_items: Iterable[dict[str, Any]]) -> dict[str, Any]:
    from data_manager import data_manager
    material_db = data_manager.get_material_db()
    stacks = _make_stacks(order_items, material_db)
    if not stacks:
        raise LoadingFailedError("CRITICAL: Failed to create stacks from order items. Ensure material keys and quantities are valid.")
    return _plan_loading_from_stacks(selected_vehicle, stacks)


def plan_fleet_loading(selection_result: dict[str, Any]) -> dict[str, Any]:
    from data_manager import data_manager
    material_db = data_manager.get_material_db()
    
    vehicle_results: list[dict[str, Any]] = []
    total_weight_kg = 0.0
    
    for allocation in selection_result.get("vehicle_allocations", []):
        vehicle = dict(allocation["vehicle"])
        # In V10.2.2, we assume selection results contain order items per vehicle for stack logic
        # For compatibility with assigned_pallets, we convert those back
        pallets = list(allocation.get("assigned_pallets", []))
        
        # Group by material_key to reconstruct "orders" for that vehicle
        per_mat_qty = {}
        for p in pallets:
            # We need to know how many items were in each pallet
            # Since selection logic works on items, it's better to pass items
            # But the current selection result gives us pallets
            # I'll rely on material_db and stack_qty if provided
            key = p["material_key"]
            mat = material_db.get(key, {})
            qty_in_pallet = int(mat.get("팔레트당적재수", 1))
            per_mat_qty[key] = per_mat_qty.get(key, 0) + qty_in_pallet
            
        assigned_orders = [{"material_key": k, "quantity": v} for k, v in per_mat_qty.items()]
        stacks = _make_stacks(assigned_orders, material_db)
        load_result = _plan_loading_from_stacks(vehicle, stacks)
        
        vehicle_results.append({
            "vehicle": vehicle,
            "assigned_pallets": pallets,
            "load_result": load_result,
        })
        total_weight_kg += float(load_result["total_weight_kg"])

    return {
        "vehicle_results": vehicle_results,
        "vehicle_counts": dict(selection_result.get("vehicle_counts", {})),
        "total_weight_kg": total_weight_kg,
        "total_freight_krw": int(selection_result.get("total_freight_krw", 0)),
    }
