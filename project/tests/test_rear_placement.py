import pytest
from loader import _plan_loading_from_pallets

def test_rear_placement_logic():
    # 1. 가상 차량 설정 (10.1m 길이 - 5열 배치 가능, 1,100mm 남음)
    vehicle = {
        "cargo_length_mm": 10100.0,
        "cargo_width_mm": 2400.0,
        "max_weight_kg": 25000.0,
        "axles": 3,
        "cargo_volume_m3": 50.0
    }
    
    # 2. 11개 팔레트 생성 (방향고정=Y를 통해 5x2=10슬롯 그리드 강제)
    pallets = []
    for i in range(11):
        pallets.append({
            "id": f"P{i+1}",
            "weight_kg": 1000.0,
            "material_name": "Test Material",
            "direction_locked": "Y",  # <--- 이 부분이 핵심 (회전 배치 차단)
            "volume_m3": 1.0,
            "qty": 1,
            "unit_type": "pallet",
            "preferred_position": "하단"
        })
    
    # 3. 로직 실행 (Standard grid fits 10, 11th should go to rear space)
    result = _plan_loading_from_pallets(vehicle, pallets)
    placements = result["placements"]
    
    # 4. 검증
    # 11번째 팔레트가 is_rear_entry=True 인지 확인
    rear_items = [p for p in placements if p.get("is_rear_entry")]
    assert len(rear_items) == 1
    
    rear_pallet = rear_items[0]
    assert rear_pallet["id"] == "P11"
    assert rear_pallet["is_rear_entry"] is True
    
    # x_mm 좌표 확인: 10100 - (1100/2) = 9550
    assert 9540 <= rear_pallet["x_mm"] <= 9560
    
    # 전방 밀착 여부 확인: 첫 번째 팔레트의 x_mm이 900이어야 함
    first_pallet = [p for p in placements if p["id"] == "P1" and p["layer"] == 1][0]
    assert first_pallet["x_mm"] == 900.0

if __name__ == "__main__":
    pytest.main([__file__])
