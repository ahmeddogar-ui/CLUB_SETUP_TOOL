"""How main.py serves the built React app (FastAPI's app.frontend): real files
as they are, index.html for page navigations to client-side routes, and a
plain 404 for anything else, so API clients never get HTML by mistake."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import revalidate_html_pages

INDEX_HTML = "<!doctype html><title>Club Setup</title>"
PAGE_NAVIGATION = {"Accept": "text/html"}


@pytest.fixture
def frontend_client(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(INDEX_HTML)
    (dist / "assets" / "app.js").write_text("console.log('app')")
    (tmp_path / "secret.txt").write_text("outside dist")

    app = FastAPI()
    app.middleware("http")(revalidate_html_pages)
    app.frontend("/", directory=dist, fallback="index.html")
    return TestClient(app)


def test_root_serves_index_html(frontend_client):
    response = frontend_client.get("/", headers=PAGE_NAVIGATION)
    assert response.status_code == 200
    assert response.text == INDEX_HTML


def test_navigating_to_a_client_side_route_serves_index_html(frontend_client):
    response = frontend_client.get("/clubs/3", headers=PAGE_NAVIGATION)
    assert response.status_code == 200
    assert response.text == INDEX_HTML


def test_a_built_asset_is_served_as_is(frontend_client):
    response = frontend_client.get("/assets/app.js")
    assert response.status_code == 200
    assert response.text == "console.log('app')"


def test_a_missing_asset_is_404_not_the_app(frontend_client):
    assert frontend_client.get("/assets/old-build.js").status_code == 404


def test_an_unknown_api_call_is_404_not_the_app(frontend_client):
    headers = {"Accept": "application/json"}
    assert frontend_client.get("/api/nope", headers=headers).status_code == 404
    assert frontend_client.post("/api/nope", headers=headers).status_code == 404


@pytest.mark.parametrize("path", ["/%2e%2e/secret.txt", "//etc/passwd"])
def test_a_path_outside_dist_is_never_served(frontend_client, path):
    response = frontend_client.get(path, headers=PAGE_NAVIGATION)
    assert "outside dist" not in response.text
    assert "root:" not in response.text


def test_pages_are_revalidated_so_a_redeploy_is_picked_up(frontend_client):
    # A stale index.html would point at hashed assets that no longer exist.
    response = frontend_client.get("/clubs/3", headers=PAGE_NAVIGATION)
    assert response.headers["Cache-Control"] == "no-cache"


def test_hashed_assets_keep_the_default_caching(frontend_client):
    response = frontend_client.get("/assets/app.js")
    assert "Cache-Control" not in response.headers
