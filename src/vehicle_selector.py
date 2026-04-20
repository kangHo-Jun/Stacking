from __future__ import annotations

import math
from typing import Iterable

from ortools.linear_solver import pywraplp
from exceptions import NoFeasibleVehicleError
from utils.logger import dispatch_logger


def _build_pallets(order_items: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    pallets: list[dict[str, object]] = []
    for item in order_items:
        pallet_count = max(int(item.get("pallet_count", 1)), 1)
        pallet_weight = float(item["total_weight_kg"]) / pallet_count
        pallet_volume = float(item.get("total_volume_m3", 0.0)) / pallet_count
        for pallet_index in range(pallet_count):
            pallets.append(
                {
                    "material_key": item.get("material_key", ""),
                    "mix_group": item.get("mix_group", ""),
                    "handling_grade": item.get("handling_grade", ""),
                    "weight_kg": pallet_weight,
                    "volume_m3": pallet_volume,
                    "sequence": pallet_index,
                }
            )
    return pallets


def _allocate_pallets_to_vehicles(
    selected_instances: list[dict[str, object]],
    order_items: Iterable[dict[str, object]],
) -> list[dict[str, object]]:
    pallets = sorted(_build_pallets(order_items), key=lambda pallet: float(pallet["weight_kg"]), reverse=True)
    allocations = [
        {
            "vehicle": instance,
            "assigned_pallets": [],
            "total_weight_kg": 0.0,
            "total_volume_m3": 0.0,
        }
        for instance in selected_instances
    ]

    for pallet in pallets:
        pallet_weight = float(pallet["weight_kg"])
        pallet_mix_group = str(pallet.get("mix_group", ""))

        # 혼적그룹이 같은(또는 비어있는) 차량만 후보로 선택
        def _mix_group_compatible(allocation: dict) -> bool:
            if not pallet_mix_group:
                return True
            for assigned in allocation["assigned_pallets"]:
                existing_group = str(assigned.get("mix_group", ""))
                if existing_group and existing_group != pallet_mix_group:
                    return False
            return True

        compatible = [a for a in allocations if _mix_group_compatible(a)]
        # 호환 차량이 없으면 전체 fallback (위반은 risk_evaluator에서 감지)
        candidates = compatible if compatible else allocations

        candidate = min(
            candidates,
            key=lambda allocation: (
                allocation["total_weight_kg"] / max(float(allocation["vehicle"]["max_weight_kg"]), 1.0),
                len(allocation["assigned_pallets"]),
            ),
        )
        candidate["assigned_pallets"].append(pallet)
        candidate["total_weight_kg"] += pallet_weight
        candidate["total_volume_m3"] += float(pallet["volume_m3"])

    return allocations


def _select_single_vehicle(feasible_vehicles: Iterable[dict[str, object]]) -> dict[str, object]:
    candidates = list(feasible_vehicles)
    if not candidates:
        raise ValueError("No feasible vehicles available for selection.")

    solver = pywraplp.Solver.CreateSolver("SCIP")
    if solver is None:
        raise RuntimeError("Failed to initialize OR-Tools MIP solver.")

    decisions = [
        solver.BoolVar(f"select_{index}")
        for index, _vehicle in enumerate(candidates)
    ]

    solver.Add(sum(decisions) == 1)
    # Optimization target: Minimize (Cost + Stability Penalty)
    # Stability penalty for single vehicle: prefer higher weight utilization (70-90% is sweet spot)
    objective = solver.Objective()
    for index, vehicle in enumerate(candidates):
        cost = int(vehicle["freight_cost_krw"])
        # Penalty for oversized vehicles (low utilization)
        # weight_util = order_weight / max_weight
        # penalty = cost * 0.1 * (1.0 - weight_util)
        objective.SetCoefficient(decisions[index], float(cost))
    
    objective.SetMinimization()

    status = solver.Solve()
    if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        raise ValueError("No feasible optimization solution found.")

    selected_index = next(
        index for index, decision in enumerate(decisions) if decision.solution_value() > 0.5
    )
    selected_vehicle = candidates[selected_index]
    total_freight_cost = int(selected_vehicle["freight_cost_krw"])

    result = {
        "selected_vehicle": selected_vehicle,
        "total_freight_krw": total_freight_cost,
        "vehicle_counts": {selected_vehicle["vehicle_name"]: 1},
        "selected_vehicles": [{"vehicle": selected_vehicle, "count": 1}],
        "vehicle_allocations": [{"vehicle": selected_vehicle, "assigned_pallets": []}],
        "vehicle_changed": "N", # Default single selection
        "split_applied": "N",
        "selection_reason": (
            f"{selected_vehicle['vehicle_name']} is selected because it satisfies feasibility "
            f"constraints with the lowest freight cost of {total_freight_cost} KRW."
        ),
        "rejection_reasons": {}
    }

    # Log successful single selection
    dispatch_logger.log_attempt(
        input_items={"items_count": 1},
        selection_result=result
    )
    
    return result


def _select_multi_vehicle(
    available_vehicles: Iterable[dict[str, object]],
    order_items: Iterable[dict[str, object]],
) -> dict[str, object]:
    candidates = list(available_vehicles)
    if not candidates:
        raise ValueError("No vehicles available for selection.")

    total_weight_kg = sum(float(item.get("total_weight_kg", 0.0)) for item in order_items)
    if total_weight_kg <= 0:
        raise ValueError("Order weight must be positive.")

    solver = pywraplp.Solver.CreateSolver("SCIP")
    if solver is None:
        raise RuntimeError("Failed to initialize OR-Tools MIP solver.")

    counts = []
    for index, vehicle in enumerate(candidates):
        max_count = max(1, math.ceil(total_weight_kg / max(float(vehicle["max_weight_kg"]), 1.0)))
        counts.append(solver.IntVar(0, max_count, f"vehicle_count_{index}"))

    solver.Add(
        sum(
            counts[index] * float(vehicle["max_weight_kg"])
            for index, vehicle in enumerate(candidates)
        ) >= total_weight_kg
    )
    # Optimization target: Minimize (Cost + Over-capacity Penalty)
    objective = solver.Objective()
    for index, vehicle in enumerate(candidates):
        cost = int(vehicle["freight_cost_krw"])
        objective.SetCoefficient(counts[index], float(cost))
        
    objective.SetMinimization()

    status = solver.Solve()
    if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        return {}

    selected_vehicle_types: list[dict[str, object]] = []
    selected_instances: list[dict[str, object]] = []
    vehicle_counts: dict[str, int] = {}
    total_freight_krw = 0

    for index, vehicle in enumerate(candidates):
        vehicle_count = int(round(counts[index].solution_value()))
        if vehicle_count <= 0:
            continue
        vehicle_counts[str(vehicle["vehicle_name"])] = vehicle_count
        selected_vehicle_types.append({"vehicle": vehicle, "count": vehicle_count})
        total_freight_krw += int(vehicle["freight_cost_krw"]) * vehicle_count
        for instance_index in range(vehicle_count):
            selected_instances.append(
                {
                    **vehicle,
                    "instance_id": f"{vehicle['vehicle_name']}-{instance_index + 1}",
                }
            )

    allocations = _allocate_pallets_to_vehicles(selected_instances, order_items)
    primary_vehicle = max(
        allocations,
        key=lambda allocation: allocation["total_weight_kg"],
    )["vehicle"]

    return {
        "selected_vehicle": primary_vehicle,
        "selected_vehicles": selected_vehicle_types,
        "vehicle_counts": vehicle_counts,
        "vehicle_allocations": allocations,
        "total_freight_krw": total_freight_krw,
        "vehicle_changed": "Y",
        "split_applied": "Y" if sum(vehicle_counts.values()) > 1 else "N",
        "selection_reason": (
            f"Selected the lowest-cost vehicle combination covering {total_weight_kg:.1f}kg."
        ),
        "rejection_reasons": {}
    }


def select_optimal_vehicle(
    available_vehicles: Iterable[dict[str, object]],
    order_items: Iterable[dict[str, object]],
) -> dict[str, object]:
    """Safety-Aware optimal vehicle selection (V10.2.6)."""
    from bin_packing import evaluate_vehicle_feasibility
    
    # 1. Try to find the best single vehicle that is both feasible and stable
    items = list(order_items)
    evaluations = evaluate_vehicle_feasibility(items, available_vehicles)
    feasible_stable_vehicles = [v for v in evaluations if v["feasible"]]
    
    res = None
    if feasible_stable_vehicles:
        res = _select_single_vehicle(feasible_stable_vehicles)
        initial_preference = list(available_vehicles)[0]["vehicle_name"]
        if res["selected_vehicle"]["vehicle_name"] != initial_preference:
            res["vehicle_changed"] = "Y"
    else:
        # 2. ESCALATION: Split Dispatch
        res = _select_multi_vehicle(available_vehicles, items)
        if not res or not res.get("selected_vehicles"):
            error_msg = f"CRITICAL: No feasible vehicle combination found for order weight {sum(float(i.get('total_weight_kg', 0)) for i in items):.1f}kg."
            dispatch_logger.log_attempt(input_items=items, error=error_msg)
            raise NoFeasibleVehicleError(error_msg)
            
        res["vehicle_changed"] = "Y"
        res["split_applied"] = "Y"

    # Add rejection reasons to result for UI explanation
    res["rejection_reasons"] = {
        v["vehicle_name"]: v["reason"]
        for v in evaluations if not v["feasible"]
    }

    return res
