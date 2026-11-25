"""FastAPI serves the built React app: real files as they are, and index.html
for every other path so client-side routes survive a reload."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.frontend import mount_frontend

INDEX_HTML = "<!doctype html><title>Club Setup</title>"


@pytest.fixture
def frontend_client(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(INDEX_HTML)
    (dist / "assets" / "app.js").write_text("console.log('app')")
    (tmp_path / "secret.txt").write_text("outside dist")

    app = FastAPI()
    mount_frontend(app, dist)
    return TestClient(app)


def test_root_serves_index_html(frontend_client):
    response = frontend_client.get("/")
    assert response.status_code == 200
    assert response.text == INDEX_HTML


def test_a_client_side_route_serves_index_html(frontend_client):
    response = frontend_client.get("/clubs/3")
    assert response.status_code == 200
    assert response.text == INDEX_HTML


def test_a_built_asset_is_served_as_is(frontend_client):
    response = frontend_client.get("/assets/app.js")
    assert response.status_code == 200
    assert response.text == "console.log('app')"


def test_an_unknown_api_path_is_a_json_404_not_the_app(frontend_client):
    response = frontend_client.get("/api/nope")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_a_path_outside_dist_is_never_served(frontend_client):
    response = frontend_client.get("/%2e%2e/secret.txt")
    assert "outside dist" not in response.text
