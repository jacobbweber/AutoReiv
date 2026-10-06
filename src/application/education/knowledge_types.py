"""Education Knowledge-Type Anchors [CARD-334].

Provides specialized teaching artifact shapes for:
- concept (mental model, invariants, analogies, non-examples)
- tool (command/interface signature, flags, minimal invocation, idioms)
- method (procedural SOP, decision branches, verification checkpoint)
- problem (symptom signature, reproduction context, hypothesis space, remediation rubric)

Course steps resolve a knowledge type for the course chrome. The template artifact
builder and its /api route were removed [CARD-652]: they filled every section with
the same text for every topic.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

VALID_KNOWLEDGE_TYPES: tuple[str, ...] = ("concept", "tool", "method", "problem")

KNOWLEDGE_SHAPES: Dict[str, Dict[str, Any]] = {
    "concept": {
        "shape_kind": "concept_brief",
        "label": "Concept Brief (Mental Model)",
        "template_slug": "education-concept",
        "required_sections": (
            "mental_model",
            "invariants",
            "analogy",
            "non_example",
            "boundary_conditions",
        ),
    },
    "tool": {
        "shape_kind": "tool_reference",
        "label": "Tool Reference (Interface Sheet)",
        "template_slug": "education-tool",
        "required_sections": (
            "interface_signature",
            "flags_and_arguments",
            "minimal_invocation",
            "common_idioms",
            "failure_modes",
        ),
    },
    "method": {
        "shape_kind": "method_runbook",
        "label": "Method Runbook (Procedural Recipe)",
        "template_slug": "education-method",
        "required_sections": (
            "prerequisites",
            "procedure_steps",
            "decision_branches",
            "verification_checkpoint",
            "rollback_recipe",
        ),
    },
    "problem": {
        "shape_kind": "problem_scenario",
        "label": "Problem Scenario (Diagnostic Lab)",
        "template_slug": "education-problem",
        "required_sections": (
            "symptom_signature",
            "reproduction_context",
            "hypothesis_space",
            "diagnostic_tests",
            "remediation_rubric",
        ),
    },
}

DEFAULT_STEP_KNOWLEDGE_MAP: Dict[str, str] = {
    "priming": "concept",
    "dual_coding": "concept",
    "dual-coding": "concept",
    "retrieval": "concept",
    "quiz": "concept",
    "flashcard": "concept",
    "elaboration": "method",
    "construction": "tool",
    "application": "problem",
    "analysis": "method",
    "environment": "tool",
    "retention": "problem",
    "portfolio": "concept",
    "custom": "concept",
}


def resolve_step_knowledge_type(step: str, explicit: Optional[str] = None) -> str:
    """Resolve knowledge type for a course step, honoring explicit override."""
    if explicit is not None:
        clean_exp = str(explicit).strip().lower()
        if clean_exp not in VALID_KNOWLEDGE_TYPES:
            raise ValueError(
                f"Invalid knowledge_type '{explicit}'. Must be one of {VALID_KNOWLEDGE_TYPES}"
            )
        return clean_exp
    clean_step = str(step or "").strip().lower().replace(" ", "_").replace("-", "_")
    return DEFAULT_STEP_KNOWLEDGE_MAP.get(clean_step, "concept")
