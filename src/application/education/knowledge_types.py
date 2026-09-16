"""Education Knowledge-Type Anchors [CARD-334].

Provides specialized teaching artifact shapes for:
- concept (mental model, invariants, analogies, non-examples)
- tool (command/interface signature, flags, minimal invocation, idioms)
- method (procedural SOP, decision branches, verification checkpoint)
- problem (symptom signature, reproduction context, hypothesis space, remediation rubric)

Ensures course steps specialize by knowledge type rather than collapsing into
a generic step shape, while remaining strictly separate from CARD-324
Construction/Application graded lab pressure.
"""

from __future__ import annotations

from datetime import datetime, timezone
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
    "amplifiers": "concept",
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


def build_knowledge_artifact(
    topic: str,
    knowledge_type: str,
    custom_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a specialized teaching artifact dictionary for the given knowledge type."""
    clean_topic = (topic or "").strip()
    ktype = str(knowledge_type or "").strip().lower()
    if ktype not in VALID_KNOWLEDGE_TYPES:
        raise ValueError(
            f"Unknown knowledge_type '{knowledge_type}'. Must be one of {VALID_KNOWLEDGE_TYPES}"
        )

    meta = KNOWLEDGE_SHAPES[ktype]
    data = custom_data or {}
    sections: Dict[str, Any] = {}

    if ktype == "concept":
        sections = {
            "mental_model": data.get(
                "mental_model",
                f"The core conceptual model for {clean_topic} establishes its structural definitions, state guarantees, and foundational domain boundaries.",
            ),
            "invariants": data.get(
                "invariants",
                [
                    f"{clean_topic} invariants maintain strict determinism across state transitions.",
                    f"Operational guarantees of {clean_topic} must not be bypassed or mutated.",
                ],
            ),
            "analogy": data.get(
                "analogy",
                f"Like an immutable architectural contract, {clean_topic} guarantees consistent behavior regardless of caller context.",
            ),
            "non_example": data.get(
                "non_example",
                f"Ad-hoc or mutable side-channel behaviors that break {clean_topic} determinism are non-examples.",
            ),
            "boundary_conditions": data.get(
                "boundary_conditions",
                f"Applies to all structured workflows involving {clean_topic}; degrades if external unvalidated state intrudes.",
            ),
        }
    elif ktype == "tool":
        sections = {
            "interface_signature": data.get(
                "interface_signature",
                f"{clean_topic.lower().replace(' ', '_')}(target: str, options: dict = None) -> Result",
            ),
            "flags_and_arguments": data.get(
                "flags_and_arguments",
                [
                    "--strict: Enforce non-lenient parsing",
                    "--format=json: Output structured payload",
                    "--timeout=30: Bounded execution window",
                ],
            ),
            "minimal_invocation": data.get(
                "minimal_invocation",
                f"# Invoke {clean_topic}\nresult = execute_{clean_topic.lower().replace(' ', '_')}('sample_input')",
            ),
            "common_idioms": data.get(
                "common_idioms",
                [
                    "Always sanitize caller inputs prior to execution.",
                    "Capture structured receipts for auditability.",
                ],
            ),
            "failure_modes": data.get(
                "failure_modes",
                [
                    "Exit Code 1: Invalid input schema or missing parameters.",
                    "Exit Code 2: Target resource lock or timeout.",
                ],
            ),
        }
    elif ktype == "method":
        sections = {
            "prerequisites": data.get(
                "prerequisites",
                [
                    f"Verified clean workspace and active credentials for {clean_topic}.",
                    "System dependencies and input payloads initialized.",
                ],
            ),
            "procedure_steps": data.get(
                "procedure_steps",
                [
                    f"Step 1: Inspect environment and validate preconditions for {clean_topic}.",
                    f"Step 2: Execute primary transformation pipeline for {clean_topic}.",
                    "Step 3: Capture execution telemetry and compare with expected invariants.",
                ],
            ),
            "decision_branches": data.get(
                "decision_branches",
                [
                    "If precondition fails: Abort immediately and emit diagnostic error.",
                    "If invariant holds: Advance to verification checkpoint.",
                ],
            ),
            "verification_checkpoint": data.get(
                "verification_checkpoint",
                f"Execute deterministic check confirming {clean_topic} state matches target invariant.",
            ),
            "rollback_recipe": data.get(
                "rollback_recipe",
                "Revert state changes, restore prior baseline snapshot, and log diagnostic incident.",
            ),
        }
    elif ktype == "problem":
        sections = {
            "symptom_signature": data.get(
                "symptom_signature",
                f"Failure symptom observed in {clean_topic}: unexpected deviation from target invariant.",
            ),
            "reproduction_context": data.get(
                "reproduction_context",
                f"Triggered when {clean_topic} executes under concurrent or boundary load.",
            ),
            "hypothesis_space": data.get(
                "hypothesis_space",
                [
                    "Hypothesis A: Race condition or unvalidated state race.",
                    "Hypothesis B: Timeout or missing downstream dependency.",
                ],
            ),
            "diagnostic_tests": data.get(
                "diagnostic_tests",
                [
                    f"Run targeted probe: pytest tests/ -k '{clean_topic.lower().replace(' ', '_')}'",
                    "Inspect telemetry logs for non-zero exit codes.",
                ],
            ),
            "remediation_rubric": data.get(
                "remediation_rubric",
                "Apply atomic synchronization, verify invariant pass, and lock regression test.",
            ),
        }

    return {
        "topic": clean_topic,
        "knowledge_type": ktype,
        "shape_kind": meta["shape_kind"],
        "label": meta["label"],
        "template_slug": meta["template_slug"],
        "sections": sections,
        "tags": ["education", "knowledge_type", ktype],
        "title": f"{meta['label']}: {clean_topic}",
    }


def render_knowledge_note_markdown(
    artifact: Dict[str, Any],
    stamp: Optional[str] = None,
    template_slug: Optional[str] = None,
) -> str:
    """Render a knowledge artifact into markdown with authoritative front matter."""
    topic = artifact.get("topic", "")
    ktype = artifact.get("knowledge_type", "concept")
    shape_kind = artifact.get("shape_kind", "concept_brief")
    tpl_slug = template_slug or artifact.get("template_slug", f"education-{ktype}")
    title = artifact.get("title", f"Knowledge Anchor: {topic}")
    sections = artifact.get("sections", {})

    ts = stamp
    if not ts:
        base = datetime.now(timezone.utc)
        ts = base.strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        "---",
        f'uid: "{ts.replace("-", "").replace(":", "")}"',
        f'title: "{title}"',
        'document_type: "study_artifact"',
        'domain: "education"',
        f'topic: "{topic}"',
        f'knowledge_type: "{ktype}"',
        f'shape_kind: "{shape_kind}"',
        f'tags: ["education", "knowledge_type", "{ktype}"]',
        f'template: "{tpl_slug}"',
        f'summary: "Specialized {ktype} teaching artifact for {topic}"',
        'status: "active"',
        'priority: "medium"',
        'schema_version: "1.0"',
        "---",
        "",
        f"# {title}",
        "",
        f"> **Topic:** {topic}",
        f"> **Knowledge Anchor:** {ktype.title()} ({shape_kind})",
        "",
        "---",
        "",
    ]

    sec_idx = 1
    for sec_key, sec_val in sections.items():
        sec_title = sec_key.replace("_", " ").title()
        lines.append(f"## {sec_idx}. {sec_title}")
        if isinstance(sec_val, list):
            for item in sec_val:
                lines.append(f"- {item}")
        else:
            lines.append(str(sec_val))
        lines.append("")
        sec_idx += 1

    return "\n".join(lines).strip() + "\n"
