from __future__ import annotations


def test_dashboard_summary_allows_local_vite_origin(client) -> None:
    preflight = client.options(
        "/api/dashboard/summary/1",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:5173"

    response = client.get(
        "/api/dashboard/summary/1",
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
