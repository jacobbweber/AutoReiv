"""
Unit tests for Agent Training Factory Phase Prompt Registry [CARD-175].
Validates canonical default instructions, SQLite persistence, and override cascade.
"""

import sqlite3
from pathlib import Path

import pytest

from src.application.agent_training_factory.prompt_registry import (
    ALL_PHASE_IDS,
    PhasePromptRegistry,
    get_all_phase_instructions,
    get_phase_system_prompt,
    reset_phase_instruction,
    save_phase_instruction,
)


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    db_file = tmp_path / "test_autoreiv.db"
    conn = sqlite3.connect(str(db_file))
    conn.close()
    return db_file


def test_registry_defaults_and_metadata():
    """All 8 phases have default prompts, descriptions, and read-only context variables."""
    registry = PhasePromptRegistry()
    assert len(ALL_PHASE_IDS) == 8
    for phase_id in ALL_PHASE_IDS:
        meta = registry.get_phase_metadata(phase_id)
        assert meta is not None
        assert meta["id"] == phase_id
        assert len(meta["name"]) > 0
        assert len(meta["description"]) > 0
        assert len(meta["default_prompt"]) > 10
        assert isinstance(meta["context_variables"], list)
        assert len(meta["context_variables"]) > 0


def test_save_and_retrieve_custom_instruction(temp_db: Path):
    """Custom prompt persists and overrides default prompt."""
    custom = "You are an expert PowerShell author. Write modular, idempotent cmdlets."
    save_phase_instruction("author", custom, str(temp_db))

    prompt = get_phase_system_prompt("author", str(temp_db))
    assert prompt == custom

    # Unmodified phase still returns platform default
    distill_prompt = get_phase_system_prompt("intent_distill", str(temp_db))
    registry = PhasePromptRegistry()
    assert distill_prompt == registry.get_phase_metadata("intent_distill")["default_prompt"]


def test_get_all_phase_instructions_indicates_custom(temp_db: Path):
    """get_all_phase_instructions returns metadata with is_custom flag."""
    save_phase_instruction("blueprint", "Custom blueprint instructions", str(temp_db))

    all_phases = get_all_phase_instructions(str(temp_db))
    assert len(all_phases) == 8

    bp = next(p for p in all_phases if p["id"] == "blueprint")
    assert bp["is_custom"] is True
    assert bp["active_prompt"] == "Custom blueprint instructions"

    author = next(p for p in all_phases if p["id"] == "author")
    assert author["is_custom"] is False
    assert author["active_prompt"] == author["default_prompt"]


def test_reset_phase_instruction_restores_default(temp_db: Path):
    """Resetting a phase removes SQLite override and restores default."""
    save_phase_instruction("verify", "Strict verification", str(temp_db))
    assert get_phase_system_prompt("verify", str(temp_db)) == "Strict verification"

    reset_phase_instruction("verify", str(temp_db))
    registry = PhasePromptRegistry()
    assert get_phase_system_prompt("verify", str(temp_db)) == registry.get_phase_metadata("verify")["default_prompt"]
