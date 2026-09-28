"""CARD-540 (absorbed by CARD-562): the inert allow_wiki_access field is gone; old data still loads."""

import subprocess

from src.domain.agents.guardrails import AgentProfileGuardrail
from src.domain.kernel.models import AgentProfile
from src.domain.settings.models import AgentCustomization


def test_field_is_gone_from_the_models():
    assert "allow_wiki_access" not in AgentProfile.model_fields
    assert "allow_wiki_access" not in AgentCustomization.model_fields


def test_old_profile_with_the_field_still_loads():
    old = {"id": "xa", "name": "Xa agent", "description": "d", "system_prompt": "prompt text", "allow_wiki_access": False}
    prof = AgentProfile.model_validate(old)
    assert not hasattr(prof, "allow_wiki_access")
    assert AgentCustomization.model_validate({"agent_id": "x", "allow_wiki_access": True}).agent_id == "x"
    assert AgentProfileGuardrail.validate(dict(old), available_tools=set()).id == "xa"


def test_no_code_reads_or_writes_it():
    out = subprocess.run(
        ["git", "grep", "-n", "allow_wiki_access", "--", "src"], capture_output=True, text=True, check=False
    ).stdout
    live = [ln for ln in out.splitlines() if "CARD-540" not in ln]
    assert live == []
