"""CARD-603: per-agent template folders, AutoReiv study routing, run-state memory filter."""

from contextlib import contextmanager

import pytest

from src.application.kernel.tool_registry import _tool_context
from src.application.memory.extractor import is_short_lived_fact
from src.application.skills.wiki_tools import WikiTools
from src.domain.agents.guardrails import AgentProfileGuardrail, AgentValidationError
from src.domain.wiki.template_folders import TemplateFolderError, is_hidden, normalize_template_folder
from src.infrastructure.agents.agent_files import meta_from_profile
from tests.unit.agent_skills.catalog import platform_pack_profile

GENERAL = "02_Resources/_Templates/General"
EDUCATION = "02_Resources/_Templates/Education"


@contextmanager
def as_agent(agent_id, template_folder):
    token = _tool_context.set({"agent_id": agent_id, "template_folder": template_folder})
    try:
        yield
    finally:
        _tool_context.reset(token)


@pytest.fixture
def tools(tmp_path):
    return WikiTools(wiki_root=tmp_path / "wiki")


def _slugs(rows):
    return {r["slug"] for r in rows}


def test_shipped_agents_set_their_template_folder():
    assert platform_pack_profile("autoreiv").template_folder == GENERAL
    assert platform_pack_profile("tutor").template_folder == EDUCATION


def test_scaffold_seeds_templates_into_group_folders(tools):
    root = tools.store.root_dir / "02_Resources" / "_Templates"
    assert (root / "General" / "adr-decision.md").is_file()
    assert (root / "General" / "weekly_notes.md").is_file()
    assert (root / "Education" / "education-flashcard.md").is_file()
    assert (root / "Education" / "feynman-technique.md").is_file()
    assert not (root / "adr-decision.md").exists()


def test_scaffold_does_not_duplicate_unsorted_root_templates(tmp_path):
    root = tmp_path / "wiki" / "02_Resources" / "_Templates"
    root.mkdir(parents=True)
    (root / "adr-decision.md").write_text("---\ntitle: Mine\ndocument_type: template\n---\n\n# Mine\n", encoding="utf-8")
    WikiTools(wiki_root=tmp_path / "wiki")
    assert not (root / "General" / "adr-decision.md").exists()
    assert (root / "adr-decision.md").read_text(encoding="utf-8").count("Mine") == 2


def test_list_and_read_are_confined_to_the_agents_folder(tools):
    with as_agent("autoreiv", GENERAL):
        general = _slugs(tools.wiki_template_list())
        assert "adr-decision" in general and "weekly-notes" in general
        assert not any(s.startswith("education-") for s in general)
        assert tools.wiki_template_read("adr-decision")["path"].startswith(GENERAL + "/")
        missing = tools.wiki_template_read("education-flashcard")
        assert missing["success"] is False and "not found" in missing["error"]
    with as_agent("tutor", EDUCATION):
        education = _slugs(tools.wiki_template_list())
        assert "education-flashcard" in education and "adr-decision" not in education
        assert tools.wiki_template_read("adr-decision")["success"] is False


def test_create_lands_in_own_folder_and_update_outside_is_not_found(tools):
    with as_agent("autoreiv", GENERAL):
        res = tools.create_wiki_template(slug="incident-postmortem", title="Incident", description="d", content="# X")
        assert res["success"] and res["path"] == f"{GENERAL}/incident-postmortem.md"
        upd = tools.update_wiki_template(slug="education-quiz", title="hijack")
        assert upd["success"] is False and "not found" in upd["error"]
    with as_agent("tutor", EDUCATION):
        assert tools.update_wiki_template(slug="incident-postmortem", title="x")["success"] is False
        assert "incident-postmortem" not in _slugs(tools.wiki_template_list())


def test_use_outside_the_folder_is_not_found(tools):
    with as_agent("autoreiv", GENERAL):
        res = tools.wiki_note_create(title="Quiz me", template="education-quiz")
        assert res["success"] is False and "not found" in res["error"]
        ok = tools.wiki_note_create(title="Decision 1", template="adr-decision")
        assert ok["success"] and ok["path"].startswith("00_Inbox/")


def test_search_and_read_skip_other_agents_template_folders(tools):
    with as_agent("autoreiv", GENERAL):
        hits = tools.wiki_note_search(query="", limit=200, document_type="template")
        paths = [h["path"] for h in hits]
        assert any(p.startswith(GENERAL + "/") for p in paths)
        assert not any(p.startswith(EDUCATION + "/") for p in paths)
        listed = [n["path"] for n in tools.wiki_note_list(category="resources")]
        assert not any(p.startswith(EDUCATION + "/") for p in listed)
        assert EDUCATION not in str(tools.get_wiki_overview(max_items=200))
        read = tools.wiki_note_read(relative_path=f"{EDUCATION}/education-flashcard.md")
        assert read["success"] is False and "not found" in read["error"]
        upd = tools.wiki_note_update(relative_path=f"{EDUCATION}/education-flashcard.md", content="x")
        assert upd["success"] is False
    with as_agent("tutor", EDUCATION):
        hits = tools.wiki_note_search(query="", limit=200, document_type="template")
        assert not any(h["path"].startswith(GENERAL + "/") for h in hits)


def test_agent_without_a_folder_has_no_templates(tools):
    with as_agent("custom-agent", None):
        assert tools.wiki_template_list() == []
        assert tools.wiki_template_read("adr-decision")["success"] is False
        res = tools.create_wiki_template(slug="x", title="X", description="d", content="# X")
        assert res["success"] is False and "Agent Studio" in res["error"]
        assert tools.wiki_note_create(title="t", template="adr-decision")["success"] is False


def test_missing_or_empty_folders_are_handled(tools):
    with as_agent("autoreiv", "02_Resources/_Templates/DoesNotExist"):
        assert tools.wiki_template_list() == []
        assert tools.wiki_template_read("adr-decision")["success"] is False
        res = tools.create_wiki_template(slug="first", title="First", description="d", content="# F")
        assert res["success"] and res["path"] == "02_Resources/_Templates/DoesNotExist/first.md"


def test_platform_callers_still_see_every_template(tools):
    slugs = _slugs(tools.wiki_template_list())
    assert {"adr-decision", "education-flashcard"} <= slugs
    assert tools.wiki_template_read("education-flashcard") is not None


def test_folder_setting_is_validated_and_saved():
    assert normalize_template_folder(" 02_Resources\\_Templates\\General/ ") == GENERAL
    assert normalize_template_folder("") is None
    for bad in ("../outside", "C:/Users/x", "/abs/path", "02_Resources/../../x"):
        with pytest.raises(TemplateFolderError):
            normalize_template_folder(bad)
    base = {"id": "helper", "name": "Helper", "system_prompt": "You help the operator with wiki notes."}
    with pytest.raises(AgentValidationError):
        AgentProfileGuardrail.validate({**base, "template_folder": "../x"})
    profile = AgentProfileGuardrail.validate({**base, "template_folder": "02_Resources/_Templates/Helper"})
    assert profile.template_folder == "02_Resources/_Templates/Helper"
    meta, _ = meta_from_profile(profile)
    assert meta["template_folder"] == "02_Resources/_Templates/Helper"
    assert "template_folder" not in meta_from_profile(AgentProfileGuardrail.validate(base))[0]


def test_is_hidden_keeps_own_folder_visible_inside_a_wider_one():
    assert is_hidden(f"{EDUCATION}/a.md", GENERAL, [EDUCATION])
    assert not is_hidden(f"{GENERAL}/a.md", GENERAL, ["02_Resources/_Templates"])
    assert not is_hidden("01_Notes/a.md", GENERAL, [EDUCATION])


def test_autoreiv_sends_study_requests_to_tutor_without_tools():
    prompt = platform_pack_profile("autoreiv").system_prompt
    assert "flashcards, quizzes" in prompt and "open Tutor in Chat" in prompt
    assert "do not search the wiki or call any tool" in prompt


@pytest.mark.parametrize(
    "entity,attribute,value",
    [
        ("system", "max_steps_per_reply", "50"),
        ("project", "spaced_flashcard_template", "identified_in_wiki_vault"),
        ("assistant", "search_progress", "searched inbox"),
        ("system", "context_window", "262144"),
    ],
)
def test_run_state_is_never_a_durable_fact(entity, attribute, value):
    assert is_short_lived_fact(entity, attribute, value)


@pytest.mark.parametrize(
    "entity,attribute,value",
    [
        ("user", "preferred_study_time_of_day", "evening"),
        ("user", "preferred_study_session_duration_minutes", "10"),
        ("system", "os_platform", "windows"),
        ("user", "wiki_template_incident_postmortem_name", "Incident Postmortem"),
    ],
)
def test_durable_facts_are_kept(entity, attribute, value):
    assert not is_short_lived_fact(entity, attribute, value)
