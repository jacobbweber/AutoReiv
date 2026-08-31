"""CARD-100 Chat Job/Phase UI [REQ-ORCH-042]."""

from pathlib import Path

INDEX_HTML = Path("src/web/templates/index.html")
CHAT_JS = Path("src/web/static/modules/studios/chat.js")


def test_goal_badge_is_multi_phase_job_not_plan_graph():
    html = INDEX_HTML.read_text(encoding="utf-8")
    js = CHAT_JS.read_text(encoding="utf-8")
    assert "Plan Graph Active" not in html
    assert "Plan Graph Active" not in js
    assert "Plan Graph" not in html
    assert "Plan Graph" not in js
    assert "Multi-phase job" in html
    assert 'id="goalBadge"' in html
    assert "Self-Verify" in html


def test_job_phase_status_strip_consumes_sse_and_names_parked_failed():
    html = INDEX_HTML.read_text(encoding="utf-8")
    js = CHAT_JS.read_text(encoding="utf-8")
    assert 'id="jobPhaseStatusStrip"' in html
    assert 'data-job-phase="status"' in html
    assert 'data-job-phase="phase"' in html
    assert 'data-job-phase="agent"' in html
    assert 'data-job-phase="react"' in html
    assert "function applyJobPhaseEvent" in js
    assert "function formatJobPhaseStrip" in js
    assert "function updateJobPhaseFromEvent" in js
    assert "eventType === 'job_created'" in js
    assert "eventType === 'phase_start'" in js
    assert "eventType === 'phase_complete'" in js
    assert "eventType === 'react_state'" in js
    for state in ("THINKING", "CALLING_TOOLS", "PARKED", "DONE", "FAILED"):
        assert state in js
    assert "Graph" not in html.split('id="goalBadge"')[1].split("</div>")[0]
