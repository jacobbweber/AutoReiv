"""CARD-438: Tutor max_turns Studio Save must not 422 when pack tools lag the catalog."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.web.app import create_app


def test_tutor_put_max_turns_persists_when_education_tools_missing_from_catalog():
    """Simulate stale worker: education_* on Tutor allowlist but unmounted from catalog."""
    app = create_app()
    with TestClient(app) as client:
        before = client.get("/api/agents/tutor")
        assert before.status_code == 200, before.text
        payload = before.json()
        assert "education_quiz_extract" in (payload.get("allowed_tool_names") or [])

        # Unmount education tools from the live catalog (stale-worker simulation).
        tool_reg: ScopedToolRegistry = client.app.state.tool_reg
        for name in list(tool_reg._tools):
            if str(name).startswith("education_"):
                tool_reg.unmount_tool(name)
        assert "education_quiz_extract" not in {t.name for t in tool_reg.list_tools()}

        payload["max_turns"] = 100
        # Studio always re-sends skill-derived tools including education_*.
        put = client.put("/api/agents/tutor", json=payload)
        assert put.status_code == 200, put.text
        assert put.json()["agent"]["max_turns"] == 100

        after = client.get("/api/agents/tutor")
        assert after.status_code == 200
        assert after.json()["max_turns"] == 100

        # Brand-new unknown tool still rejected.
        payload["max_turns"] = 50
        payload["allowed_tool_names"] = list(payload.get("allowed_tool_names") or []) + [
            "definitely_not_a_real_tool_zz"
        ]
        bad = client.put("/api/agents/tutor", json=payload)
        assert bad.status_code == 422
        assert "definitely_not_a_real_tool_zz" in bad.text
