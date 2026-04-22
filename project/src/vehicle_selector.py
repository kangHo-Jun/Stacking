from __future__ import annotations

import math
from typing import Iterable

from ortools.linear_solver import pywraplp


def _build_pallets(order_items: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    pallets: list[dict[str, object]] = []
    for item in order_items:
        if "quantity" not in item or "pallet_capacity" not in item:
            pallet_count = max(int(item.get("pallet_count", 1)), 1)
            pallet_weight = float(item["total_weight_kg"]) / pallet_count
            pallet_volume = float(item.get("total_volume_m3", 0.0)) / pallet_count
            for pallet_index in range(pallet_count):
                pallets.append(
                    {
                        "material_key": item.get("material_key", ""),
                        "handling_grade": item.get("handling_grade", ""),
                        "preferred_position": item.get("preferred_position", "하단"),
                        "weight_kg": pallet_weight,
                        "volume_m3": pallet_volume,
                        "qty": 1,
                        "unit_type": "pallet",
                        "material_name": item.get("material_name", item.get("material_key", "")),
                        "sequence": pallet_index,
                    }
                )
            continue

        pallet_capacity = max(int(item.get("pallet_capacity", 1)), 1)
        quantity = max(int(item.get("quantity", 0)), 0)
        unit_weight = float(item["total_weight_kg"]) / max(quantity, 1)
        unit_volume = float(item.get("total_volume_m3", 0.0)) / max(quantity, 1)
        full_pallets = quantity // pallet_capacity
        remainder = quantity % pallet_capacity

        for pallet_index in range(full_pallets):
            pallets.append(
                {
                    "material_key": item.get("material_key", ""),
                        "handling_grade": item.get("handling_grade", ""),
                        "preferred_position": item.get("preferred_position", "하단"),
                    "weight_kg": unit_weight * pallet_capacity,
                    "volume_m3": unit_volume * pallet_capacity,
                    "qty": pallet_capacity,
                    "unit_type": "pallet",
                    "material_name": item.get("material_name", item.get("material_key", "")),
                    "sequence": pallet_index,
                }
            )
        if remainder:
            pallets.append(
                {
                    "material_key": item.get("material_key", ""),
                    "handling_grade": item.get("handling_grade", ""),
                    "preferred_position": item.get("preferred_position", "하단"),
                    "weight_kg": unit_weight * remainder,
                    "volume_m3": unit_volume * remainder,
                    "qty": remainder,
                    "unit_type": "sheet",
                    "material_name": item.get("material_name", item.get("material_key", "")),
                    "sequence": full_pallets,
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
        candidate = min(
            allocations,
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
    solver.Minimize(
        sum(
            decisions[index] * int(vehicle["freight_cost_krw"])
            for index, vehicle in enumerate(candidates)
        )
    )

    status = solver.Solve()
    if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        raise ValueError("No feasible optimization solution found.")

    selected_index = next(
        index for index, decision in enumerate(decisions) if decision.solution_value() > 0.5
    )
    selected_vehicle = candidates[selected_index]
    total_freight_cost = int(selected_vehicle["freight_cost_krw"])

    return {
        "selected_vehicle": selected_vehicle,
        "total_freight_krw": total_freight_cost,
        "vehicle_counts": {selected_vehicle["vehicle_name"]: 1},
        "selected_vehicles": [{"vehicle": selected_vehicle, "count": 1}],
        "vehicle_allocations": [{"vehicle": selected_vehicle, "assigned_pallets": []}],
        "selection_reason": (
            f"{selected_vehicle['vehicle_name']} is selected because it satisfies feasibility "
            f"constraints with the lowest freight cost of {total_freight_cost} KRW."
        ),
    }


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
    solver.Minimize(
        sum(
            counts[index] * int(vehicle["freight_cost_krw"])
            for index, vehicle in enumerate(candidates)
        )
    )

    status = solver.Solve()
    if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        raise ValueError("No feasible optimization solution found.")

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
        "selection_reason": (
            f"Selected the lowest-cost vehicle combination covering {total_weight_kg:.1f}kg."
        ),
    }


def select_optimal_vehicle(
    vehicles: Iterable[dict[str, object]],
    order_items: Iterable[dict[str, object]] | None = None,
) -> dict[str, object]:
    if order_items is None:
        return _select_single_vehicle(vehicles)
    return _select_multi_vehicle(vehicles, order_items)
