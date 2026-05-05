from __future__ import annotations

import json
import re

from fastapi.testclient import TestClient


def test_spa_routes_return_modern_shell(client: TestClient) -> None:
    routes = ["/", "/teses", "/lab", "/decisoes", "/config", "/instalar"]

    for route in routes:
        response = client.get(route)

        assert response.status_code == 200, route
        assert '<div id="root"></div>' in response.text
        assert 'href="/manifest.webmanifest"' in response.text
        assert re.search(r'src="/assets/index-[^"]+\.js"', response.text)


def test_frontend_assets_are_served_from_bundle(client: TestClient) -> None:
    index_response = client.get("/")
    asset_match = re.search(r'src="(?P<asset>/assets/index-[^"]+\.js)"', index_response.text)
    assert asset_match is not None

    asset_response = client.get(asset_match.group("asset"))
    assert asset_response.status_code == 200
    assert asset_response.text
    assert "text/html" not in asset_response.headers["content-type"]

    manifest_response = client.get("/manifest.webmanifest")
    assert manifest_response.status_code == 200
    manifest = json.loads(manifest_response.text)
    assert manifest["display"] == "standalone"


def test_api_routes_still_return_json_not_shell(client: TestClient) -> None:
    health_response = client.get("/health")
    assert health_response.status_code == 200
    assert health_response.json()["status"] == "ok"

    api_response = client.get("/api/assistant/decisions")
    assert api_response.status_code == 200
    assert api_response.headers["content-type"].startswith("application/json")
    assert '<div id="root"></div>' not in api_response.text
