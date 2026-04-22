from __future__ import annotations

from pathlib import Path

from bin_packing import filter_feasible_vehicles, load_vehicle_db
from input_parser import load_material_db, process_orders
from loader import plan_loading
from report_generator import generate_report
from risk_evaluator import evaluate_risk
from vehicle_selector import select_optimal_vehicle


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"


def collect_orders() -> list[dict[str, object]]:
    orders: list[dict[str, object]] = []

    while True:
        material_key = input("자재 key 입력 (빈 줄 종료): ").strip()
        if not material_key:
            break

        quantity = int(input("수량 입력: ").strip())
        orders.append(
            {
                "material_key": material_key,
                "quantity": quantity,
            }
        )

    return orders


def run_pipeline(orders: list[dict[str, object]]) -> dict[str, object]:
    material_db = load_material_db(DATA_DIR / "자재정보.csv")
    vehicle_db = load_vehicle_db(DATA_DIR / "차량정보.csv")

    order_result = process_orders(material_db, orders)
    feasible_vehicles = filter_feasible_vehicles(order_result["items"], vehicle_db)
    if not feasible_vehicles:
        raise ValueError("적재 불가 - 분할 배차 필요")

    selection_result = select_optimal_vehicle(feasible_vehicles)
    load_result = plan_loading(selection_result["selected_vehicle"], order_result["items"])
    risk_result = evaluate_risk(load_result)
    report_paths = generate_report(
        order_result,
        selection_result,
        load_result,
        risk_result,
        OUTPUT_DIR,
    )

    return {
        "order_result": order_result,
        "selection_result": selection_result,
        "load_result": load_result,
        "risk_result": risk_result,
        "report_paths": report_paths,
    }


def main() -> int:
    orders = collect_orders()
    if not orders:
        print("입력된 주문이 없습니다.")
        return 0

    try:
        result = run_pipeline(orders)
    except ValueError as exc:
        print(str(exc))
        return 1

    risk_result = result["risk_result"]
    report_paths = result["report_paths"]

    print("[결과 출력]")
    print(f"위험도: {risk_result['final_level']}")
    print(f"현장매뉴얼: {risk_result['manual']}")
    print(f"저장완료: {report_paths['json_path']}")
    print(f"저장완료: {report_paths['instruction_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
