"""
Unit tests for modular CSS serving and index template hygiene [CARD-396].
"""

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def client(tmp_path):
    store = SQLiteStateStore(db_path=str(tmp_path / "test.db"))
    app = create_app(
        state_store=store,
        wiki_path=str(tmp_path / "wiki"),
    )
    return TestClient(app)


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


def test_index_inline_style_hygiene(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    # Monolithic inline styles (which were > 1,300 lines) are eliminated from index.html
    assert "CARD-315: Education sections collapse" not in html
    assert "CARD-312: Observe expand scrolls" not in html
    assert "CARD-313: Settings collapse" not in html
    assert "CARD-314: Factory fills hosted" not in html
