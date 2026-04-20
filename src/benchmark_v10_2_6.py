import time
import os
import sys
import math
from typing import List, Dict, Any

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_manager import data_manager
from bin_packing import load_vehicle_db
from vehicle_selector import select_optimal_vehicle
from loader import plan_loading

def benchmark():
    print("=== V10.2.6 Performance Benchmark ===")
    
    # 1. Setup Data
    materials = data_manager.get_material_db()
    vehicles = load_vehicle_db("/Users/zart/Library/Mobile Documents/com~apple~CloudDocs/프로젝트/적재시스템/project/data/차량정보.csv")
    
    gyp_key = next((k for k in materials.keys() if "석고보드" in k), list(materials.keys())[0])
    m = materials[gyp_key]

    def get_test_items(qty):
        weight = m["낱장무게(kg)"] * qty
        vol = m["낱장부피(m3)"] * qty
        pallets = math.ceil(qty / m["팔레트당적재수"])
        return [{
            "material_key": gyp_key,
            "quantity": qty,
            "total_weight_kg": weight,
            "total_volume_m3": vol,
            "pallet_count": pallets,
            "mix_group": m.get("mix_group", "A")
        }]

    # --- Test 1: Single Case (Complex Stability Correction) ---
    print("\n[Test 1] Single Case (with Stability Fix)")
    items = get_test_items(1800) # Requires Fix1/2/3
    
    start_time = time.perf_counter()
    sel = select_optimal_vehicle(vehicles, items)
    _ = plan_loading(sel["selected_vehicle"], items)
    end_time = time.perf_counter()
    
    single_time = (end_time - start_time) * 1000
    print(f"Processing Time: {single_time:.2f} ms")

    # --- Test 2: Batch (10 Cases) ---
    print("\n[Test 2] Batch Processing (10 Cases)")
    qtys = [100, 500, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 8000]
    
    batch_start = time.perf_counter()
    for q in qtys:
        itms = get_test_items(q)
        sel = select_optimal_vehicle(vehicles, itms)
        if "selected_vehicle" in sel:
             _ = plan_loading(sel["selected_vehicle"], itms)
        else:
             # Multi-vehicle case
             pass
    batch_end = time.perf_counter()
    
    batch_time = (batch_end - batch_start) * 1000
    avg_time = batch_time / 10
    print(f"Total Batch Time (10 cases): {batch_time:.2f} ms")
    print(f"Average Time per Case: {avg_time:.2f} ms")

    print("\n[Benchmark Summary]")
    if batch_time < 1000:
        print("Result: PASS (Under 1s for 10 cases)")
    else:
        print("Result: SLOW (Over 1s for 10 cases)")

if __name__ == "__main__":
    benchmark()
