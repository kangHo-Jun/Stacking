import sys
import os
from pathlib import Path
import json
import traceback
import math

# Add src to path
PROJECT_ROOT = Path("/Users/zart/Library/Mobile Documents/com~apple~CloudDocs/프로젝트/적재시스템")
sys.path.append(str(PROJECT_ROOT / "src"))

from data_manager import data_manager
from vehicle_selector import select_optimal_vehicle
from loader import plan_fleet_loading, MIX_CONFLICTS
from bin_packing import load_vehicle_db

# Mock more conflicts for testing
MIX_CONFLICTS.add(frozenset({"A", "B"})) # GYP and Isopink conflict

def run_scenario(name, order_items):
    print(f"\n>>> Scenario: {name}")
    try:
        # 1. Fetch Data
        material_db = data_manager.get_material_db()
        vehicles = load_vehicle_db(PROJECT_ROOT / "data" / "차량정보.csv")
        
        # 2. Prepare order with metadata from DB
        processed_items = []
        for item in order_items:
            key = item["material_key"]
            if key not in material_db:
                print(f"Error: Material {key} not found")
                continue
            mat = material_db[key]
            processed_items.append({
                **item,
                "total_weight_kg": float(mat.get("낱장무게(kg)", 0)) * item["quantity"],
                "total_volume_m3": float(mat.get("낱장부피(m3)", 0)) * item["quantity"],
                "pallet_count": math.ceil(item["quantity"] / int(mat.get("팔레트당적재수", 1))),
                "mix_group": mat.get("mix_group", ""),
                "handling_grade": mat.get("취급등급", "")
            })
            
        # 3. Selection
        selection = select_optimal_vehicle(vehicles, processed_items)
        
        # 4. Loading Plan
        fleet_plan = plan_fleet_loading(selection)
        
        return {
            "name": name,
            "selection": selection,
            "fleet_plan": fleet_plan
        }
    except Exception as e:
        print(f"FAILED Scenario {name}: {e}")
        traceback.print_exc()
        return None

def main():
    import math # Required for processed_items calculation
    
    scenarios = [
        ("S1: Mass GYP 1800 (4000 qty)", [
            {"material_key": "석고보드 일반9.5T 900*1800_900x1800_9.5", "quantity": 4000}
        ]),
        ("S2: Rotation - Long GYP 2400 (2000 qty)", [
            {"material_key": "석고보드 일반9.5T 900*2400_900x2400_9.5", "quantity": 2000}
        ]),
        ("S3: Mix - Multi-Size GYP", [
            {"material_key": "석고보드 일반9.5T 900*1800_900x1800_9.5", "quantity": 1200},
            {"material_key": "석고보드 일반9.5T 900*2400_900x2400_9.5", "quantity": 1200}
        ]),
        ("S4: Conflict - Group A vs B", [
            {"material_key": "석고보드 일반9.5T 900*1800_900x1800_9.5", "quantity": 600}, # Group A
            {"material_key": "아이소핑크 100T 900*1800_900x1800_100", "quantity": 20} # Group B
        ]),
        ("S5: Geometry - Extra Long Item", [
            {"material_key": "석고보드 방균9.5T 900*2650_900x2650_9.5", "quantity": 1200}
        ]),
        ("S6: Priority - Urgency", [
            {"material_key": "석고보드 일반9.5T 900*1800_900x1800_9.5", "quantity": 1200}, # Prio from DB
        ]),
        ("S7: Dead Space - Filler", [
             {"material_key": "석고보드 일반9.5T 900*2400_900x2400_9.5", "quantity": 1200}
        ]),
        ("S8: Drop-off - Multi-Drop", [
            {"material_key": "석고보드 일반9.5T 900*1800_900x1800_9.5", "quantity": 240, "delivery_group": 1},
            {"material_key": "석고보드 일반12.5T 900*1800_900x1800_12.5", "quantity": 180, "delivery_group": 2},
            {"material_key": "석고보드 방화12.5T 900*1800_900x1800_12.5", "quantity": 90, "delivery_group": 3}
        ]),
        ("S9: Overweight - Massive Split", [
             {"material_key": "석고보드 일반9.5T 900*1800_900x1800_9.5", "quantity": 10000}
        ]),
        ("S10: Complex Mix", [
            {"material_key": "석고보드 일반9.5T 900*2400_900x2400_9.5", "quantity": 600, "delivery_group": 1},
            {"material_key": "아이소핑크 100T 900*1800_900x1800_100", "quantity": 40, "delivery_group": 2},
            {"material_key": "석고보드 방균9.5T 900*2650_900x2650_9.5", "quantity": 360, "priority": 1}
        ])
    ]
    
    all_results = []
    for name, items in scenarios:
        res = run_scenario(name, items)
        if res:
            all_results.append(res)
            
    # Save Report
    with open("integration_report.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
        
    print(f"\nDone. Saved {len(all_results)} scenarios to integration_report.json")

if __name__ == "__main__":
    main()
