"""OC-3: Wiki note create single-lever [CARD-412 / ADR-0055].

Locks: create via canonical API path → read back same path with non-empty body.
Negative: success theater with empty/missing note must fail.
"""

from __future__ import annotations


def test_oc3_wiki_note_create_readback_nonempty(operator_client):
    client, _store, wiki = operator_client
    payload = {
        "title": "OC3 Single Lever Note",
        "category": "inbox",
        "domain": "engineering",
        "topic": "contracts",
        "document_type": "note",
        "tags": ["oc3", "card-412"],
        "summary": "Operator contract create/read smoke",
        "content": (
            "# OC3 Contract Body\n\n"
            "This note must survive create → read-back with a non-empty body.\n\n"
            "Expected field: card-412-oc3-marker\n"
        ),
    }
    create = client.post("/api/wiki/note", json=payload)
    assert create.status_code == 200, create.text
    data = create.json()
    assert data.get("success") is True
    path = data["path"]
    assert path.replace("\\", "/").startswith("00_Inbox/"), path

    read = client.get(f"/api/wiki/note?path={path}")
    assert read.status_code == 200, read.text
    note = read.json()
    assert note.get("success") is True
    content = (note.get("content") or "").strip()
    assert content, "OC-3 FAIL: success theater — note body empty on read-back"
    assert "card-412-oc3-marker" in content
    assert note.get("title") == "OC3 Single Lever Note"

    disk = wiki.joinpath(*path.split("/"))
    assert disk.is_file()
    assert "card-412-oc3-marker" in disk.read_text(encoding="utf-8")


def test_oc3_negative_empty_content_is_detectable(operator_client):
    """Empty-body create must remain detectable (no fake durable deliverable)."""
    client, _store, _wiki = operator_client
    create = client.post(
        "/api/wiki/note",
        json={
            "title": "OC3 Empty Theater",
            "category": "inbox",
            "content": "",
            "domain": "engineering",
            "topic": "contracts",
        },
    )
    assert create.status_code == 200
    path = create.json()["path"]
    read = client.get(f"/api/wiki/note?path={path}")
    assert read.status_code == 200
    content = (read.json().get("content") or "").strip()
    assert content == ""
