"""CARD-322: Education Learning OS — Wiki templates for every Education artifact.

Verifies:
- [REQ-EDU-WIKI-TPL-001]: Catalog of Wiki templates covering Education notes, quizzes, flashcards, labs, scores.
- [REQ-EDU-WIKI-TPL-002]: Education create/update write-back paths require template_id / template tag + front matter.
- [REQ-EDU-WIKI-TPL-003]: No freeform Education dump path that bypasses templates.
- [REQ-EDU-WIKI-TPL-004]: Proof: after Priming / Retrieval / course steps, Wiki notes show expected template front matter.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.education.construction import create_study_artifact_note
from src.application.education.course import (
    ORDERED_COURSE_STEPS,
    complete_course_step,
    start_or_resume_course,
)
from src.application.education.priming_wiki_io import create_priming_note
from src.application.education.templates import (
    EDUCATION_TEMPLATES,
    EducationTemplateRequiredError,
    assert_education_template_required,
    get_education_template,
    get_template_for_step,
    list_education_templates,
)
from src.application.skills.wiki_tools import WikiTools
from src.domain.wiki.frontmatter import FrontmatterParser
from src.domain.wiki.store import WikiStore
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


def test_req_edu_wiki_tpl_001_catalog_contains_all_education_templates(tmp_path: Path):
    """[REQ-EDU-WIKI-TPL-001] Catalog covers notes, quizzes, flashcards, labs, scores."""
    # Check template registry module
    templates = list_education_templates()
    template_slugs = {t["slug"] for t in templates}

    expected_slugs = {
        "education-priming",
        "education-dual-coding",
        "education-elaboration",
        "education-quiz",
        "education-flashcard",
        "education-lab",
        "education-score",
    }
    assert expected_slugs.issubset(template_slugs)

    for slug in expected_slugs:
        t = get_education_template(slug)
        assert t is not None
        assert t["title"]
        assert t["description"]
        assert "content" in t

    # Verify WikiStore scaffolding seeds them into 02_Resources/_Templates/
    wiki_root = tmp_path / "wiki"
    store = WikiStore(root_dir=wiki_root)
    store.scaffold()

    seeded_templates = store.list_templates()
    seeded_slugs = {s["slug"] for s in seeded_templates}
    for slug in expected_slugs:
        assert slug in seeded_slugs, f"Expected template {slug} to be seeded in WikiStore"


def test_req_edu_wiki_tpl_002_writebacks_require_and_persist_template_frontmatter(tmp_path: Path):
    """[REQ-EDU-WIKI-TPL-002] Education writebacks require template_id and serialize it into YAML frontmatter."""
    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    tools = WikiTools(wiki_root=wiki_root)

    # 1. create_priming_note persists template in frontmatter
    res = create_priming_note(
        tools,
        title="Paxos Priming Schema",
        content="## Outline\n- Consensus algorithm overview",
        topic="Paxos Consensus",
    )
    assert res["success"] is True
    path = wiki_root / res["path"]
    assert path.exists()

    content = path.read_text(encoding="utf-8")
    meta, body = FrontmatterParser.parse(content)
    assert meta.template == "education-priming"
    assert "education" in meta.tags
    assert meta.topic == "paxos_consensus"

    # 2. create_study_artifact_note persists template in frontmatter
    res_lab = create_study_artifact_note(
        tools,
        title="Raft Leader Election Lab",
        content="## Objective\nConstruct leader election state machine.",
        topic="Raft Consensus",
    )
    assert res_lab["success"] is True
    path_lab = wiki_root / res_lab["path"]
    assert path_lab.exists()

    content_lab = path_lab.read_text(encoding="utf-8")
    meta_lab, _ = FrontmatterParser.parse(content_lab)
    assert meta_lab.template == "education-lab"
    assert "education" in meta_lab.tags


def test_req_edu_wiki_tpl_003_freeform_dump_rejected(tmp_path: Path):
    """[REQ-EDU-WIKI-TPL-003] Attempting to create an Education artifact without an authorized template fails."""
    # Blank or None template must be rejected
    with pytest.raises(EducationTemplateRequiredError):
        assert_education_template_required(None)

    with pytest.raises(EducationTemplateRequiredError):
        assert_education_template_required("")

    with pytest.raises(EducationTemplateRequiredError):
        assert_education_template_required("unregistered-random-template")

    # Valid education template is accepted
    assert assert_education_template_required("education-quiz") == "education-quiz"
    assert assert_education_template_required("education-lab") == "education-lab"

    # Reject in write-back functions as well
    wiki_root = tmp_path / "wiki"
    tools = WikiTools(wiki_root=wiki_root)
    with pytest.raises(EducationTemplateRequiredError):
        create_priming_note(tools, title="Bad", content="test", topic="test", template="")

    with pytest.raises(EducationTemplateRequiredError):
        create_study_artifact_note(tools, title="Bad", content="test", topic="test", template="not-a-real-template")


def test_req_edu_wiki_tpl_004_course_steps_produce_valid_template_frontmatter(tmp_path: Path):
    """[REQ-EDU-WIKI-TPL-004] Course step artifacts across priming, dual_coding, retrieval have correct template frontmatter."""
    # All ordered course steps map to known education templates
    for step in ORDERED_COURSE_STEPS:
        tpl_slug = get_template_for_step(step)
        assert tpl_slug in EDUCATION_TEMPLATES

    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    tools = WikiTools(wiki_root=wiki_root)

    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    course = start_or_resume_course(
        repo, topic_id="Raft Log Replication", steps=ORDERED_COURSE_STEPS
    )

    # 1. Complete priming
    res_priming = complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    path_priming = wiki_root / res_priming["wiki_path"]
    meta_p, _ = FrontmatterParser.parse(path_priming.read_text(encoding="utf-8"))
    assert meta_p.template == "education-priming"

    # 2. Complete dual_coding
    res_dual = complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    path_dual = wiki_root / res_dual["wiki_path"]
    meta_d, _ = FrontmatterParser.parse(path_dual.read_text(encoding="utf-8"))
    assert meta_d.template == "education-dual-coding"

    # 3. Complete retrieval
    res_retrieval = complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    path_retrieval = wiki_root / res_retrieval["wiki_path"]
    meta_r, _ = FrontmatterParser.parse(path_retrieval.read_text(encoding="utf-8"))
    assert meta_r.template == "education-quiz"

    # 4. Complete elaboration
    res_elab = complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    path_elab = wiki_root / res_elab["wiki_path"]
    meta_e, _ = FrontmatterParser.parse(path_elab.read_text(encoding="utf-8"))
    assert meta_e.template == "education-elaboration"

    # 5. Complete construction
    res_const = complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    path_const = wiki_root / res_const["wiki_path"]
    meta_c, _ = FrontmatterParser.parse(path_const.read_text(encoding="utf-8"))
    assert meta_c.template == "education-lab"

