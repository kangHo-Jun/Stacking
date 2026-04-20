from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, Response, flash, redirect, render_template, request, url_for

from data_manager import data_manager
from loader import plan_fleet_loading, plan_loading
from report_generator import generate_fleet_report, generate_report
from risk_evaluator import evaluate_fleet_risk, evaluate_risk
from vehicle_selector import select_optimal_vehicle


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
TEMPLATES_DIR = PROJECT_ROOT / "src" / "templates"
DB_PATH = DATA_DIR / "history.db"
HOMEBREW_LIB = "/opt/homebrew/lib"
CACHE_DIR = PROJECT_ROOT / ".cache"

existing_fallback = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
if HOMEBREW_LIB not in existing_fallback.split(":"):
    os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = (
        f"{HOMEBREW_LIB}:{existing_fallback}" if existing_fallback else HOMEBREW_LIB
    )
CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("XDG_CACHE_HOME", str(CACHE_DIR))

app = Flask(__name__, template_folder=str(TEMPLATES_DIR))
app.secret_key = "stacking-demo-secret"


def get_db_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_history_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                vehicle_name TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                total_weight REAL NOT NULL,
                freight_cost INTEGER NOT NULL,
                result_json TEXT NOT NULL
            )
            """
        )
        connection.commit()


def get_material_options() -> list[str]:
    material_db = data_manager.get_material_db()
    return sorted(material_db.keys())


def run_pipeline(orders: list[dict[str, object]]) -> dict[str, object]:
    from input_parser import process_orders
    material_db = data_manager.get_material_db()
    vehicle_db = data_manager.get_vehicle_db()

    order_result = process_orders(material_db, orders)
    selection_result = select_optimal_vehicle(vehicle_db, order_result["items"])
    if not selection_result.get("vehicle_allocations"):
        raise ValueError("적재 불가 - 분할 배차 필요")

    fleet_load_result = plan_fleet_loading(selection_result)
    fleet_risk_result = evaluate_fleet_risk(fleet_load_result)
    report_paths = generate_fleet_report(
        order_result,
        selection_result,
        fleet_load_result,
        fleet_risk_result,
        OUTPUT_DIR,
    )

    return {
        "order_result": order_result,
        "selection_result": selection_result,
        "load_result": fleet_load_result,
        "risk_result": fleet_risk_result,
        "report_paths": report_paths,
    }


def save_history(run_result: dict[str, object]) -> int:
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with run_result["report_paths"]["json_path"].open("r", encoding="utf-8") as handle:
        payload_text = handle.read()
    payload = json.loads(payload_text)

    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO history (created_at, vehicle_name, risk_level, total_weight, freight_cost, result_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                payload["차량"],
                payload["위험도"],
                payload["총중량"],
                payload["총운임"],
                payload_text,
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def risk_color(level: str) -> str:
    return {
        "Safe": "#1f9d55",
        "Caution": "#d9a404",
        "Danger": "#d96b00",
        "Critical": "#d64545",
    }.get(level, "#4a5568")


def render_pdf_bytes(html: str) -> bytes:
    from weasyprint import HTML

    return HTML(string=html, base_url=str(PROJECT_ROOT)).write_pdf()


@app.context_processor
def inject_helpers() -> dict[str, object]:
    return {"risk_color": risk_color}


@app.get("/")
def index() -> str:
    init_history_db()
    return render_template("index.html", material_options=get_material_options())


@app.post("/run")
def run() -> str:
    init_history_db()
    material_keys = request.form.getlist("material_key")
    quantities = request.form.getlist("quantity")
    orders: list[dict[str, object]] = []

    for material_key, quantity in zip(material_keys, quantities):
        material_key = material_key.strip()
        quantity_text = quantity.strip()
        if not material_key and not quantity_text:
            continue
        quantity_value = int(quantity_text or 0)
        if quantity_value <= 0:
            return "수량을 입력해주세요", 400
        orders.append({"material_key": material_key, "quantity": quantity_value})

    if not orders:
        flash("주문 항목을 1개 이상 입력하십시오.")
        return redirect(url_for("index"))

    try:
        run_result = run_pipeline(orders)
    except ValueError as exc:
        flash(str(exc))
        return redirect(url_for("index"))

    history_id = save_history(run_result)
    payload = json.loads(run_result["report_paths"]["json_path"].read_text(encoding="utf-8"))

    return render_template(
        "result.html",
        payload=payload,
        history_id=history_id,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        placements=[],
        vehicle_sections=payload.get("차량별결과", []),
    )


@app.get("/history")
def history() -> str:
    init_history_db()
    selected_id = request.args.get("id", type=int)

    with get_db_connection() as connection:
        rows = connection.execute(
            "SELECT id, created_at, vehicle_name, risk_level, total_weight, freight_cost, result_json FROM history ORDER BY id DESC"
        ).fetchall()

    selected_payload = None
    if selected_id is not None:
        for row in rows:
            if row["id"] == selected_id:
                selected_payload = json.loads(row["result_json"])
                break
    elif rows:
        selected_payload = json.loads(rows[0]["result_json"])
        selected_id = int(rows[0]["id"])

    return render_template(
        "history.html",
        rows=rows,
        selected_id=selected_id,
        selected_payload=selected_payload,
        selected_payload_text=(
            json.dumps(selected_payload, ensure_ascii=False, indent=2)
            if selected_payload is not None
            else None
        ),
    )


@app.get("/pdf/<int:history_id>")
def download_pdf(history_id: int) -> Response:
    init_history_db()
    with get_db_connection() as connection:
        row = connection.execute(
            "SELECT created_at, result_json FROM history WHERE id = ?",
            (history_id,),
        ).fetchone()

    if row is None:
        return Response("Not Found", status=404)

    payload = json.loads(row["result_json"])
    html = render_template(
        "result.html",
        payload=payload,
        history_id=history_id,
        created_at=row["created_at"],
        placements=[],
        vehicle_sections=payload.get("차량별결과", []),
        pdf_mode=True,
    )
    pdf_bytes = render_pdf_bytes(html)

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=result_{history_id}.pdf"},
    )


if __name__ == "__main__":
    init_history_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT") or 5000))
