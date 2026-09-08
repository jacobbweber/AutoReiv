"""
Agent Training Factory Phase Prompt Registry & SQLite Persistence [CARD-175].

Maintains canonical default system prompts, descriptions, and read-only context variables
for all 8 factory pipeline stages. Persists operator overrides to factory_phase_instructions.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any, Dict, List, Optional

from src.application.agent_training_factory.registry import (
    DEFAULT_PIPELINE,
    PHASE_AUTHOR,
    PHASE_BLUEPRINT,
    PHASE_GROUND,
    PHASE_INTENT_DISTILL,
    PHASE_OPTIMIZE,
    PHASE_PROMOTE,
    PHASE_SCENARIO_VERIFY,
    PHASE_VERIFY,
)

logger = logging.getLogger(__name__)

ALL_PHASE_IDS = list(DEFAULT_PIPELINE)

# Phase metadata: name, description, default prompt, and read-only context variables
PHASE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    PHASE_INTENT_DISTILL: {
        "id": PHASE_INTENT_DISTILL,
        "name": "1. Intent Distill",
        "description": "Distills high-level intent into structured answers and incorporates Reflexion lessons from prior runs.",
        "default_prompt": (
            "You are the Intent Distill phase of the Agent Training Factory. "
            "Produce structured answers to the question battery. Domain-agnostic. "
            "On outer rinse, incorporate Reflexion lessons and set shape_changed if skill/tool shape should change."
        ),
        "context_variables": [
            "{{target_agent_id}}",
            "{{seed_intent}}",
            "{{objectives}}",
            "{{failure_lessons}}",
            "{{questions}}",
        ],
    },
    PHASE_GROUND: {
        "id": PHASE_GROUND,
        "name": "2. Environment Ground",
        "description": "Probes the host OS, inspects available CLI tools, and qualifies cmdlet and tool namespaces.",
        "default_prompt": (
            "You are the Ground phase of the Agent Training Factory. "
            "Inspect the host environment, discover CLI tools and modules, and verify environmental prerequisites."
        ),
        "context_variables": [
            "{{target_agent_id}}",
            "{{os_family}}",
            "{{deliverable_type}}",
            "{{prerequisites}}",
            "{{constraints}}",
        ],
    },
    PHASE_BLUEPRINT: {
        "id": PHASE_BLUEPRINT,
        "name": "3. Capability Blueprint",
        "description": "Architects modular capability tools, parameters, and SKILL.md runbooks matching the operator's brief.",
        "default_prompt": (
            "You are the Blueprint phase of the Agent Training Factory. "
            "Design modular, high-cohesion capability tools and SKILL.md runbooks matching the operator intent. "
            "Enforce strict tool consolidation and anti-bloat standards."
        ),
        "context_variables": [
            "{{target_agent_id}}",
            "{{seed_intent}}",
            "{{objectives}}",
            "{{existing_pack}}",
            "{{grounding_facts}}",
        ],
    },
    PHASE_AUTHOR: {
        "id": PHASE_AUTHOR,
        "name": "4. Tool & Skill Author",
        "description": "Generates complete, runnable tool code, PowerShell scripts, and operating runbooks.",
        "default_prompt": (
            "You are the Author phase of the Agent Training Factory. "
            "Generate complete, production-ready, typed Python or PowerShell tool implementations and markdown runbooks. "
            "Require strict parameter validation, error handling, and security boundaries. Never omit code with placeholders."
        ),
        "context_variables": [
            "{{seed_brief}}",
            "{{operating_manual}}",
            "{{blueprint_tools}}",
            "{{scenarios}}",
            "{{rinse_feedback}}",
        ],
    },
    PHASE_SCENARIO_VERIFY: {
        "id": PHASE_SCENARIO_VERIFY,
        "name": "5. Scenario Verify",
        "description": "Generates realistic behavioral test scenarios and validates deliverables against end-to-end user journeys.",
        "default_prompt": (
            "You are the Scenario Verify phase of the Agent Training Factory. "
            "Evaluate whether the authored deliverables satisfy all end-to-end user scenarios and requirements. "
            "Identify missing edge cases, unexpected outputs, or requirement violations."
        ),
        "context_variables": [
            "{{seed_intent}}",
            "{{objectives}}",
            "{{authored_files}}",
            "{{scenarios}}",
        ],
    },
    PHASE_VERIFY: {
        "id": PHASE_VERIFY,
        "name": "6. Code Battery Verify",
        "description": "Executes 4-stage sandbox tests, syntax analysis, parameter typechecking, and execution idempotency.",
        "default_prompt": (
            "You are the Verify phase of the Agent Training Factory. "
            "Enforce strict sandbox safety, syntax validity, parameter typing, and execution idempotency. "
            "Report actionable failure classes and criticism notes when tests fail."
        ),
        "context_variables": [
            "{{tool_names}}",
            "{{sandbox_results}}",
            "{{syntax_errors}}",
            "{{test_output}}",
        ],
    },
    PHASE_OPTIMIZE: {
        "id": PHASE_OPTIMIZE,
        "name": "7. Refactor & Optimize",
        "description": "Refines code readability, eliminates redundancy, and polishes documentation without altering external behavior.",
        "default_prompt": (
            "You are the Optimize phase of the Agent Training Factory. "
            "Review validated code for readability, performance, concise docstrings, and documentation clarity "
            "without altering external behavior or introducing regressions."
        ),
        "context_variables": [
            "{{authored_files}}",
            "{{verification_summary}}",
        ],
    },
    PHASE_PROMOTE: {
        "id": PHASE_PROMOTE,
        "name": "8. Pack Promotion & HITL",
        "description": "Assembles the final agent pack manifest and stages capability deliverables for operator deployment approval.",
        "default_prompt": (
            "You are the Promote phase of the Agent Training Factory. "
            "Assemble the final agent pack manifest, verify schema version compliance, and stage the pack for operator deployment."
        ),
        "context_variables": [
            "{{target_agent_id}}",
            "{{deliverable_type}}",
            "{{pack_json}}",
            "{{tool_count}}",
        ],
    },
}


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS factory_phase_instructions (
            phase_id TEXT PRIMARY KEY,
            custom_prompt TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


class PhasePromptRegistry:
    """Registry managing canonical default prompts and descriptions."""

    def __init__(self) -> None:
        self._definitions = PHASE_DEFINITIONS

    def get_phase_metadata(self, phase_id: str) -> Optional[Dict[str, Any]]:
        return self._definitions.get(phase_id)

    def get_default_prompt(self, phase_id: str) -> str:
        meta = self.get_phase_metadata(phase_id)
        return meta["default_prompt"] if meta else ""


def get_phase_system_prompt(phase_id: str, db_path: Optional[str] = None) -> str:
    """
    Resolve the active system prompt for a phase.
    Returns custom prompt from SQLite if present; otherwise returns platform default.
    """
    registry = PhasePromptRegistry()
    default_prompt = registry.get_default_prompt(phase_id)

    if not db_path:
        return default_prompt

    try:
        conn = sqlite3.connect(db_path)
        try:
            _ensure_table(conn)
            cur = conn.cursor()
            cur.execute(
                "SELECT custom_prompt FROM factory_phase_instructions WHERE phase_id = ?",
                (phase_id,),
            )
            row = cur.fetchone()
            if row and row[0] and str(row[0]).strip():
                return str(row[0]).strip()
        finally:
            conn.close()
    except Exception as e:
        logger.warning("Failed to read custom prompt for phase '%s': %s", phase_id, e)

    return default_prompt


def get_all_phase_instructions(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Return metadata, defaults, active prompts, and is_custom status for all 8 phases.
    """
    registry = PhasePromptRegistry()
    custom_map: Dict[str, str] = {}

    if db_path:
        try:
            conn = sqlite3.connect(db_path)
            try:
                _ensure_table(conn)
                cur = conn.cursor()
                cur.execute("SELECT phase_id, custom_prompt FROM factory_phase_instructions")
                for pid, cp in cur.fetchall():
                    if cp and str(cp).strip():
                        custom_map[pid] = str(cp).strip()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("Failed to query factory_phase_instructions: %s", e)

    results: List[Dict[str, Any]] = []
    for phase_id in ALL_PHASE_IDS:
        meta = registry.get_phase_metadata(phase_id)
        if not meta:
            continue
        custom = custom_map.get(phase_id)
        is_custom = custom is not None and len(custom.strip()) > 0
        active_prompt = custom if is_custom else meta["default_prompt"]
        results.append(
            {
                "id": phase_id,
                "phase_id": phase_id,
                "name": meta["name"],
                "description": meta["description"],
                "default_prompt": meta["default_prompt"],
                "active_prompt": active_prompt,
                "prompt": active_prompt,
                "is_custom": is_custom,
                "context_variables": list(meta.get("context_variables", [])),
            }
        )

    return results


def save_phase_instruction(phase_id: str, custom_prompt: str, db_path: str) -> Dict[str, Any]:
    """
    Save custom prompt instructions for a phase in SQLite.
    """
    registry = PhasePromptRegistry()
    meta = registry.get_phase_metadata(phase_id)
    if not meta:
        raise ValueError(f"Unknown phase ID '{phase_id}'.")

    clean_prompt = str(custom_prompt or "").strip()
    if not clean_prompt:
        raise ValueError("Prompt instruction cannot be empty.")

    conn = sqlite3.connect(db_path)
    try:
        _ensure_table(conn)
        conn.execute(
            """
            INSERT INTO factory_phase_instructions (phase_id, custom_prompt, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(phase_id) DO UPDATE SET
                custom_prompt = excluded.custom_prompt,
                updated_at = CURRENT_TIMESTAMP
            """,
            (phase_id, clean_prompt),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "id": phase_id,
        "name": meta["name"],
        "description": meta["description"],
        "default_prompt": meta["default_prompt"],
        "active_prompt": clean_prompt,
        "is_custom": True,
        "context_variables": list(meta.get("context_variables", [])),
    }


def reset_phase_instruction(phase_id: str, db_path: str) -> Dict[str, Any]:
    """
    Delete custom prompt instructions for a phase, restoring platform default.
    """
    registry = PhasePromptRegistry()
    meta = registry.get_phase_metadata(phase_id)
    if not meta:
        raise ValueError(f"Unknown phase ID '{phase_id}'.")

    conn = sqlite3.connect(db_path)
    try:
        _ensure_table(conn)
        conn.execute(
            "DELETE FROM factory_phase_instructions WHERE phase_id = ?",
            (phase_id,),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "id": phase_id,
        "name": meta["name"],
        "description": meta["description"],
        "default_prompt": meta["default_prompt"],
        "active_prompt": meta["default_prompt"],
        "is_custom": False,
        "context_variables": list(meta.get("context_variables", [])),
    }
