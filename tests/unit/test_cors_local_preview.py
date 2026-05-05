from __future__ import annotations


def test_dashboard_summary_allows_vite_preview_origin(client) -> None:
    preflight = client.options(
        "/api/dashboard/summary/1",
        headers={
            "Origin": "http://127.0.0.1:4174",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://127.0.0.1:4174"
    assert preflight.headers["access-control-allow-credentials"] == "true"

    response = client.get(
        "/api/dashboard/summary/1",
        headers={"Origin": "http://127.0.0.1:4174"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:4174"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_dashboard_summary_allows_published_frontend_origin(client) -> None:
    origin = "https://thesis-lab-view.vercel.app"
    preflight = client.options(
        "/api/dashboard/summary/1",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == origin
    assert preflight.headers["access-control-allow-credentials"] == "true"

    response = client.get(
        "/api/dashboard/summary/1",
        headers={"Origin": origin},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"


def test_dashboard_summary_allows_project_preview_origin_via_regex(client) -> None:
    origin = "https://thesis-lab-view-9o1a7zg40-oracles-projects-2432cd65.vercel.app"
    preflight = client.options(
        "/api/dashboard/summary/1",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == origin
    assert preflight.headers["access-control-allow-credentials"] == "true"

    response = client.get(
        "/api/dashboard/summary/1",
        headers={"Origin": origin},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"
