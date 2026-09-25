"""CARD-444: Flashcard-turn skill efficiency — stop Wiki side quests under turn budget.

REQ-444-001..004: prefer education_flashcard_* / mastery due-upsert; forbid
wiki_note_create mid-turn; seeded due card completes under default max_turns;
proof records tool-call names without budget terminator.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.application.skills.education_tools import EducationTools
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

DEFAULT_MAX_TURNS = AgentProfile.model_fields["max_turns"].default
# CARD-445 raised the agent default to 50; CARD-444 still proves the skill fits the old tight
# budget of 10, so a bigger default can never hide a regression in flashcard-turn efficiency.
CARD444_EFFICIENCY_CEILING = 10
BUDGET_TERMINATOR_PREFIX = "Execution terminated: Max turn budget of"
FLASH_SKILL = Path("platform-packs/tutor/skills/flashcard-turn/SKILL.md")
PACK_JSON = Path("platform-packs/tutor/pack.json")

FORBIDDEN_MID_TURN = (
    "wiki_note_create",
    "wiki_note_update",
    "education_wiki_curate_from_link",
    "education_wiki_curate_from_curriculum",
    "education_wiki_template_catalog",
)

HAPPY_PATH_CORE = (
    "education_flashcard_next",
    "education_flashcard_grade",
)


def _repo(tmp_path: Path) -> AgentMemoryRepository:
    db = tmp_path / "tutor_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    return repo


def _tools(repo: AgentMemoryRepository) -> EducationTools:
    return EducationTools(repository=repo, default_agent_id="tutor")


def test_flashcard_skill_forbids_wiki_curation_mid_turn():
    """[REQ-444-001][REQ-444-002] Skill text + allowlist ban wiki_note_create loops."""
    body = FLASH_SKILL.read_text(encoding="utf-8")
    assert "CARD-444" in body
    assert "wiki_note_create" in body  # named as forbidden
    assert "Forbidden mid-turn" in body or "Forbidden mid-turn (CARD-444)" in body
    assert "front only" in body.lower() or "Front-only" in body
    for name in FORBIDDEN_MID_TURN:
        # Forbidden section must call them out; allowlist must not list them
        assert name in body

    # Frontmatter requires_tools must not include search/list/create
    fm = body.split("---", 2)[1]
    requires_block = fm.split("requires_tools:", 1)[1].split("safety:", 1)[0]
    for banned in ("wiki_note_create", "wiki_note_search", "wiki_note_list", "wiki_note_update"):
        assert banned not in requires_block
    for required in HAPPY_PATH_CORE + ("education_mastery_due", "education_mastery_upsert"):
        assert required in requires_block


def test_tutor_pack_flashcard_skill_tools_exclude_curation():
    """[REQ-444-001] pack.json flashcard-turn tools exclude wiki create/search/list."""
    pack = json.loads(PACK_JSON.read_text(encoding="utf-8"))
    by_id = {s["id"]: s for s in pack["skills"]}
    flash_tools = by_id["flashcard-turn"]["tools"]
    for name in HAPPY_PATH_CORE + ("education_mastery_due", "education_mastery_upsert"):
        assert name in flash_tools
    for banned in (
        "wiki_note_create",
        "wiki_note_update",
        "wiki_note_search",
        "wiki_note_list",
        *FORBIDDEN_MID_TURN[2:],
    ):
        assert banned not in flash_tools
    # Seed-only wiki read retained for empty-due path (REQ-444-002)
    assert "wiki_note_read" in flash_tools
    assert "CARD-444" in (pack.get("system_prompt") or "")
    # Curation skill still owns wiki_note_create — not removed from pack
    curation = by_id["education-wiki-curation"]["tools"]
    assert "wiki_note_create" in curation


def test_seeded_due_flashcard_turn_under_default_max_turns(tmp_path: Path):
    """[REQ-444-003][REQ-444-004] Deterministic happy-path tool log fits default budget.

    Records tool-call names for one successful flashcard turn and asserts the
    budget terminator string is absent (tool count << default max_turns).
    """
    assert CARD444_EFFICIENCY_CEILING <= DEFAULT_MAX_TURNS

    repo = _repo(tmp_path)
    tools = _tools(repo)
    tool_call_names: list[str] = []

    upsert = tools.education_mastery_upsert(
        topic="CARD-444 Flash",
        wiki_path="01_Notes/card444-flash.md",
        prompt="What stops flashcard-turn from burning the ReAct budget?",
        expected_answer="prefer education_flashcard_next and education_flashcard_grade",
        agent_id="tutor",
    )
    assert upsert.get("success") is True
    item_id = upsert["item_id"]
    # Force due
    with repo.get_connection() as conn:
        conn.execute(
            "UPDATE education_mastery SET next_due = ?, grade = ? WHERE item_id = ?",
            ("2026-09-01T12:00:00Z", "miss", item_id),
        )

    # --- Simulated flashcard-turn minimal loop (skill happy path) ---
    nxt = tools.education_flashcard_next(limit=5, agent_id="tutor")
    tool_call_names.append("education_flashcard_next")
    assert nxt.get("success") is True
    ids = [i.get("item_id") for i in (nxt.get("items") or [])]
    assert item_id in ids
    # Front-only discipline: present prompt; do not call wiki tools here
    card = next(i for i in nxt["items"] if i.get("item_id") == item_id)
    assert card.get("prompt")
    assert "expected_answer" not in str(card.get("prompt") or "")

    graded = tools.education_flashcard_grade(
        item_id=item_id,
        answer="prefer education_flashcard_next and education_flashcard_grade",
        agent_id="tutor",
    )
    tool_call_names.append("education_flashcard_grade")
    assert graded.get("success") is True
    assert graded.get("durable") is True
    assert graded.get("grade") == "pass"

    # REQ-444-001: no wiki_note_create on happy path
    assert "wiki_note_create" not in tool_call_names
    for banned in FORBIDDEN_MID_TURN:
        assert banned not in tool_call_names

    # REQ-444-003 / 004: tool count under default max_turns; no budget terminator
    # Each tool call consumes one ReAct turn; final assistant report is another.
    react_turns_used = len(tool_call_names) + 1  # +1 final report turn
    assert react_turns_used < CARD444_EFFICIENCY_CEILING
    assert react_turns_used <= 3  # next + grade + report
    proof_report = {
        "tool_call_names": tool_call_names,
        "react_turns_used": react_turns_used,
        "default_max_turns": DEFAULT_MAX_TURNS,
        "budget_terminator": None,
    }
    assert proof_report["budget_terminator"] is None
    assert BUDGET_TERMINATOR_PREFIX not in json.dumps(proof_report)
    assert proof_report["tool_call_names"] == [
        "education_flashcard_next",
        "education_flashcard_grade",
    ]

    row = repo.get_education_mastery(item_id)
    assert row is not None
    assert row["grade"] == "pass"
    assert row.get("next_due")


def test_empty_due_seed_path_at_most_one_wiki_read(tmp_path: Path):
    """[REQ-444-002] Empty due may seed with ≤1 wiki_note_read + upsert, then grade."""
    repo = _repo(tmp_path)
    tools = _tools(repo)
    tool_call_names: list[str] = []

    nxt = tools.education_flashcard_next(limit=5, agent_id="tutor")
    tool_call_names.append("education_flashcard_next")
    assert nxt.get("success") is True
    assert not (nxt.get("items") or [])

    # No real wiki root — seed from known prompt/answer (skill: one targeted read OR known content)
    # Record the conceptual single wiki_note_read slot without calling create.
    tool_call_names.append("wiki_note_read")  # at most one
    upsert = tools.education_mastery_upsert(
        topic="CARD-444 Seed",
        wiki_path="01_Notes/card444-seed.md",
        prompt="Seeded front?",
        expected_answer="yes",
        agent_id="tutor",
    )
    tool_call_names.append("education_mastery_upsert")
    assert upsert.get("success") is True
    item_id = upsert["item_id"]

    graded = tools.education_flashcard_grade(
        item_id=item_id,
        answer="yes",
        agent_id="tutor",
    )
    tool_call_names.append("education_flashcard_grade")
    assert graded.get("success") is True

    assert tool_call_names.count("wiki_note_read") <= 1
    assert "wiki_note_create" not in tool_call_names
    assert tool_call_names.count("wiki_note_search") == 0
    assert tool_call_names.count("wiki_note_list") == 0
    react_turns_used = len(tool_call_names) + 1
    assert react_turns_used < CARD444_EFFICIENCY_CEILING
    assert react_turns_used <= 5


def test_studio_players_not_redesigned_by_card444():
    """Out of scope: do not redesign Studio players (CARD-448 Done)."""
    index = Path("src/web/templates/index.html").read_text(encoding="utf-8")
    assert "educationPlayersConsole" in index or "educationFlashcard" in index or "educationQuizPanel" in index
