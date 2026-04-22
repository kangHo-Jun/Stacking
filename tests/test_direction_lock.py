import pytest
from loader import _compute_floor_grid

def test_compute_floor_grid_without_lock():
    # 25톤 기본 제원 (10100 x 2400)
    L, W = 10100, 2400
    
    # 방향 고정 없을 때: 최적 배치(회전 포함) 선택 -> 11 (11x1)
    cols, rows, p_len, p_wid = _compute_floor_grid(L, W, locked_direction=False)
    assert cols == 11
    assert rows == 1
    assert p_len == 900.0
    assert p_wid == 1800.0

def test_compute_floor_grid_with_lock():
    # 25톤 기본 제원 (10100 x 2400)
    L, W = 10100, 2400
    
    # 방향 고정(Y) 일 때: 방향A(1800 길이방향) 강제 -> 10 (5x2)
    cols, rows, p_len, p_wid = _compute_floor_grid(L, W, locked_direction=True)
    assert cols == 5
    assert rows == 2
    assert p_len == 1800.0
    assert p_wid == 900.0

if __name__ == "__main__":
    pytest.main([__file__])
