"""
Unit tests for Chat Multi-Phase Deliverable Deduplication [CARD-409].
"""

from src.web.routers.chat import deduplicate_phase_deliverables


def test_deduplicate_phase_deliverables_prefers_final_content_without_stutter():
    priors = [
        "### System Health Check\nAll services operational. Staged to 00_Inbox/system_health.md.",
    ]
    final = (
        "Done ✅ — System Health Check completed and note staged to `00_Inbox/system_health.md`.\n\n"
        "### Telemetry Summary\n- API: Healthy\n- DB: Healthy"
    )

    result = deduplicate_phase_deliverables(priors, final)
    # Must NOT concatenate priors with `---` if final already covers the outcome
    assert "---" not in result
    assert result.strip() == final.strip()


def test_deduplicate_phase_deliverables_handles_empty_priors():
    final = "Standalone final deliverable."
    assert deduplicate_phase_deliverables([], final) == final


def test_deduplicate_phase_deliverables_handles_empty_final_content():
    priors = ["Prior phase deliverable."]
    assert deduplicate_phase_deliverables(priors, "") == "Prior phase deliverable."


def test_deduplicate_phase_deliverables_preserves_genuinely_disjoint_deliverables():
    # If prior was a distinct artifact/phase not mentioned or covered in final at all
    priors = ["### Phase 1 Output: Code Migration Diff\n```diff\n+ line\n```"]
    final = "### Phase 2 Output: Test Run Results\n15 tests passed."
    result = deduplicate_phase_deliverables(priors, final)
    # Genuinely disjoint different outputs are kept together
    assert "Phase 1 Output" in result
    assert "Phase 2 Output" in result
