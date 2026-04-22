import sys
import os

# Add src to path
sys.path.append(os.path.abspath('project/src'))

from loader import _compute_floor_grid

def analyze():
    # 1. Vehicle dimensions from default in loader.py or typical 25t
    # Based on loader.py: cargo_length_mm = 10100.0, cargo_width_mm = 2400.0
    L = 10100.0
    W = 2400.0
    
    cols, rows, p_len, p_wid = _compute_floor_grid(L, W)
    print(f"Vehicle: {L} x {W}")
    print(f"Grid: cols={cols}, rows={rows}")
    print(f"Pallet Dims: {p_len} x {p_wid}")
    print(f"Total slots: {cols * rows}")
    
    # 2. 2500 sheets calculation
    # Material: '석고보드 9.5*900*2400'
    # Typically 80 sheets per pallet
    qty = 2500
    cap = 80
    full_pallets = qty // cap
    remainder = qty % cap
    print(f"\n2500 sheets / {cap} per pallet:")
    print(f"Full pallets: {full_pallets}")
    print(f"Remainder: {remainder} ({'sheet unit' if remainder > 0 else 'none'})")
    print(f"Total pallet objects: {full_pallets + (1 if remainder else 0)}")

if __name__ == "__main__":
    analyze()
