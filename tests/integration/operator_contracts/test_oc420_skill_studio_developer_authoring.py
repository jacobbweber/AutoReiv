"""CARD-420 operator contract: Skill Studio Build/Review mints a visible developer job.

REQ-420-001..005. Temp user-data only [ADR-0055].
Accept records a decision on the standing job and does not write skill_tool_bindings.
"""

from __future__ import annotations

import inspect

GOOD_MARKDOWN = """---
name: Wiki Digest
description: File a short wiki digest
requires_tools: []
---
# Wiki Digest

## Done-when
A wiki note exists in the inbox.
"""

GOOD_DRAFT = {
    "skill_id": "wiki_digest",
    "name": "Wiki Digest",
    "description": "File a short wiki digest",
    "tier": "pack",
    "safety": {
        "read_only": True,
        "requires_hitl": False,
        "untrusted_input_allowed": False,
    },
    "requires_tools": [],
    "markdown": GOOD_MARKDOWN,
    "intent_notes": "Keep the runbook short.",
    "source_context": "",
}


def _count(store, table: str) -> int:
    conn = store._get_connection()
    try:
        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return int(row[0])
    finally:
        if getattr(store, "_mem_conn", None) is None:
            conn.close()


def test_oc420_lint_does_not_mint_job_and_build_is_visible_developer_job(operator_client):
    """REQ-420-001, REQ-420-002, REQ-420-004, REQ-420-005."""
    client, store, _wiki = operator_client
    jobs_before = _count(store, "jobs")
    bindings_before = _count(store, "skill_tool_bindings")

    lint = client.post(
        "/api/skill_studio/authoring/lint",
        json={
            "draft": {
                **GOOD_DRAFT,
                "requires_tools": ["not_a_real_tool_420"],
                "markdown": GOOD_MARKDOWN.replace(
                    "requires_tools: []",
                    "requires_tools:\n- not_a_real_tool_420",
                ),
            }
        },
    )
    assert lint.status_code == 200, lint.text
    lint_body = lint.json()
    assert lint_body["opened_job"] is False
    assert lint_body.get("job_id") in (None, "")
    assert lint_body["llm_rewrite"] is False
    assert "markdown_content" not in lint_body
    codes = {item["code"] for item in lint_body["blockers"]}
    assert "TOOL-UNKNOWN" in codes
    assert _count(store, "jobs") == jobs_before

    created = client.post(
        "/api/skill_studio/authoring/jobs",
        json={"intent": "build", "draft": GOOD_DRAFT},
    )
    assert created.status_code == 200, created.text
    body = created.json()
    job_id = body["job_id"]
    assert job_id.startswith("job_")
    assert body["agent_id"] == "developer"
    assert body["resumed"] is False
    assert body["visible"] is True
    assert body["llm_rewrite"] is False
    assert "markdown_content" not in body
    packet = body["packet"]
    assert packet["schema"] == "skill_studio_authoring_packet"
    assert packet["version"] == 1
    assert packet["studio"] == "skill"
    assert packet["intent"] == "build"
    assert packet["draft"]["skill_id"] == "wiki_digest"
    assert packet["draft"]["markdown"] == GOOD_MARKDOWN
    assert packet["lint"]["cheap"] is True
    watch = body["watch"]
    assert watch["primary"] == "observe"
    assert watch["observe"]["studio"] == "observe"
    assert watch["observe"]["job_id"] == job_id
    assert watch["chat"]["studio"] == "chat"
    assert watch["chat"]["job_id"] == job_id
    assert watch["chat"]["agent_id"] == "developer"

    observed = client.get(f"/api/observe/jobs/{job_id}")
    assert observed.status_code == 200, observed.text
    journey = observed.json()
    job_event = next(item for item in journey["timeline"] if item.get("kind") == "job")
    assert job_event["agent_id"] == "developer"
    assert job_event["job_id"] == job_id
    packet_event = next(item for item in journey["timeline"] if item.get("kind") == "skill_studio_authoring_packet")
    assert packet_event["payload"]["skill_id"] == "wiki_digest"
    assert packet_event["payload"]["intent"] == "build"
    phase_event = next(item for item in journey["timeline"] if item.get("kind") == "phase")
    assert phase_event["assigned_agent_id"] == "developer"

    resumed = client.post(
        "/api/skill_studio/authoring/jobs",
        json={"intent": "review", "draft": GOOD_DRAFT},
    )
    assert resumed.status_code == 200, resumed.text
    again = resumed.json()
    assert again["job_id"] == job_id
    assert again["resumed"] is True
    assert again["packet"]["intent"] == "review"
    assert again["llm_rewrite"] is False
    assert _count(store, "jobs") == jobs_before + 1

    unknown = client.post(
        f"/api/skill_studio/authoring/jobs/{job_id}/proposals",
        json={"patches": [{"field": "skill_id", "value": "hijack"}]},
    )
    assert unknown.status_code == 400

    proposed = client.post(
        f"/api/skill_studio/authoring/jobs/{job_id}/proposals",
        json={"patches": [{"field": "description", "value": "Shorter trigger text"}]},
    )
    assert proposed.status_code == 200, proposed.text
    fetched = client.get(f"/api/skill_studio/authoring/jobs/{job_id}")
    assert fetched.status_code == 200, fetched.text
    detail = fetched.json()
    assert detail["agent_id"] == "developer"
    assert detail["packet"]["schema"] == "skill_studio_authoring_packet"
    assert detail["proposals"]["patches"] == [{"field": "description", "value": "Shorter trigger text"}]
    assert detail["proposals"]["decision"] is None

    accepted = client.post(
        f"/api/skill_studio/authoring/jobs/{job_id}/decision",
        json={"decision": "accept"},
    )
    assert accepted.status_code == 200, accepted.text
    decision = accepted.json()
    assert decision["decision"] == "accept"
    assert decision["persisted_skill"] is False
    assert decision["patches"] == [{"field": "description", "value": "Shorter trigger text"}]
    assert _count(store, "skill_tool_bindings") == bindings_before

    from src.application.skills import developer_authoring as authoring

    source = inspect.getsource(authoring)
    assert "SkillToolBindingRepository" not in source
    assert "skill_tool_bindings" not in source
    assert "phase_llm" not in source
    assert "scaffold/runbook" not in source
