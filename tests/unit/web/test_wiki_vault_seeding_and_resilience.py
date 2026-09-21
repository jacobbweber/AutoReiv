"""
Unit tests for Wiki Vault Seeding, System Info Resiliency, and Settings Matrix Hardening [REQ-WIKI-011, REQ-WIKI-012, REQ-SYST-004, REQ-SET-009].
"""

import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from src.application.gateway.gateway_service import MultiProviderGateway
from src.domain.wiki.store import WikiStore
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


def test_wiki_store_seed_starter_notes():
    """Verify that WikiStore scaffolds clean vanilla folder structure and templates [REQ-WIKI-011, CARD-406]."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = WikiStore(root_dir=tmp_dir, auto_seed=True)
        store.scaffold()

        # Check directories exist
        assert (Path(tmp_dir) / "00_Inbox").exists()
        assert (Path(tmp_dir) / "01_Notes").exists()
        assert (Path(tmp_dir) / "02_Resources" / "operating_manuals").exists()
        assert (Path(tmp_dir) / "02_Resources" / "_Templates").exists()
        assert (Path(tmp_dir) / "03_Archive").exists()

        # Check inbox is clean (vanilla install, no starter notes)
        inbox_dir = Path(tmp_dir) / "00_Inbox"
        inbox_files = list(inbox_dir.glob("*.md"))
        assert len(inbox_files) == 0

        # Check notes are clean (vanilla install, no pre-filled notes)
        notes_dir = Path(tmp_dir) / "01_Notes"
        notes_files = list(notes_dir.rglob("*.md"))
        assert len(notes_files) == 0

        # Check templates exist in _Templates
        templates_dir = Path(tmp_dir) / "02_Resources" / "_Templates"
        assert (templates_dir / "tag-authority.md").exists()
        assert (templates_dir / "note_template.md").exists()
        assert len(list(templates_dir.glob("*.md"))) >= 2

        # Verify tree hierarchy reflects empty notes/inbox and valid structure
        tree = store.get_tree()
        assert len(tree["inbox"]) == 0
        assert len(tree["notes"]) == 0


def test_settings_matrix_dual_shape_payload(tmp_path):
    """Verify that /api/settings/matrix accepts both nested purposes dict and flat dict [REQ-SET-009]."""
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    gateway = MultiProviderGateway(default_provider_id="ollama")
    app = create_app(state_store=store, gateway_instance=gateway, wiki_path=str(tmp_path / "wiki"))
    client = TestClient(app)

    # 1. Test nested payload (from SPA frontend)
    nested_payload = {
        "default_model": "llama3.2:1b",
        "purposes": {
            "general": "llama3.2:1b",
            "reasoning": "deepseek-r1:8b",
            "task_execution": "qwen2.5-coder:7b",
            "vision": "default",
            "auxiliary": "default",
            "fast": "llama3.2:1b",
        },
    }
    res = client.post("/api/settings/matrix", json=nested_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "updated"
    assert data["matrix"]["purposes"]["general"] == "llama3.2:1b"
    assert data["matrix"]["purposes"]["reasoning"] == "deepseek-r1:8b"

    # 2. Test flat payload (from legacy/simple callers)
    flat_payload = {
        "default_model": "gpt-4o",
        "general": "gpt-4o",
        "reasoning": "o1-preview",
    }
    res2 = client.post("/api/settings/matrix", json=flat_payload)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "updated"
    assert data2["matrix"]["default_model"] == "gpt-4o"
    assert data2["matrix"]["purposes"]["general"] == "gpt-4o"


def test_model_discovery_offline_fallback(tmp_path):
    """Verify that /api/models/discover handles offline providers gracefully without crashing [REQ-SET-009]."""
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    gateway = MultiProviderGateway(default_provider_id="ollama")
    app = create_app(state_store=store, gateway_instance=gateway, wiki_path=str(tmp_path / "wiki"))
    client = TestClient(app)

    # Point to an unreachable host on random port
    res = client.get("/api/models/discover?provider_id=ollama&host_url=http://127.0.0.1:59999")
    assert res.status_code == 200
    data = res.json()
    assert "models" in data
    assert len(data["models"]) >= 1
    assert any("llama" in m["name"].lower() for m in data["models"])
