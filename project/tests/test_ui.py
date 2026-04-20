from __future__ import annotations

import sys


def _client():
    sys.path.insert(0, "src")
    import app as webapp

    return webapp.app.test_client(), webapp


def test_main_page() -> None:
    client, _webapp = _client()
    response = client.get("/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "대산 적재 AI" in body
    assert "최적 배차 실행" in body


def test_run_json(first_material_key: str) -> None:
    client, _webapp = _client()
    response = client.post(
        "/run",
        data={"material_key": [first_material_key], "quantity[]": ["10"]},
    )

    assert response.status_code == 200
    assert response.is_json


def test_json_keys(first_material_key: str) -> None:
    client, _webapp = _client()
    response = client.post(
        "/run",
        data={"material_key": [first_material_key], "quantity[]": ["10"]},
    )
    payload = response.get_json()

    assert payload is not None
    assert {"차량", "위험도", "시각화SVG", "팔레트목록"}.issubset(payload.keys())


def test_full_regression(first_material_key: str) -> None:
    client, _webapp = _client()
    response = client.post(
        "/run",
        data={"material_key": [first_material_key], "quantity[]": ["10"]},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["vehicle_sections"]
    assert payload["팔레트목록"]
