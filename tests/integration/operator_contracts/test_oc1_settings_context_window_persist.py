"""OC-1: Settings context-window persist [CARD-412 / ADR-0055].

Locks: save static default_context_window via settings API → re-read → value matches.
Negative: silent drop / mismatch after save must fail.
"""

from __future__ import annotations


def test_oc1_default_context_window_persists_across_reread(operator_client):
    client, store, _wiki = operator_client
    target = 131072

    save = client.post(
        "/api/settings/matrix",
        json={
            "default_model": "qwen3:8b",
            "default_context_window": target,
            "purposes": {"fast": "qwen3:8b"},
            "model_context_windows": {},
            "max_concurrent_generations": 1,
        },
    )
    assert save.status_code == 200, save.text
    body = save.json()
    assert body.get("status") == "updated"
    assert body["matrix"]["default_context_window"] == target

    # Process-equivalent reload: re-GET settings (fresh read from SQLite)
    got = client.get("/api/settings")
    assert got.status_code == 200
    matrix = got.json()["matrix"]
    assert matrix["default_context_window"] == target, (
        f"OC-1 FAIL: context window did not persist (got {matrix.get('default_context_window')!r})"
    )

    # Negative: must not silently fall back to None/0 after a second independent store read
    raw = store.get_setting("purpose_matrix") or {}
    assert raw.get("default_context_window") == target
    assert raw.get("default_context_window") not in (None, 0, "0", "")


def test_oc1_context_window_survives_provider_save_roundtrip(operator_client):
    """Saving providers must not wipe a previously persisted context window [CARD-412]."""
    client, _store, _wiki = operator_client
    target = 262144

    client.post(
        "/api/settings/matrix",
        json={"default_model": "default", "default_context_window": target, "purposes": {}},
    )
    prov = client.post(
        "/api/settings/providers",
        json={
            "provider_id": "ollama",
            "base_url": "http://127.0.0.1:11434",
            "default_model_id": "llama3.2:1b",
            "set_as_default": True,
            "default_provider_id": "ollama",
        },
    )
    assert prov.status_code == 200

    got = client.get("/api/settings")
    assert got.json()["matrix"]["default_context_window"] == target
