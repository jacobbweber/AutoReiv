"""CARD-739: Multi-turn active-project SDLC dogfood and Tutor study flow integration contract.

Exercises:
1. Active-project SDLC loop: create_project (auto-selects + initializes empty root commit on main) ->
   write AGENTS.md with Checks -> write_card (defaults to Proposed) -> git_create_branch ->
   write_project_file -> git_commit -> run_project_checks -> set_card_status("In Review") ->
   review_card -> finish_review("Done").
2. Tutor study loop: start_or_resume_course (slug topic_id) -> skill_view progressive references
   (socratic-tutoring priming-and-construction.md, quiz-turn grading-rubric.md) ->
   wiki_note_create + education_quiz_extract (title-case topic) -> education_quiz_grade ->
   education_progress_summary & education_progress_mastery (slug vs title-case topic matching).
"""

from __future__ import annotations

import sys
from pathlib import Path

from src.application.education.course import start_or_resume_course
from src.application.kernel.tool_registry import _tool_context
from src.application.safety.tool_policy_gate import expand_education_wiki_note_tools
from src.application.sdlc.check_record import GreenCheckRecord
from src.application.sdlc.projects_service import ProjectsService
from src.application.skills.card_review_tools import CardReviewTools
from src.application.skills.card_tools import CardTools
from src.application.skills.education_tools import EducationTools
from src.application.skills.git_tools import GitTools
from src.application.skills.project_dev_tools import ProjectDevTools
from src.application.skills.project_file_tools import ProjectFileTools
from src.application.skills.session_skills import clear_session_skill_activations
from src.application.skills.user_catalog import UserSkillCatalog
from src.application.skills.wiki_tools import WikiTools
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def test_active_project_multi_turn_sdlc_dogfood_from_fresh_create_project(tmp_path: Path) -> None:
    """Fresh create_project selects the repo, has a valid main HEAD for branching, and moves Proposed -> In Review -> Done."""
    store = SQLiteStateStore(db_path=str(tmp_path / "state.db"))
    store.initialize_db()
    projects_dir = tmp_path / "projects"
    svc = ProjectsService(store=store, projects_dir=projects_dir)
    check_rec = GreenCheckRecord(path=tmp_path / "sdlc" / "green-checks.json")

    file_tools = ProjectFileTools(root_resolver=svc.selected_or_refuse)
    dev_tools = ProjectDevTools(root_resolver=svc.selected_or_refuse, check_record=check_rec)
    git_tools = GitTools(root_resolver=svc.selected_or_refuse)
    card_tools = CardTools(root_resolver=svc.selected_or_refuse, check_record=check_rec)
    review_tools = CardReviewTools(
        root_resolver=svc.selected_or_refuse,
        card_tools=card_tools,
        dev_tools=dev_tools,
        check_record=check_rec,
    )

    session_id = "sess-card739-sdlc"
    token = _tool_context.set({"agent_id": "autoreiv", "session_id": session_id})
    try:
        # 1. Create a fresh project via create_project: should auto-select and have a valid root commit on main
        created = svc.create_project("dogfood-calc", name="Dogfood Calc")
        assert created["success"] is True, created
        assert svc.get_selected().get("slug") == "dogfood-calc"
        proj_dir = Path(created["path"])
        assert sorted(p.name for p in proj_dir.iterdir()) == [".git"]

        # 2. Branch immediately from fresh main before any files exist
        branch_res = git_tools.git_create_branch(name="feat/card-1-calc-multiply")
        assert branch_res["success"] is True, branch_res
        assert branch_res["branch"] == "feat/card-1-calc-multiply"

        # 3. Write card without an explicit status: line (defaults to Proposed)
        card_res = card_tools.write_card(
            title="Implement calc.multiply",
            content=(
                "# CARD-1 Implement calc.multiply\n\n"
                "## Problem\nNeed a multiply(a, b) helper with unit check.\n\n"
                "## Acceptance Criteria\n- [ ] calc.multiply(6, 7) == 42\n"
            ),
        )
        assert card_res["success"] is True, card_res
        assert card_res["status"] == "Proposed"
        card_id = card_res["id"]

        # 4. AutoReiv moves Proposed -> In Progress directly while working the card
        ip_res = card_tools.set_card_status(card_id=card_id, status="In Progress")
        assert ip_res["success"] is True, ip_res
        assert ip_res["status"] == "In Progress"

        # 5. Write AGENTS.md with Checks and calc.py implementation, commit, and run checks
        py_cmd = f"{Path(sys.executable).as_posix()} -c \"import calc; assert calc.multiply(6, 7) == 42\""
        assert file_tools.write_project_file(
            path="AGENTS.md",
            content=f"# AGENTS.md\n\n## Checks\n- fast: {py_cmd}\n\n## Branches\n- Base branch: main\n",
        )["success"] is True
        assert file_tools.write_project_file(
            path="calc.py",
            content="def multiply(a: int, b: int) -> int:\n    return a * b\n",
        )["success"] is True

        commit_res = git_tools.git_commit(
            subject="feat(calc): add multiply helper and AGENTS checks",
            paths=["AGENTS.md", "calc.py"],
        )
        assert commit_res["success"] is True, commit_res

        checks_res = dev_tools.run_project_checks()
        assert checks_res["success"] is True, checks_res
        assert checks_res["passed"] is True, checks_res

        # 6. Transition In Progress -> In Review, then review_card -> finish_review(Done)
        ir_res = card_tools.set_card_status(card_id=card_id, status="In Review")
        assert ir_res["success"] is True, ir_res
        assert ir_res["status"] == "In Review"

        packet = review_tools.review_card(card_id=card_id)
        assert "=== Review packet: CARD-1" in packet
        assert "passed - green recorded" in packet
        assert "calc.py" in packet

        verdict = review_tools.finish_review(
            card_id=card_id,
            verdict="Done",
            review="- [x] calc.multiply(6, 7) == 42 verified in calc.py and green run_project_checks",
        )
        assert "=== Review Done: CARD-1" in verdict
        assert card_tools.read_card(card_id)["status"] == "Done"
    finally:
        _tool_context.reset(token)
        clear_session_skill_activations(session_id)


def test_tutor_multi_turn_study_and_progressive_reference_dogfood(tmp_path: Path) -> None:
    """Tutor loads progressive references, extracts & grades recall, and matches slug vs title topic in progress."""
    data_dir = tmp_path / "data"
    wiki_root = data_dir / "wiki"
    wiki_root.mkdir(parents=True, exist_ok=True)

    repo = AgentMemoryRepository(agent_id="tutor", data_dir=data_dir)
    repo.initialize_schema()
    wiki_tools = WikiTools(wiki_root=wiki_root)
    edu_tools = EducationTools(data_dir=data_dir, wiki_root=wiki_root, repository=repo, default_agent_id="tutor")
    skill_tools = UserSkillCatalog()

    session_id = "sess-card739-tutor"
    token = _tool_context.set({"agent_id": "tutor", "session_id": session_id, "allowed_skill": ["*"]})
    try:
        # 1. Start a course with slug topic_id="distributed-consensus"
        course = start_or_resume_course(repo, topic_id="distributed-consensus")
        assert course["topic_id"] == "distributed-consensus"

        # 2. Load consolidated progressive references via skill_view
        priming_ref = skill_tools.skill_view(
            skill_id="socratic-tutoring",
            reference="priming-and-construction.md",
        )
        assert priming_ref["success"] is True
        assert "Priming" in priming_ref["content"]

        rubric_ref = skill_tools.skill_view(
            skill_id="quiz-turn",
            reference="grading-rubric.md",
        )
        assert rubric_ref["success"] is True
        assert "education_quiz_grade" in rubric_ref["content"]

        # Policy gate unlocks wiki_note_* for socratic-tutoring
        unlocked = expand_education_wiki_note_tools(["skill.socratic-tutoring"])
        assert "wiki_note_create" in unlocked
        assert "wiki_overview" not in unlocked

        # 3. Create a study note titled "Distributed Consensus" and extract + grade a quiz item
        note_res = wiki_tools.wiki_note_create(
            title="Distributed Consensus",
            content=(
                "# Distributed Consensus\n\n"
                "- **Quorum**: Majority of nodes required to agree on a proposed state transition.\n\n"
                "## Quiz\n"
                "- Q: What term describes the majority of nodes required to agree on a state transition?\n"
                "  A: quorum\n"
            ),
        )
        assert note_res["success"] is True, note_res

        ext_res = edu_tools.education_quiz_extract(
            wiki_path=note_res["path"],
            topic="Distributed Consensus",
            persist=True,
        )
        assert ext_res["success"] is True, ext_res
        assert ext_res["count"] >= 1
        item_id = ext_res["items"][0]["item_id"]

        grade_res = edu_tools.education_quiz_grade(item_id=item_id, answer="quorum")
        assert grade_res["success"] is True, grade_res
        assert grade_res["correct"] is True
        assert grade_res["grade"] == "pass"

        # 4. Query progress summary using the course's slug topic_id ("distributed-consensus"):
        # must match the "Distributed Consensus" mastery item and report 100.0% mastery!
        prog = edu_tools.education_progress_summary(topic_id="distributed-consensus")
        assert prog["success"] is True, prog
        assert prog["mastery"]["item_count"] >= 1
        assert prog["mastery"]["pass_count"] >= 1
        assert prog["mastery"]["mastery_pct"] == 100.0

        # Negative assertion: an unrelated topic still reports 0 scoped items and mastery_pct=None
        unrelated = edu_tools.education_progress_mastery(topic="linear-algebra")
        assert unrelated["success"] is True
        assert unrelated["item_count"] == 0
        assert unrelated["mastery_pct"] is None
    finally:
        _tool_context.reset(token)
        clear_session_skill_activations(session_id)
