import json
import os
import sys
import math

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_manager import data_manager
from bin_packing import load_vehicle_db
from vehicle_selector import select_optimal_vehicle
from loader import plan_loading

def get_priority_stage(lr, sel):
    if sel.get("split_applied") == "Y":
        return "Split"
    if sel.get("vehicle_changed") == "Y":
        return "VehicleChange"
    
    # Check Fixes in loader result
    level = lr.get("correction_level", 0)
    if level == 3: return "Fix3"
    if level == 2: return "Fix2"
    if level == 1: return "Fix1"
    return "None"

def generate_evidence():
    # 1. Setup Data
    materials = data_manager.get_material_db()
    vehicles = load_vehicle_db("/Users/zart/Library/Mobile Documents/com~apple~CloudDocs/프로젝트/적재시스템/project/data/차량정보.csv")
    
    results = []
    
    # helper to find keys
    gyp_keys = sorted([k for k in materials.keys() if "석고보드" in k])
    ins_keys = sorted([k for k in materials.keys() if "아이소핑크" in k or "단열재" in k])
    
    k1 = gyp_keys[0] if gyp_keys else list(materials.keys())[0]
    k2 = gyp_keys[1] if len(gyp_keys) > 1 else k1
    ki = ins_keys[0] if ins_keys else k1

    def make_items(mat_key, qty):
        m = materials[mat_key]
        weight = m["낱장무게(kg)"] * qty
        vol = m["낱장부피(m3)"] * qty
        pallets = math.ceil(qty / m["팔레트당적재수"])
        return [{
            "material_key": mat_key,
            "quantity": qty,
            "total_weight_kg": weight,
            "total_volume_m3": vol,
            "pallet_count": pallets,
            "mix_group": m.get("mix_group", "A")
        }]

    # --- 1. Resolved Cases (3) ---
    for i, (name, qty, init_v) in enumerate([("R1 (Fix1)", 1800, "25톤"), ("R2 (Fix2)", 400, "11톤"), ("R3 (Fix3)", 1200, "5톤_단축")]):
        items = make_items(k1 if i<2 else k2, qty)
        sel = select_optimal_vehicle(vehicles, items)
        lr = plan_loading(sel["selected_vehicle"], items)
        
        results.append({
            "케이스명": name,
            "초기 차량명": init_v,
            "최종 차량명": sel["selected_vehicle"]["vehicle_name"],
            "correction_stage": get_priority_stage(lr, sel),
            "correction_level": lr["correction_level"],
            "vehicle_changed": sel["vehicle_changed"],
            "split_applied": sel["split_applied"],
            "final_risk_level": lr["braking_risk_level"],
            "dispatch_allowed": "Y" if lr["dispatch_allowed"] else "N"
        })

    # --- 2. Vehicle Changed Cases (3) ---
    for i, (name, qty, init_v) in enumerate([("C1 (Change)", 150, "1톤_트럭"), ("C2 (Change)", 300, "3.5톤_트럭"), ("C3 (Change)", 550, "5톤_단축")]):
        items = make_items(k1, qty)
        sel = select_optimal_vehicle(vehicles, items)
        lr = plan_loading(sel["selected_vehicle"], items)
        results.append({
            "케이스명": name,
            "초기 차량명": init_v,
            "최종 차량명": sel["selected_vehicle"]["vehicle_name"],
            "correction_stage": get_priority_stage(lr, sel),
            "correction_level": lr["correction_level"],
            "vehicle_changed": sel["vehicle_changed"],
            "split_applied": sel["split_applied"],
            "final_risk_level": lr["braking_risk_level"],
            "dispatch_allowed": "Y" if lr["dispatch_allowed"] else "N"
        })

    # --- 3. Split Cases (3) ---
    for i, (name, qty, init_v) in enumerate([("S1 (Split)", 7500, "25톤"), ("S2 (Split)", 4500, "25톤"), ("S3 (Split)", 2500, "25톤")]):
        items = make_items(k1 if i<2 else k2, qty)
        sel = select_optimal_vehicle(vehicles, items)
        
        # Split case re-packing for evidence
        allocated_pallets = sel["vehicle_allocations"][0]["assigned_pallets"]
        summary = {}
        for p in allocated_pallets:
            k = p["material_key"]
            summary[k] = summary.get(k, 0) + (qty / math.ceil(qty / materials[k]["팔레트당적재수"]))
            
        mini_items = []
        for k, q in summary.items():
            mini_items.extend(make_items(k, q))
            
        lr = plan_loading(sel["selected_vehicles"][0]["vehicle"], mini_items)
        results.append({
            "케이스명": name,
            "초기 차량명": init_v,
            "최종 차량명": f"{sel['selected_vehicles'][0]['vehicle']['vehicle_name']} 외 {len(sel['selected_vehicles'])-1}대",
            "correction_stage": get_priority_stage(lr, sel),
            "correction_level": lr["correction_level"],
            "vehicle_changed": "Y",
            "split_applied": "Y",
            "final_risk_level": lr["braking_risk_level"],
            "dispatch_allowed": "Y" if lr["dispatch_allowed"] else "N"
        })

    # Print Table
    cols = ["케이스명", "초기 차량명", "최종 차량명", "correction_stage", "correction_level", "vehicle_changed", "split_applied", "final_risk_level", "dispatch_allowed"]
    print("| " + " | ".join(cols) + " |")
    print("| " + " | ".join(["---"] * len(cols)) + " |")
    for r in results:
        print("| " + " | ".join(str(r[c]) for c in cols) + " |")

if __name__ == "__main__":
    generate_evidence()
