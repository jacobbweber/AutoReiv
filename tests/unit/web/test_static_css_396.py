"""
Unit tests for modular CSS serving and index template hygiene [CARD-396].
"""

import pytest


@pytest.fixture
def client(shared_client):
    """Read-only GETs share one app per module [CARD-560]."""
    return shared_client


def test_index_serves_modular_css_links(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    for sheet in ["base.css", "components.css", "desktop.css", "studios.css"]:
        assert f"/static/css/{sheet}" in html


def test_static_css_files_served_successfully(client):
    sheets = ["base.css", "components.css", "desktop.css", "studios.css"]
    for sheet in sheets:
        response = client.get(f"/static/css/{sheet}")
        assert response.status_code == 200
        assert "text/css" in response.headers.get("content-type", "")
        assert len(response.text) > 200

