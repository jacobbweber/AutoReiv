"""Education Wiki Template Catalog and Enforcement [CARD-322].

Enforces structured Wiki templates across all Education Learning OS artifacts
(priming, dual coding, elaboration, quizzes, flashcards, labs, scores).
Rejects freeform dumps into the Wiki that lack authorized template IDs and front matter.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class EducationTemplateRequiredError(ValueError):
    """Raised when an Education artifact attempts to bypass template enforcement."""


EDUCATION_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "education-priming": {
        "slug": "education-priming",
        "title": "Education Priming & Schema Blueprint",
        "description": "Schema, prerequisites, learning goals, and mental model anchors before detailed learning.",
        "filename": "education-priming.md",
        "document_type": "template",
        "tags": ["education", "priming", "schema", "template"],
        "content": (
            "---\n"
            "uid: \"YYYYMMDD-HHMMSS\"\n"
            "title: \"Education Priming & Schema Blueprint\"\n"
            "document_type: \"template\"\n"
            "domain: \"education\"\n"
            "topic: \"priming\"\n"
            "tags: [\"education\", \"priming\", \"schema\", \"template\"]\n"
            "template: \"education-priming\"\n"
            "summary: \"Schema, prerequisites, learning goals, and mental model anchors before detailed learning.\"\n"
            "status: \"template\"\n"
            "priority: \"medium\"\n"
            "schema_version: \"1.0\"\n"
            "---\n\n"
            "# Priming: ${TITLE}\n\n"
            "> **Topic:** [Target Concept / Topic]\n"
            "> **Pedagogy Phase:** Priming (Schema First)\n\n"
            "---\n\n"
            "## 1. Schema & Mental Model Blueprint\n"
            "[High-level framing, architecture, and core invariant]\n\n"
            "## 2. Prerequisites & Assumptions\n"
            "- [Prerequisite 1]\n"
            "- [Prerequisite 2]\n\n"
            "## 3. Learning Goals\n"
            "- [Goal 1]\n"
            "- [Goal 2]\n\n"
            "## 4. Initial Verification Quiz\n"
            "Q: [Foundational question checking schema retention]?\n"
            "A: [Expected answer]\n"
        ),
    },
    "education-dual-coding": {
        "slug": "education-dual-coding",
        "title": "Education Dual Coding (Prose + Visual Map)",
        "description": "Verbal concept explanation paired with structured Mermaid diagram for dual-channel cognitive encoding.",
        "filename": "education-dual-coding.md",
        "document_type": "template",
        "tags": ["education", "dual_coding", "mermaid", "template"],
        "content": (
            "---\n"
            "uid: \"YYYYMMDD-HHMMSS\"\n"
            "title: \"Education Dual Coding (Prose + Visual Map)\"\n"
            "document_type: \"template\"\n"
            "domain: \"education\"\n"
            "topic: \"dual_coding\"\n"
            "tags: [\"education\", \"dual_coding\", \"mermaid\", \"template\"]\n"
            "template: \"education-dual-coding\"\n"
            "summary: \"Verbal concept explanation paired with structured Mermaid diagram for dual-channel cognitive encoding.\"\n"
            "status: \"template\"\n"
            "priority: \"medium\"\n"
            "schema_version: \"1.0\"\n"
            "---\n\n"
            "# Dual Coding: ${TITLE}\n\n"
            "> **Topic:** [Target Concept / Topic]\n"
            "> **Pedagogy Phase:** Dual Coding (Paivio Paired Code)\n\n"
            "---\n\n"
            "## 1. Verbal Code (Concept Prose)\n"
            "[Clear prose explanation establishing core definitions and causal flows]\n\n"
            "## 2. Visual Code (Mermaid Relational Diagram)\n"
            "```mermaid\n"
            "flowchart TD\n"
            "    A[Core Concept] --> B[Components & Invariants]\n"
            "    B --> C[Execution & State Flow]\n"
            "    C --> D[Verified Outcome]\n"
            "```\n\n"
            "## 3. Step-through Mapping\n"
            "1. Grasp the verbal definition\n"
            "2. Trace decision paths through the diagram\n"
            "3. Synthesize both representations into durable mental models\n\n"
            "## 4. Verification Quiz\n"
            "Q: What are the two representations used in Dual Coding for ${TITLE}?\n"
            "A: verbal prose and visual diagrams\n"
        ),
    },
    "education-elaboration": {
        "slug": "education-elaboration",
        "title": "Education Elaboration & Conceptual Interrogation",
        "description": "Socratic probing questions, mechanistic walkthrough, analogies, and boundary edge cases.",
        "filename": "education-elaboration.md",
        "document_type": "template",
        "tags": ["education", "elaboration", "feynman", "template"],
        "content": (
            "---\n"
            "uid: \"YYYYMMDD-HHMMSS\"\n"
            "title: \"Education Elaboration & Conceptual Interrogation\"\n"
            "document_type: \"template\"\n"
            "domain: \"education\"\n"
            "topic: \"elaboration\"\n"
            "tags: [\"education\", \"elaboration\", \"feynman\", \"template\"]\n"
            "template: \"education-elaboration\"\n"
            "summary: \"Socratic probing questions, mechanistic walkthrough, analogies, and boundary edge cases.\"\n"
            "status: \"template\"\n"
            "priority: \"medium\"\n"
            "schema_version: \"1.0\"\n"
            "---\n\n"
            "# Elaboration: ${TITLE}\n\n"
            "> **Topic:** [Target Concept / Topic]\n"
            "> **Pedagogy Phase:** Elaboration (Mechanistic Interrogation)\n\n"
            "---\n\n"
            "## 1. Deep Mechanism\n"
            "[Why does this work the way it does? What underlying principles govern its behavior?]\n\n"
            "## 2. Analogies & Non-Examples\n"
            "- **Analogy:** [Real-world parallel]\n"
            "- **Non-Example:** [What looks like this concept but violates its core invariant]\n\n"
            "## 3. Probing Interrogations\n"
            "- What breaks if [invariant X] is violated?\n"
            "- How does this compare to [alternative approach Y]?\n\n"
            "## 4. Edge Cases & Failure Modes\n"
            "- [Failure scenario 1 and recovery strategy]\n"
        ),
    },
    "education-quiz": {
        "slug": "education-quiz",
        "title": "Education Retrieval Quiz Arena",
        "description": "Active retrieval questions with external binary verification criteria and mastery anchors.",
        "filename": "education-quiz.md",
        "document_type": "template",
        "tags": ["education", "quiz", "retrieval", "template"],
        "content": (
            "---\n"
            "uid: \"YYYYMMDD-HHMMSS\"\n"
            "title: \"Education Retrieval Quiz Arena\"\n"
            "document_type: \"template\"\n"
            "domain: \"education\"\n"
            "topic: \"retrieval\"\n"
            "tags: [\"education\", \"quiz\", \"retrieval\", \"template\"]\n"
            "template: \"education-quiz\"\n"
            "summary: \"Active retrieval questions with external binary verification criteria and mastery anchors.\"\n"
            "status: \"template\"\n"
            "priority: \"medium\"\n"
            "schema_version: \"1.0\"\n"
            "---\n\n"
            "# Quiz: ${TITLE}\n\n"
            "> **Topic:** [Target Concept / Topic]\n"
            "> **Pedagogy Phase:** Retrieval Practice (Active Recall)\n\n"
            "---\n\n"
            "## 1. Active Recall Questions\n"
            "### Item 1\n"
            "- **Prompt:** [Exact question prompt]\n"
            "- **Expected Binary Answer:** [Authoritative answer]\n"
            "- **Mastery Item ID:** [edu_item_id]\n\n"
            "### Item 2\n"
            "- **Prompt:** [Exact question prompt]\n"
            "- **Expected Binary Answer:** [Authoritative answer]\n"
            "- **Mastery Item ID:** [edu_item_id]\n"
        ),
    },
    "education-flashcard": {
        "slug": "education-flashcard",
        "title": "Education Spaced Flashcard",
        "description": "Single-concept prompt/recall card with Leitner/SRS interval schedule and learner fact binding.",
        "filename": "education-flashcard.md",
        "document_type": "template",
        "tags": ["education", "flashcard", "srs", "template"],
        "content": (
            "---\n"
            "uid: \"YYYYMMDD-HHMMSS\"\n"
            "title: \"Education Spaced Flashcard\"\n"
            "document_type: \"template\"\n"
            "domain: \"education\"\n"
            "topic: \"retrieval\"\n"
            "tags: [\"education\", \"flashcard\", \"srs\", \"template\"]\n"
            "template: \"education-flashcard\"\n"
            "summary: \"Single-concept prompt/recall card with Leitner/SRS interval schedule and learner fact binding.\"\n"
            "status: \"template\"\n"
            "priority: \"medium\"\n"
            "schema_version: \"1.0\"\n"
            "---\n\n"
            "# Flashcard: ${TITLE}\n\n"
            "## Front (Prompt)\n"
            "[Question or stimulus prompt]\n\n"
            "## Back (Recall Target)\n"
            "[Concise, unambiguous target answer]\n\n"
            "## Ledger Metadata\n"
            "- **Item ID:** [course_topic_item]\n"
            "- **Interval Stage:** [0 / 1 / 2 / 3]\n"
            "- **Next Due:** [YYYY-MM-DDTHH:MM:SSZ]\n"
        ),
    },
    "education-lab": {
        "slug": "education-lab",
        "title": "Education Construction & Application Lab",
        "description": "Generative exercise or coding lab with concrete invariants, test commands, and verification receipt.",
        "filename": "education-lab.md",
        "document_type": "template",
        "tags": ["education", "lab", "application", "exercise", "template"],
        "content": (
            "---\n"
            "uid: \"YYYYMMDD-HHMMSS\"\n"
            "title: \"Education Construction & Application Lab\"\n"
            "document_type: \"template\"\n"
            "domain: \"education\"\n"
            "topic: \"application\"\n"
            "tags: [\"education\", \"lab\", \"application\", \"exercise\", \"template\"]\n"
            "template: \"education-lab\"\n"
            "summary: \"Generative exercise or coding lab with concrete invariants, test commands, and verification receipt.\"\n"
            "status: \"template\"\n"
            "priority: \"medium\"\n"
            "schema_version: \"1.0\"\n"
            "---\n\n"
            "# Lab: ${TITLE}\n\n"
            "> **Topic:** [Target Concept / Topic]\n"
            "> **Pedagogy Phase:** Construction / Application\n\n"
            "---\n\n"
            "## 1. Objective & Invariants\n"
            "[What must be constructed or solved, and what invariants must hold true]\n\n"
            "## 2. Hands-on Tasks\n"
            "1. [Task 1]\n"
            "2. [Task 2]\n\n"
            "## 3. Verification Criteria\n"
            "- Test command: `[pytest / npm test ...]`\n"
            "- Expected outcome: [Pass condition]\n\n"
            "## 4. Verification Receipt\n"
            "- **Status:** [Pending / Passed / Failed]\n"
            "- **Job ID:** [standing_job_id]\n"
        ),
    },
    "education-score": {
        "slug": "education-score",
        "title": "Education Mastery Ledger Scorecard",
        "description": "Topic mastery summary, pass/miss records, metacognitive error patterns, and retention schedule.",
        "filename": "education-score.md",
        "document_type": "template",
        "tags": ["education", "score", "mastery", "ledger", "template"],
        "content": (
            "---\n"
            "uid: \"YYYYMMDD-HHMMSS\"\n"
            "title: \"Education Mastery Ledger Scorecard\"\n"
            "document_type: \"template\"\n"
            "domain: \"education\"\n"
            "topic: \"analysis\"\n"
            "tags: [\"education\", \"score\", \"mastery\", \"ledger\", \"template\"]\n"
            "template: \"education-score\"\n"
            "summary: \"Topic mastery summary, pass/miss records, metacognitive error patterns, and retention schedule.\"\n"
            "status: \"template\"\n"
            "priority: \"medium\"\n"
            "schema_version: \"1.0\"\n"
            "---\n\n"
            "# Scorecard: ${TITLE}\n\n"
            "> **Topic:** [Target Concept / Topic]\n"
            "> **Pedagogy Phase:** Analysis & Metacognitive Review\n\n"
            "---\n\n"
            "## 1. Mastery Status\n"
            "- **Current Step:** [current_step]\n"
            "- **Mastery Items Count:** [count]\n"
            "- **Pass Rate:** [%]\n\n"
            "## 2. Weakness & Error Patterns\n"
            "- [Identified error pattern 1]\n"
            "- [Identified error pattern 2]\n\n"
            "## 3. Retention Routine Next Due\n"
            "- Scheduled date: [timestamp]\n"
        ),
    },
    "education-portfolio": {
        "slug": "education-portfolio",
        "title": "Education Growth Portfolio & Depth Trajectory",
        "description": "Topic mastery progression, depth ladder level, milestone proofs, and growth trajectory.",
        "filename": "education-portfolio.md",
        "document_type": "template",
        "tags": ["education", "portfolio", "growth", "mastery", "template"],
        "content": (
            "---\n"
            "uid: \"YYYYMMDD-HHMMSS\"\n"
            "title: \"Education Growth Portfolio & Depth Trajectory\"\n"
            "document_type: \"template\"\n"
            "domain: \"education\"\n"
            "topic: \"portfolio\"\n"
            "tags: [\"education\", \"portfolio\", \"growth\", \"mastery\", \"template\"]\n"
            "template: \"education-portfolio\"\n"
            "summary: \"Topic mastery progression, depth ladder level, milestone proofs, and growth trajectory.\"\n"
            "status: \"template\"\n"
            "priority: \"medium\"\n"
            "schema_version: \"1.0\"\n"
            "---\n\n"
            "# Growth Portfolio: ${TITLE}\n\n"
            "> **Topic:** [Target Concept / Topic]\n"
            "> **Pedagogy Phase:** Growth Portfolio & Adaptive Depth\n\n"
            "---\n\n"
            "## 1. Mastery Level & Academic Ladder\n"
            "- **Level:** [Level Index]\n"
            "- **Rank:** [Academic Rank]\n"
            "- **Label:** [Level Name]\n"
            "- **Progress to Next Milestone:** [Progress %]\n\n"
            "## 2. Mastery Statistics & Receipts\n"
            "- **Total Ledger Items:** [count]\n"
            "- **Passed Items:** [passed_count]\n"
            "- **Pass Rate:** [pass_rate]%\n"
            "- **Active Miss Reasons:** [reasons]\n\n"
            "## 3. Milestones & Growth Trajectory\n"
            "- **Current Capabilities:** [Summary of verified invariants and abilities]\n"
            "- **Next Milestone Goal:** [Specific requirements for next rung]\n"
        ),
    },
}

STEP_TO_TEMPLATE_MAP: Dict[str, str] = {
    "priming": "education-priming",
    "dual_coding": "education-dual-coding",
    "dual-coding": "education-dual-coding",
    "retrieval": "education-quiz",
    "quiz": "education-quiz",
    "flashcard": "education-flashcard",
    "elaboration": "education-elaboration",
    "construction": "education-lab",
    "application": "education-lab",
    "lab": "education-lab",
    "analysis": "education-score",
    "score": "education-score",
    "environment": "education-priming",
    "amplifiers": "education-dual-coding",
    "retention": "education-quiz",
    "portfolio": "education-portfolio",
    "growth": "education-portfolio",
}


def list_education_templates() -> List[Dict[str, Any]]:
    """Return all registered Education templates."""
    return list(EDUCATION_TEMPLATES.values())


def get_education_template(template_id: str) -> Optional[Dict[str, Any]]:
    """Get an education template by slug/id."""
    clean_id = (template_id or "").strip().lower().replace("_", "-").replace(".md", "")
    return EDUCATION_TEMPLATES.get(clean_id)


def get_template_for_step(step_name: str) -> str:
    """Resolve the authoritative template slug for an education course step."""
    clean_step = (step_name or "").strip().lower().replace(" ", "_")
    return STEP_TO_TEMPLATE_MAP.get(clean_step, "education-priming")


def assert_education_template_required(template: Optional[str]) -> str:
    """Validate that template is specified and registered. Reject freeform dumps [REQ-EDU-WIKI-TPL-003]."""
    clean_id = (template or "").strip().lower().replace("_", "-").replace(".md", "")
    if not clean_id:
        raise EducationTemplateRequiredError("Education artifact write-back requires a valid template_id")
    if clean_id not in EDUCATION_TEMPLATES:
        raise EducationTemplateRequiredError(
            f"Unauthorized Education template: '{clean_id}'. Must be one of {sorted(EDUCATION_TEMPLATES.keys())}"
        )
    return clean_id
