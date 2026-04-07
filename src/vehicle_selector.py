from __future__ import annotations

from typing import Iterable

from ortools.linear_solver import pywraplp


def select_optimal_vehicle(feasible_vehicles: Iterable[dict[str, object]]) -> dict[str, object]:
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
        "selection_reason": (
            f"{selected_vehicle['vehicle_name']} is selected because it satisfies feasibility "
            f"constraints with the lowest freight cost of {total_freight_cost} KRW."
        ),
    }
