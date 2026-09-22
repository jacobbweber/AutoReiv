"""
WikiStore Core Engine [REQ-WIKI-001, REQ-WIKI-003, REQ-WIKI-004].
Manages local-first plain-text markdown files under the Degree/Class taxonomy.
"""

from __future__ import annotations

import datetime as dt
import logging
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from .frontmatter import (
    FrontmatterParser,
    WikiInboxNoteMeta,
    WikiNoteMeta,
    clean_note_content,
    compute_content_hash,
    compute_context_tokens,
    compute_word_count,
)

log = logging.getLogger(__name__)

_LINK_PATTERN = re.compile(r"\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]")
_WORD_PATTERN = re.compile(r"[a-zA-Z0-9_]{3,}")
_SLUG_CLEAN_PATTERN = re.compile(r"[^a-zA-Z0-9_]+")



# Pre-CARD-406 scaffold seeded these empty taxonomy dirs under 01_Notes.
# CARD-416 scrubs them when empty; never reintroduce via mkdir lists.
_EMPTY_SEED_TAXONOMY_REL_PATHS: tuple[str, ...] = (
    "computer_science/artificial_intelligence",
    "general/notes",
    "operations/diagnostics",
    "operations/worklog",
    "systems_engineering/observability",
)


def slugify(text: str) -> str:
    """Convert text to clean snake_case filename slug."""
    s = text.strip().lower()
    s = _SLUG_CLEAN_PATTERN.sub("_", s).strip("_")
    return s[:80] or f"note_{int(dt.datetime.now().timestamp())}"


CORE_STRUCTURED_TEMPLATES: Dict[str, Dict[str, str]] = {
    "feynman-technique.md": {
        "title": "Feynman Technique Study Note",
        "summary": "Explaining complex concepts in plain language with analogies, concrete walkthroughs, and knowledge gap tracking.",
        "content": (
            "---\n"
            "uid: \"YYYYMMDD-HHMMSS\"\n"
            "title: \"Feynman Technique Study Note\"\n"
            "document_type: \"template\"\n"
            "domain: \"general\"\n"
            "topic: \"study\"\n"
            "tags: [\"feynman\", \"learning\", \"study\", \"template\"]\n"
            "summary: \"Explaining complex concepts in plain language with analogies, concrete walkthroughs, and knowledge gap tracking.\"\n"
            "status: \"template\"\n"
            "priority: \"medium\"\n"
            "sensitivity: \"internal\"\n"
            "confidence_score: 1.0\n"
            "schema_version: \"1.0\"\n"
            "---\n\n"
            "# ${TITLE}\n\n"
            "> **Concept / Topic:** [Name of the concept]\n"
            "> **Domain / Context:** [Subject or system]\n"
            "> **Iteration:** [1st / 2nd / 3rd — track revision cycles]\n\n"
            "---\n\n"
            "## Step 1: Teach It Simply\n\n"
            "*Explain the concept as if teaching someone with no background knowledge. Use plain language, real-world analogies, and concrete examples. Avoid unexplained jargon.*\n\n"
            "### Core Explanation\n"
            "[Write the core explanation here. Aim for clarity and intuition over dense formal definitions.]\n\n"
            "### Plain Analogy\n"
            "[A simple, memorable analogy that captures the essence of the concept. Example: 'DNS is like a phone book for the internet.']\n\n"
            "### Concrete Example\n"
            "[Walk through one specific, realistic example demonstrating the concept in action.]\n\n"
            "---\n\n"
            "## Step 2: Identify Gaps\n\n"
            "*Where did you hesitate, use vague language, hand-wave, or rely on buzzwords? These are the knowledge gaps to investigate.*\n\n"
            "| # | Knowledge Gap Description | Severity | Source to Review | Status |\n"
            "|---|---|---|---|---|\n"
            "| 1 | [Specific question or mechanism not fully understood] | [Critical / Moderate] | [Docs / Source code / RFC] | [Open / Resolved] |\n\n"
            "---\n\n"
            "## Step 3: Simplify and Refine\n\n"
            "*Clean up the explanation using the insights gained from filling the gaps above.*\n\n"
            "### Refined Takeaway\n"
            "[The final, clean explanation — free of jargon, logically ordered, and complete.]\n\n"
            "---\n\n"
            "## Step 4: Review Checklist\n\n"
            "- [ ] Can I explain this concept without looking at reference material?\n"
            "- [ ] Does my analogy hold up under scrutiny without creating false assumptions?\n"
            "- [ ] Are all key technical terms defined in simple terms?\n"
        ),
    },
    "concept-map-system-hub.md": {
        "title": "System Hub (Concept Map)",
        "summary": "Mapping system components, directional dependencies, feedback loops, and high-leverage intervention points with Mermaid.",
        "content": (
            "---\n"
            "uid: \"YYYYMMDD-HHMMSS\"\n"
            "title: \"System Hub (Concept Map)\"\n"
            "document_type: \"template\"\n"
            "domain: \"general\"\n"
            "topic: \"architecture\"\n"
            "tags: [\"concept_map\", \"systems\", \"architecture\", \"template\"]\n"
            "summary: \"Mapping system components, directional dependencies, feedback loops, and high-leverage intervention points with Mermaid.\"\n"
            "status: \"template\"\n"
            "priority: \"medium\"\n"
            "sensitivity: \"internal\"\n"
            "confidence_score: 1.0\n"
            "schema_version: \"1.0\"\n"
            "---\n\n"
            "# ${TITLE}\n\n"
            "> **System / Domain:** [Central system or topic being mapped]\n"
            "> **Purpose:** [What question, workflow, or architectural problem this map addresses]\n\n"
            "---\n\n"
            "## 1. Core Hub & Scope\n\n"
            "- **Core Hub:** [Describe the central component, pipeline, or system]\n"
            "- **System Boundary:** [What is explicitly in-scope vs. external/out-of-scope]\n\n"
            "---\n\n"
            "## 2. Components & Nodes\n\n"
            "| Node ID | Component Name | Type | Description | Status |\n"
            "|---|---|---|---|---|\n"
            "| A | [Component A] | [Input / Process / Output / Storage / Constraint] | [Brief description of role] | [Active / At Risk] |\n"
            "| B | [Component B] | [Input / Process / Output / Storage / Constraint] | [Brief description of role] | [Active / At Risk] |\n"
            "| C | [Component C] | [Input / Process / Output / Storage / Constraint] | [Brief description of role] | [Active / At Risk] |\n\n"
            "---\n\n"
            "## 3. Connections & Feedback Loops\n\n"
            "| From | To | Relationship Type | Description | Strength |\n"
            "|---|---|---|---|---|\n"
            "| [A] | [B] | [influences / triggers / depends on / enables / inhibits] | [How and why this connection exists] | [High / Med] |\n"
            "| [B] | [C] | [influences / triggers / depends on / enables / inhibits] | [Description] | [High / Med] |\n\n"
            "### Feedback Loops\n"
            "- **Loop 1:** [e.g. A → B → C → A (reinforcing or balancing loop)]\n\n"
            "---\n\n"
            "## 4. Visual Architecture Map (Mermaid)\n\n"
            "```mermaid\n"
            "graph TD\n"
            "    A[Component A] -->|triggers| B[Component B]\n"
            "    B -->|writes to| C[Component C]\n"
            "```\n\n"
            "---\n\n"
            "## 5. Leverage Points & Interventions\n\n"
            "*Where would a small change produce the greatest positive impact on the entire system?*\n\n"
            "| # | Leverage Point | Rationale | Proposed Intervention | Priority |\n"
            "|---|---|---|---|---|\n"
            "| 1 | [Node or Connection] | [Why changing this produces outsized results] | [Specific action to take] | [High / Med] |\n\n"
            "---\n\n"
            "## 6. Key Takeaways\n\n"
            "1. [Key takeaway 1]\n"
            "2. [Key takeaway 2]\n"
        ),
    },
    "dikw-pyramid-of-insight.md": {
        "title": "Pyramid of Insight (DIKW Framework)",
        "summary": "Progressive extraction of value: Data observations, Information patterns, Knowledge cause-and-effect, and Wisdom action plan.",
        "content": (
            "---\n"
            "uid: \"YYYYMMDD-HHMMSS\"\n"
            "title: \"Pyramid of Insight (DIKW Framework)\"\n"
            "document_type: \"template\"\n"
            "domain: \"general\"\n"
            "topic: \"analysis\"\n"
            "tags: [\"dikw\", \"analysis\", \"rca\", \"decision\", \"template\"]\n"
            "summary: \"Progressive extraction of value: Data observations, Information patterns, Knowledge cause-and-effect, and Wisdom action plan.\"\n"
            "status: \"template\"\n"
            "priority: \"medium\"\n"
            "sensitivity: \"internal\"\n"
            "confidence_score: 1.0\n"
            "schema_version: \"1.0\"\n"
            "---\n\n"
            "# ${TITLE}\n\n"
            "> **Subject:** [Topic, Incident, or Decision Area]\n"
            "> **Chain:** Data → Information → Knowledge → Wisdom\n\n"
            "---\n\n"
            "## 1. Data (Objective Observations)\n\n"
            "*Raw facts, metrics, and error logs collected without interpretation.*\n\n"
            "| Metric / Event | Value / Log Snippet | Timestamp / Range | Source |\n"
            "|---|---|---|---|\n"
            "| | | | |\n"
            "| | | | |\n\n"
            "---\n\n"
            "## 2. Information (Context & Patterns)\n\n"
            "*Data structured to answer: Who? What? Where? When?*\n\n"
            "- **Observed Trend:** [Pattern identified over time or across hosts/services]\n"
            "- **Comparative Baseline:** [How this compares to expected baseline or SLA]\n"
            "- **Key Findings:**\n"
            "  1. [Finding 1]\n"
            "  2. [Finding 2]\n\n"
            "---\n\n"
            "## 3. Knowledge (The Cause: Why & How)\n\n"
            "*Cause-and-effect hypothesis explaining the observed patterns.*\n\n"
            "> **Hypothesis:** [Underlying technical cause for the patterns identified above]\n\n"
            "- **Supporting Evidence:** [Evidence point 1]\n"
            "- **Technical & Operational Implication:** [What this means for the platform or workflow]\n"
            "- **Crucial Insight:**\n"
            "  - *We observed:* [Information-level fact]\n"
            "  - *Caused by:* [Knowledge-level root cause]\n"
            "  - *Therefore, we must:* [Leads to Wisdom action below]\n\n"
            "---\n\n"
            "## 4. Wisdom (Strategic Action Plan)\n\n"
            "*Applying knowledge to make sound technical and operational decisions.*\n\n"
            "| # | Action Item | Owner | Target Date | Priority |\n"
            "|---|---|---|---|---|\n"
            "| 1 | [Specific, measurable action to fix or improve] | [Owner] | [Date] | [High / Med] |\n"
            "| 2 | [Preventative safeguard or automated test] | [Owner] | [Date] | [High / Med] |\n\n"
            "### Verification & Success Criteria\n"
            "- [How will we prove this solved the issue?]\n"
        ),
    },
    "zettelkasten-atomic.md": {
        "title": "Zettelkasten (Atomic Note)",
        "summary": "Single atomic idea written in self-contained language with explicit bidirectional wikilinks.",
        "content": (
            "---\n"
            "uid: \"YYYYMMDD-HHMMSS\"\n"
            "title: \"Zettelkasten (Atomic Note)\"\n"
            "document_type: \"template\"\n"
            "domain: \"general\"\n"
            "topic: \"concepts\"\n"
            "tags: [\"zettelkasten\", \"atomic\", \"second_brain\", \"template\"]\n"
            "summary: \"Single atomic idea written in self-contained language with explicit bidirectional wikilinks.\"\n"
            "status: \"template\"\n"
            "priority: \"medium\"\n"
            "sensitivity: \"internal\"\n"
            "confidence_score: 1.0\n"
            "schema_version: \"1.0\"\n"
            "---\n\n"
            "# ${TITLE}\n\n"
            "> **Rule:** Exactly one core idea per note. The note must be understandable without consulting the original source.\n\n"
            "---\n\n"
            "## 1. The Core Idea\n\n"
            "[Explain the single idea here in your own words. Keep it clear, concise, and focused — typically 3 to 8 sentences.]\n\n"
            "---\n\n"
            "## 2. Context & Motivation\n\n"
            "[Brief background on why this idea matters or the context in which it arose.]\n\n"
            "---\n\n"
            "## 3. Relational Links (Wikilinks)\n\n"
            "*The value of an atomic note comes from its explicit connections to other notes.*\n\n"
            "- **Expands on:** [[Related Note Title]] — [Explain how it expands]\n"
            "- **Contradicts / Alternative to:** [[Alternative Approach]] — [Explain the trade-off]\n"
            "- **Concrete Example of:** [[Broader Concept]] — [Explain relationship]\n\n"
            "---\n\n"
            "## 4. Emerging Questions\n\n"
            "- [ ] [Unanswered question or new direction sparked by this note]\n"
            "- [ ] [Potential future atomic note topic]\n"
        ),
    },
    "sop-runbook.md": {
        "title": "Standard Operating Procedure (SOP / Runbook)",
        "summary": "Repeatable operational procedure with prerequisites, numbered execution steps, verification checks, and rollback.",
        "content": (
            "---\n"
            "uid: \"YYYYMMDD-HHMMSS\"\n"
            "title: \"Standard Operating Procedure (SOP / Runbook)\"\n"
            "document_type: \"template\"\n"
            "domain: \"operations\"\n"
            "topic: \"runbooks\"\n"
            "tags: [\"sop\", \"runbook\", \"operations\", \"procedures\", \"template\"]\n"
            "summary: \"Repeatable operational procedure with prerequisites, numbered execution steps, verification checks, and rollback.\"\n"
            "status: \"template\"\n"
            "priority: \"high\"\n"
            "sensitivity: \"internal\"\n"
            "confidence_score: 1.0\n"
            "schema_version: \"1.0\"\n"
            "---\n\n"
            "# ${TITLE}\n\n"
            "> **Objective:** [Clear, single-sentence goal of this procedure]\n"
            "> **Target System:** [Host, VM, cluster, or environment]\n"
            "> **Estimated Duration:** [e.g. 15 minutes]\n\n"
            "---\n\n"
            "## 1. Prerequisites & Safety Checks\n\n"
            "- [ ] [Required administrative permission or elevation]\n"
            "- [ ] [Backup or snapshot completed before proceeding]\n"
            "- [ ] [Network or dependency availability verified]\n\n"
            "---\n\n"
            "## 2. Step-by-Step Execution\n\n"
            "### Step 1: [First Action]\n"
            "[Description of action]\n"
            "```powershell\n"
            "# Exact command to execute\n"
            "Get-Service -Name \"ExampleService\"\n"
            "```\n"
            "*Expected Output:*\n"
            "```text\n"
            "Status: Running\n"
            "```\n\n"
            "### Step 2: [Second Action]\n"
            "[Description of action]\n"
            "```powershell\n"
            "# Command\n"
            "```\n\n"
            "---\n\n"
            "## 3. Verification & Acceptance Check\n\n"
            "*How to verify that the procedure succeeded without regressions:*\n\n"
            "```powershell\n"
            "# Verification command\n"
            "Test-NetConnection -Port 8000\n"
            "```\n"
            "- [ ] All health checks return healthy / HTTP 200.\n"
            "- [ ] Relevant services are running and listening.\n\n"
            "---\n\n"
            "## 4. Rollback Procedure\n\n"
            "*If any step fails or verification criteria are not met:*\n\n"
            "1. [Immediate step to halt execution]\n"
            "2. [Exact command to restore previous state or revert snapshot]\n"
            "```powershell\n"
            "# Rollback command\n"
            "```\n"
            "3. [Notification or incident log step]\n"
        ),
    },
    "adr-decision.md": {
        "title": "Architecture Decision Record (ADR / Trade-Off)",
        "summary": "Documenting architectural context, options considered, trade-offs, final decision, and blast radius.",
        "content": (
            "---\n"
            "uid: \"YYYYMMDD-HHMMSS\"\n"
            "title: \"Architecture Decision Record (ADR / Trade-Off)\"\n"
            "document_type: \"template\"\n"
            "domain: \"systems_engineering\"\n"
            "topic: \"architecture\"\n"
            "tags: [\"adr\", \"architecture\", \"decision\", \"trade_off\", \"template\"]\n"
            "summary: \"Documenting architectural context, options considered, trade-offs, final decision, and blast radius.\"\n"
            "status: \"template\"\n"
            "priority: \"high\"\n"
            "sensitivity: \"internal\"\n"
            "confidence_score: 1.0\n"
            "schema_version: \"1.0\"\n"
            "---\n\n"
            "# ${TITLE}\n\n"
            "> **Status:** [Proposed / Accepted / Superseded / Deprecated]\n"
            "> **Deciders:** [Names / Roles]\n"
            "> **Date:** [YYYY-MM-DD]\n\n"
            "---\n\n"
            "## 1. Context & Problem Statement\n\n"
            "[Describe the architectural context, constraints, and the problem being solved. What forces are driving this decision?]\n\n"
            "---\n\n"
            "## 2. Decision Drivers\n\n"
            "- [Driver 1: e.g. Local offline execution with zero cloud dependency]\n"
            "- [Driver 2: e.g. Predictable latency under 200ms]\n"
            "- [Driver 3: e.g. Maintainability and minimal external libraries]\n\n"
            "---\n\n"
            "## 3. Considered Options\n\n"
            "### Option A: [Option Name] (Chosen)\n"
            "- **Description:** [How it works]\n"
            "- **Pros:**\n"
            "  - [Advantage 1]\n"
            "  - [Advantage 2]\n"
            "- **Cons / Costs:**\n"
            "  - [Disadvantage 1]\n\n"
            "### Option B: [Alternative Option Name]\n"
            "- **Description:** [How it works]\n"
            "- **Pros:**\n"
            "  - [Advantage 1]\n"
            "- **Cons / Costs:**\n"
            "  - [Why it was rejected]\n\n"
            "---\n\n"
            "## 4. Decision Outcome\n\n"
            "**Chosen Option:** **Option A: [Option Name]**\n\n"
            "### Rationale\n"
            "[Explain why this option best satisfies the decision drivers over the alternatives.]\n\n"
            "---\n\n"
            "## 5. Consequences & Blast Radius\n\n"
            "### Positive Consequences\n"
            "- [Positive effect on system]\n\n"
            "### Negative Consequences / Trade-offs\n"
            "- [Trade-off accepted]\n\n"
            "### Blast Radius & Mitigation\n"
            "- **Affected Modules:** [List of components or services impacted]\n"
            "- **Mitigation Strategy:** [How risks are contained]\n"
        ),
    },
    "concept-comparison.md": {
        "title": "Concept Comparison & Distinction",
        "summary": "Comparative analysis separating structural fundamentals from superficial enhancements with side-by-side distinction tables, failure modes, and analogies.",
        "content": (
            "---\n"
            "uid: \"YYYYMMDD-HHMMSS\"\n"
            "title: \"Concept Comparison & Distinction\"\n"
            "document_type: \"template\"\n"
            "domain: \"general\"\n"
            "topic: \"concepts\"\n"
            "tags: [\"comparison\", \"distinction\", \"architecture\", \"concepts\", \"template\"]\n"
            "summary: \"Comparative analysis separating structural fundamentals from superficial enhancements with side-by-side distinction tables, failure modes, and analogies.\"\n"
            "status: \"template\"\n"
            "priority: \"medium\"\n"
            "sensitivity: \"internal\"\n"
            "confidence_score: 1.0\n"
            "schema_version: \"1.0\"\n"
            "---\n\n"
            "# ${TITLE}\n\n"
            "> **One-sentence version:** [High-level distinction summary contrasting the two concepts: concept A decides what exists and where; concept B decides how it looks and behaves.]\n\n"
            "---\n\n"
            "## 1. The Core Concepts, Precisely\n\n"
            "| Concept / Term | What It Means | Question It Answers |\n"
            "|---|---|---|\n"
            "| [Concept A] | [Definition of first concept] | \"[Key question answered by concept A]\" |\n"
            "| [Concept B] | [Definition of second concept] | \"[Key question answered by concept B]\" |\n\n"
            "*[Concept A] is upstream of [Concept B]. You design / establish [Concept A] first, then apply [Concept B] to express or enhance it.*\n\n"
            "---\n\n"
            "## 2. The Structural Layer: [Concept A Name]\n\n"
            "*[Describe the fundamental, architectural thinking behind Concept A: organizing content, sequence, logic, and operations.]*\n\n"
            "| Term / Mechanism | Meaning |\n"
            "|---|---|\n"
            "| [Term 1] | [Explanation] |\n"
            "| [Term 2] | [Explanation] |\n"
            "| [Term 3] | [Explanation] |\n\n"
            "> **Structural Test:** [How to verify Concept A is sound on its own without Concept B.]\n\n"
            "---\n\n"
            "## 3. The Enhancement Layer: [Concept B Name]\n\n"
            "*[Describe the visual, aesthetic, behavioral, or polish layer applied on top of Concept A.]*\n\n"
            "| Term / Mechanism | Meaning |\n"
            "|---|---|\n"
            "| [Term 1] | [Explanation] |\n"
            "| [Term 2] | [Explanation] |\n"
            "| [Term 3] | [Explanation] |\n\n"
            "> **Enhancement Test:** [How to verify Concept B is consistent, intentional, and well-executed.]\n\n"
            "---\n\n"
            "## 4. Side-by-Side Comparison\n\n"
            "| Dimension | [Concept A Name] | [Concept B Name] |\n"
            "|---|---|---|\n"
            "| **Decides** | [What exists, where, in what order] | [How it looks and feels] |\n"
            "| **Artifacts** | [Architecture maps, flows, wireframes] | [Style guides, tokens, components] |\n"
            "| **Failure Mode** | [User lost, flow broken, cannot complete task] | [Looks cheap, inconsistent, unpolished] |\n"
            "| **Fixable Later?** | [No / Expensive — restructuring requires rework] | [Yes / Cheap — reskinning is lightweight] |\n"
            "| **Thinking Type** | [\"Where does this go and how does it connect?\"] | [\"Make it clean, consistent, and measured\"] |\n\n"
            "---\n\n"
            "## 5. Rule of Thumb & Order of Work\n\n"
            "> **Rule of Thumb:** You can polish a broken structure, but no amount of polish makes a broken structure functional.\n"
            "> **Order of Work:** [Concept A Step 1] → [Concept A Step 2] → [Concept B Step 1] → [Concept B Step 2].\n\n"
            "---\n\n"
            "## 6. The Core Analogy\n\n"
            "*Building a house:* [Concept A] is the floor plan and plumbing — where rooms, doors, and pipes go. [Concept B] is the paint, trim, and fixtures. A beautiful paint job does not help if the bedroom has no door.\n"
        ),
    },
    "weekly_notes.md": {
        "title": "Weekly Work Log & Task Carry-Over",
        "summary": "Obsidian-compatible weekly work log with daily sections, carry-over tasks, and project goals.",
        "content": (
            "---\n"
            'title: "{{week_title}} ({{week}})"\n'
            "domain: weekly\n"
            "topic: worklog\n"
            "category: notes\n"
            "document_type: log\n"
            "status: active\n"
            "tags:\n"
            "  - worklog\n"
            "  - weekly_notes\n"
            'week: "{{week}}"\n'
            'date_start: "{{date_start}}"\n'
            'date_end: "{{date_end}}"\n'
            "---\n"
            "[[My Dashboard]]\n\n"
            "## Projects\n"
            "-\n\n"
            "---\n\n"
            "## {{week_title}} Summary\n\n"
            "### 🎯 Focusing\n"
            "-\n\n"
            "### ⚡ Ad-Hoc\n"
            "-\n\n"
            "### 🔄 Carry-Over\n"
            "{{carry_over_tasks}}\n\n"
            "### ✅ Done\n"
            "-\n\n"
            "---\n\n"
            "## 📅 Daily Work Logs\n\n"
            "### {{monday:dddd D}}\n"
            "-\n\n"
            "### {{tuesday:dddd D}}\n"
            "-\n\n"
            "### {{wednesday:dddd D}}\n"
            "-\n\n"
            "### {{thursday:dddd D}}\n"
            "-\n\n"
            "### {{friday:dddd D}}\n"
            "-\n\n"
            "### {{saturday:dddd D}}\n"
            "-\n\n"
            "### {{sunday:dddd D}}\n"
            "-\n"
        ),
    },
}

# Register Education Learning OS templates [CARD-322]
try:
    from src.application.education.templates import EDUCATION_TEMPLATES

    for t_id, t_meta in EDUCATION_TEMPLATES.items():
        CORE_STRUCTURED_TEMPLATES[t_meta["filename"]] = {
            "title": t_meta["title"],
            "summary": t_meta["description"],
            "content": t_meta["content"],
        }
except ImportError:
    pass


class WikiStore:
    """
    Core local-first document storage and indexing engine.
    """

    def __init__(self, root_dir: str | Path | None = None, auto_seed: bool = False):
        from src.infrastructure.data.resolver import LEGACY_WIKI_STRINGS, DataDirResolver

        if root_dir is None or str(root_dir).strip() in LEGACY_WIKI_STRINGS:
            self.root_dir = Path(DataDirResolver().resolve().wiki_path).resolve()
        else:
            self.root_dir = Path(root_dir).resolve()
        self.auto_seed = auto_seed

    def scaffold(self, seed_starter: Optional[bool] = None, auto_migrate: bool = True) -> None:
        """Ensure standard CARD-173 numbered taxonomy folders exist on disk and seed canonical assets."""
        from src.infrastructure.data.resolver import ensure_live_data_root
        ensure_live_data_root(self.root_dir)
        directories = [
            self.root_dir / "00_Inbox",
            self.root_dir / "01_Notes",
            self.root_dir / "02_Resources" / "operating_manuals",
            self.root_dir / "02_Resources" / "_Templates",
            self.root_dir / "03_Archive",
        ]
        for d in directories:
            d.mkdir(parents=True, exist_ok=True)
        # Do not mkdir domain/topic trees under 01_Notes (CARD-406/416).
        # Scrub leftover empty pre-CARD-406 seed taxonomy on every scaffold.
        self.scrub_empty_seed_taxonomy()

        # Check if legacy unnumbered directories exist, and auto-migrate them non-destructively
        if auto_migrate and any(
            (self.root_dir / p).exists()
            for p in ("inbox", "notes", "resources", "archive", "01_Projects", "02_Areas", "03_resources")
        ):
            self.migrate_legacy_vault(ensure_scaffold=False)

        # Ensure canonical Tag Authority exists
        tag_auth = self.root_dir / "02_Resources" / "_Templates" / "tag-authority.md"
        if not tag_auth.exists():
            tag_auth_content = (
                "---\n"
                "title: \"Wiki Tag Authority\"\n"
                "document_type: \"authority\"\n"
                "domain: \"general\"\n"
                "topic: \"templates\"\n"
                "status: \"active\"\n"
                "tags: [\"authority\", \"metadata\", \"taxonomy\"]\n"
                "---\n\n"
                "# Wiki Tag Authority\n\n"
                "Canonical registry of approved tags across domains. Check this list before adding new tags. If a novel concept is needed, register it here.\n\n"
                "## Domains & Approved Tags\n\n"
                "### systems_engineering\n"
                "- `hyperv`\n"
                "- `virtualization`\n"
                "- `powershell`\n"
                "- `networking`\n"
                "- `infrastructure`\n"
                "- `storage`\n\n"
                "### computer_science\n"
                "- `ai_engineering`\n"
                "- `agents`\n"
                "- `rag`\n"
                "- `llm`\n"
                "- `memory`\n"
                "- `architecture`\n\n"
                "### operations\n"
                "- `worklog`\n"
                "- `diagnostics`\n"
                "- `telemetry`\n"
                "- `observability`\n\n"
                "### general\n"
                "- `guide`\n"
                "- `onboarding`\n"
                "- `reference`\n"
                "- `template`\n"
                "- `notes`\n"
            )
            tag_auth.write_text(tag_auth_content, encoding="utf-8")

        # Ensure canonical note template exists
        note_tmpl = self.root_dir / "02_Resources" / "_Templates" / "note_template.md"
        if not note_tmpl.exists():
            tmpl_content = (
                "---\n"
                "uid: \"YYYYMMDD-HHMMSS\"\n"
                "title: \"Standard Note Template\"\n"
                "aliases: []\n"
                "document_type: \"template\"\n"
                "domain: \"general\"\n"
                "topic: \"notes\"\n"
                "tags: []\n"
                "summary: \"1-2 sentence overview of this note.\"\n"
                "status: \"template\"\n"
                "priority: \"medium\"\n"
                "sensitivity: \"internal\"\n"
                "confidence_score: 1.0\n"
                "pinned: false\n"
                "parent: \"\"\n"
                "related: []\n"
                "moc: \"\"\n"
                "source: \"manual\"\n"
                "author: \"autoreiv\"\n"
                "model: \"\"\n"
                "content_hash: \"\"\n"
                "date_created: \"YYYY-MM-DD\"\n"
                "last_updated: \"YYYY-MM-DD\"\n"
                "last_accessed: \"YYYY-MM-DD\"\n"
                "access_count: 0\n"
                "word_count: 0\n"
                "context_tokens: 0\n"
                "schema_version: \"1.0\"\n"
                "---\n\n"
                "# ${TITLE}\n\n"
                "## Context\n"
                "${CONTEXT}\n\n"
                "## Details\n"
                "${DETAILS}\n\n"
                "## References\n"
                "- [[local_agent_architecture]]\n"
            )
            note_tmpl.write_text(tmpl_content, encoding="utf-8")

        # Ensure structured templates exist [CARD-178, REQ-WIKI-030]
        templates_dir = self.root_dir / "02_Resources" / "_Templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        for filename, tmpl_meta in CORE_STRUCTURED_TEMPLATES.items():
            tmpl_file = templates_dir / filename
            if not tmpl_file.exists():
                tmpl_file.write_text(tmpl_meta["content"], encoding="utf-8")

        should_seed = self.auto_seed if seed_starter is None else seed_starter
        if should_seed:
            self._seed_starter_notes_if_empty()



    def scrub_empty_seed_taxonomy(self) -> List[str]:
        """
        Idempotently remove empty pre-CARD-406 seed taxonomy dirs under 01_Notes [CARD-416].

        Only empty directories are removed (Path.rmdir). Non-empty note paths are never deleted.
        Invoked from scaffold so establish / Settings confirm_scaffold cleans leftovers.
        """
        notes_root = self.root_dir / "01_Notes"
        if not notes_root.is_dir():
            return []

        candidates: list[Path] = []
        seen: set[Path] = set()
        for rel in _EMPTY_SEED_TAXONOMY_REL_PATHS:
            parts = Path(rel).parts
            for depth in range(len(parts), 0, -1):
                candidate = notes_root.joinpath(*parts[:depth])
                if candidate not in seen:
                    seen.add(candidate)
                    candidates.append(candidate)

        candidates.sort(key=lambda p: len(p.parts), reverse=True)
        actions: List[str] = []
        for candidate in candidates:
            if not candidate.is_dir():
                continue
            try:
                candidate.rmdir()
            except OSError:
                # Non-empty or busy — leave operator content alone.
                continue
            rel = candidate.relative_to(self.root_dir).as_posix()
            actions.append(f"Removed empty seed taxonomy: {rel}")
            log.info("CARD-416 scrubbed empty seed taxonomy path: %s", rel)
        return actions

    def _seed_starter_notes_if_empty(self) -> None:
        """
        Maintains vanilla vault seeding: strictly numbered folders with canonical templates only [CARD-406].
        Pre-filled mock domain notes are completely retired.
        """
        return

    def migrate_legacy_vault(self, ensure_scaffold: bool = True) -> Dict[str, Any]:
        """
        Migrate legacy unnumbered (inbox, notes, resources, archive) or old 0X_ folders
        into the standardized CARD-173 numbered layout:
        00_Inbox/, 01_Notes/, 02_Resources/, 03_Archive/.
        """
        if ensure_scaffold:
            self.scaffold(auto_migrate=False)
        actions = []
        migrated_files = 0

        # 1. Legacy inbox/ -> 00_Inbox/
        legacy_inbox = self.root_dir / "inbox"
        inbox_dest = self.root_dir / "00_Inbox"
        if legacy_inbox.exists() and legacy_inbox.is_dir():
            for f in list(legacy_inbox.rglob("*.md")):
                target = inbox_dest / f.name
                if not target.exists():
                    shutil.move(str(f), str(target))
                    actions.append(f"Moved {f.name} to 00_Inbox/")
                    migrated_files += 1
                else:
                    if f.resolve() != target.resolve():
                        if f.read_text(encoding="utf-8", errors="replace") == target.read_text(encoding="utf-8", errors="replace"):
                            f.unlink(missing_ok=True)
                        else:
                            safe_name = f"{f.stem}_migrated_{int(dt.datetime.now().timestamp())}{f.suffix}"
                            safe_target = inbox_dest / safe_name
                            shutil.move(str(f), str(safe_target))
                            actions.append(f"Moved {f.name} to 00_Inbox/{safe_name}")
                            migrated_files += 1
            if legacy_inbox.exists() and not any(legacy_inbox.iterdir()):
                shutil.rmtree(legacy_inbox, ignore_errors=True)

        # 2. Legacy notes/ -> 01_Notes/
        legacy_notes = self.root_dir / "notes"
        notes_dest = self.root_dir / "01_Notes"
        if legacy_notes.exists() and legacy_notes.is_dir():
            for f in list(legacy_notes.rglob("*.md")):
                rel_inside = f.relative_to(legacy_notes)
                target = notes_dest / rel_inside
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    shutil.move(str(f), str(target))
                    actions.append(f"Moved {rel_inside} to 01_Notes/")
                    migrated_files += 1
                else:
                    if f.resolve() != target.resolve():
                        if f.read_text(encoding="utf-8", errors="replace") == target.read_text(encoding="utf-8", errors="replace"):
                            f.unlink(missing_ok=True)
                        else:
                            safe_name = f"{f.stem}_migrated_{int(dt.datetime.now().timestamp())}{f.suffix}"
                            safe_target = target.parent / safe_name
                            shutil.move(str(f), str(safe_target))
                            actions.append(f"Moved {rel_inside} to 01_Notes/{safe_name}")
                            migrated_files += 1
            if legacy_notes.exists():
                for d in sorted(legacy_notes.rglob("*"), reverse=True):
                    if d.is_dir():
                        try:
                            d.rmdir()
                        except Exception:
                            pass
                if not any(legacy_notes.iterdir()):
                    shutil.rmtree(legacy_notes, ignore_errors=True)

        # 3. Legacy resources/ -> 02_Resources/
        legacy_resources = self.root_dir / "resources"
        resources_dest = self.root_dir / "02_Resources"
        if legacy_resources.exists() and legacy_resources.is_dir():
            for f in list(legacy_resources.rglob("*.md")):
                rel_inside = f.relative_to(legacy_resources)
                rel_parts = list(rel_inside.parts)
                if rel_parts and rel_parts[0].lower() == "templates":
                    rel_parts[0] = "_Templates"
                target = resources_dest / Path(*rel_parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    shutil.move(str(f), str(target))
                    actions.append(f"Moved {rel_inside} to 02_Resources/")
                    migrated_files += 1
                else:
                    f.unlink(missing_ok=True)
            if legacy_resources.exists() and not any(legacy_resources.iterdir()):
                shutil.rmtree(legacy_resources, ignore_errors=True)

        # 4. Legacy archive/ -> 03_Archive/
        legacy_archive = self.root_dir / "archive"
        archive_dest = self.root_dir / "03_Archive"
        if legacy_archive.exists() and legacy_archive.is_dir():
            for f in list(legacy_archive.rglob("*.md")):
                target = archive_dest / f.name
                if not target.exists():
                    shutil.move(str(f), str(target))
                    actions.append(f"Moved {f.name} to 03_Archive/")
                    migrated_files += 1
                else:
                    f.unlink(missing_ok=True)
            if legacy_archive.exists() and not any(legacy_archive.iterdir()):
                shutil.rmtree(legacy_archive, ignore_errors=True)

        # 5. Clean legacy 01_Projects, 02_Areas, 03_resources, 04_Archive if present
        for legacy_name in ["01_Projects", "02_Areas", "03_resources", "04_Archive"]:
            legacy_dir = self.root_dir / legacy_name
            if legacy_dir.exists() and legacy_dir.is_dir():
                for f in list(legacy_dir.rglob("*.md")):
                    dest = inbox_dest / f.name
                    if not dest.exists():
                        shutil.move(str(f), str(dest))
                        actions.append(f"Moved {f.name} from {legacy_name} to 00_Inbox/")
                        migrated_files += 1
                    else:
                        f.unlink(missing_ok=True)
                shutil.rmtree(legacy_dir, ignore_errors=True)

        return {"success": True, "migrated_count": migrated_files, "actions": actions}

    def _resolve_safe_path(self, relative_path: str) -> Optional[Path]:
        """Ensure relative path does not escape root_dir, with alias resolution between legacy and numbered paths."""
        try:
            rel = relative_path.replace("\\", "/").lstrip("/")
            target = (self.root_dir / rel).resolve()
            if not str(target).startswith(str(self.root_dir)):
                return None
            if target.exists():
                return target

            # Check legacy -> numbered mapping
            prefix_map = {
                "inbox/": "00_Inbox/",
                "00_inbox/": "00_Inbox/",
                "notes/": "01_Notes/",
                "01_notes/": "01_Notes/",
                "resources/": "02_Resources/",
                "02_resources/": "02_Resources/",
                "archive/": "03_Archive/",
                "03_archive/": "03_Archive/",
                "02_resources/templates/": "02_Resources/_Templates/",
                "resources/templates/": "02_Resources/_Templates/",
            }
            rel_lower = rel.lower()
            for prefix, mapped in prefix_map.items():
                if rel_lower.startswith(prefix):
                    alt = self.root_dir / (mapped + rel[len(prefix):])
                    if alt.exists():
                        return alt.resolve()

            # Reverse mapping: numbered -> legacy
            reverse_map = {
                "00_inbox/": "inbox/",
                "01_notes/": "notes/",
                "02_resources/": "resources/",
                "03_archive/": "archive/",
            }
            for prefix, mapped in reverse_map.items():
                if rel_lower.startswith(prefix):
                    alt = self.root_dir / (mapped + rel[len(prefix):])
                    if alt.exists():
                        return alt.resolve()

            return target
        except Exception:
            return None

    def file_note(
        self,
        title: str,
        content: str,
        domain: str = "general",
        topic: str = "general",
        category: str = "inbox",
        inbox_priority: str = "need_to_do",
        document_type: str = "atomic_note",
        tags: Optional[List[str]] = None,
        summary: str = "",
        status: Optional[str] = None,
        priority: str = "medium",
        sensitivity: str = "internal",
        extra_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create and persist a new note with structured YAML frontmatter.
        Defaults to 00_Inbox/ with clean_note_content() applied to scrub conversational chatter.
        """
        self.scaffold()
        slug = slugify(title)
        cleaned_content = clean_note_content(content)
        cat_lower = (category or "inbox").lower().strip()

        if cat_lower in ("inbox", "00_inbox"):
            rel_path = f"00_Inbox/{slug}.md"
            meta_status = status or "inbox"
            meta_doc_type = document_type if document_type != "atomic_note" else "note"
            inbox_kwargs: Dict[str, Any] = {
                "title": title,
                "domain": slugify(domain) or "general",
                "topic": slugify(topic) or "general",
                "document_type": meta_doc_type,
                "tags": tags or [],
                "summary": summary,
                "status": meta_status,
                "author": (extra_meta or {}).get("author", "autoreiv"),
            }
            if extra_meta:
                for k, v in extra_meta.items():
                    if k not in inbox_kwargs:
                        inbox_kwargs[k] = v
            inbox_meta = WikiInboxNoteMeta(**inbox_kwargs)
            full_text = FrontmatterParser.dump(inbox_meta, cleaned_content)
            final_domain = inbox_meta.domain
            final_topic = inbox_meta.topic
            final_uid = inbox_meta.uid
        elif cat_lower in ("resources", "02_resources"):
            rel_path = f"02_Resources/operating_manuals/{slug}.md"
            meta_status = status or "active"
            meta_kwargs = {
                "title": title,
                "domain": domain,
                "topic": topic,
                "document_type": document_type,
                "tags": tags or [],
                "summary": summary,
                "status": meta_status,
                "priority": priority,
                "sensitivity": sensitivity,
            }
            if extra_meta:
                meta_kwargs.update(extra_meta)
            grad_meta = WikiNoteMeta(**meta_kwargs)
            full_text = FrontmatterParser.dump(grad_meta, cleaned_content)
            final_domain = grad_meta.domain
            final_topic = grad_meta.topic
            final_uid = grad_meta.uid
        elif cat_lower in ("archive", "03_archive"):
            rel_path = f"03_Archive/{slug}.md"
            meta_status = status or "archived"
            meta_kwargs = {
                "title": title,
                "domain": domain,
                "topic": topic,
                "document_type": document_type,
                "tags": tags or [],
                "summary": summary,
                "status": meta_status,
                "priority": priority,
                "sensitivity": sensitivity,
            }
            if extra_meta:
                meta_kwargs.update(extra_meta)
            grad_meta = WikiNoteMeta(**meta_kwargs)
            full_text = FrontmatterParser.dump(grad_meta, cleaned_content)
            final_domain = grad_meta.domain
            final_topic = grad_meta.topic
            final_uid = grad_meta.uid
        else:
            safe_domain = slugify(domain) or "general"
            safe_topic = slugify(topic) or "general"
            target_folder = "01_Notes" if (self.root_dir / "01_Notes").exists() else "notes"
            rel_path = f"{target_folder}/{safe_domain}/{safe_topic}/{slug}.md"
            meta_status = status or "draft"
            meta_kwargs = {
                "title": title,
                "domain": domain,
                "topic": topic,
                "document_type": document_type,
                "tags": tags or [],
                "summary": summary,
                "status": meta_status,
                "priority": priority,
                "sensitivity": sensitivity,
            }
            if extra_meta:
                meta_kwargs.update(extra_meta)
            grad_meta = WikiNoteMeta(**meta_kwargs)
            full_text = FrontmatterParser.dump(grad_meta, cleaned_content)
            final_domain = grad_meta.domain
            final_topic = grad_meta.topic
            final_uid = grad_meta.uid

        target_path = self.root_dir / rel_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(full_text, encoding="utf-8")

        return {
            "success": True,
            "path": rel_path.replace("\\", "/"),
            "title": title,
            "uid": final_uid,
            "domain": final_domain,
            "topic": final_topic,
        }

    def get_backlinks(self, target_rel: str) -> List[str]:
        """Find all note relative paths that link to this note via [[...]]."""
        target_path = self._resolve_safe_path(target_rel)
        if not target_path or not target_path.exists():
            return []

        target_stem = target_path.stem.lower()
        raw = target_path.read_text(encoding="utf-8", errors="replace")
        meta, _ = FrontmatterParser.parse(raw)
        target_title = meta.title.lower()

        backlinks = []
        for f in sorted(self.root_dir.rglob("*.md")):
            if f.resolve() == target_path.resolve():
                continue
            f_rel = str(f.relative_to(self.root_dir)).replace("\\", "/")
            f_text = f.read_text(encoding="utf-8", errors="replace")
            for link in _LINK_PATTERN.findall(f_text):
                clean_link = link.strip().lower()
                if (
                    clean_link == target_stem
                    or clean_link == target_title
                    or clean_link.endswith("/" + target_stem)
                    or clean_link == target_stem.replace("_", " ")
                ):
                    backlinks.append(f_rel)
                    break
        return backlinks

    def read_note(self, relative_path: str) -> Dict[str, Any]:
        """
        Read a note, extract frontmatter, backlinks, and return clean content.
        """
        target_path = self._resolve_safe_path(relative_path)
        if target_path is None or not target_path.is_file():
            return {"success": False, "error": f"Note '{relative_path}' not found."}

        raw_text = target_path.read_text(encoding="utf-8", errors="replace")
        meta, body = FrontmatterParser.parse(raw_text)
        backlinks = self.get_backlinks(relative_path)
        raw_fm = FrontmatterParser.extract_raw_frontmatter(raw_text)
        if not raw_fm:
            dumped = FrontmatterParser.dump(meta)
            raw_fm = dumped.split("---")[1].strip() if "---" in dumped else ""

        return {
            "success": True,
            "path": relative_path.replace("\\", "/"),
            "meta": meta.model_dump(),
            "content": body,
            "title": meta.title,
            "backlinks": backlinks,
            "raw_frontmatter": raw_fm,
        }

    def append_note(
        self,
        relative_path: str,
        content: str,
        heading: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Safely append markdown content to an existing note (optionally under a heading)
        without corrupting frontmatter, and automatically update telemetry and content hash.
        """
        target = self._resolve_safe_path(relative_path)
        if target is None or not target.exists() or not target.is_file():
            return {"success": False, "error": f"Note not found: {relative_path}"}

        existing_text = target.read_text(encoding="utf-8", errors="replace")
        meta, body = FrontmatterParser.parse(existing_text)

        append_chunk = content.strip()
        if heading:
            clean_heading = heading.strip()
            if not clean_heading.startswith("#"):
                clean_heading = f"## {clean_heading}"
            append_chunk = f"\n\n{clean_heading}\n\n{append_chunk}"
        else:
            append_chunk = f"\n\n{append_chunk}"

        new_body = (body.strip() + append_chunk).strip()

        meta_dict = meta.model_dump()
        meta_dict["last_updated"] = dt.datetime.now().strftime("%Y-%m-%d")
        meta_dict["last_accessed"] = dt.datetime.now().strftime("%Y-%m-%d")

        serialized = FrontmatterParser.dump(meta_dict, new_body)
        target.write_text(serialized, encoding="utf-8")

        return {
            "success": True,
            "path": relative_path.replace("\\", "/"),
            "title": meta.title,
            "word_count": compute_word_count(new_body),
            "context_tokens": compute_context_tokens(new_body),
            "content_hash": compute_content_hash(new_body),
        }

    def archive_note(
        self,
        relative_path: str,
        reason: str = "archived",
        preserve_source: bool = False,
    ) -> Dict[str, Any]:
        """
        Safely archive a note to 03_Archive/<slug>_<timestamp>.md [CARD-409].
        Preserves frontmatter, sets status='archived', and updates archive metadata.
        If preserve_source is True, copies to archive instead of moving.
        """
        self.scaffold()
        target_path = self._resolve_safe_path(relative_path)
        if target_path is None or not target_path.is_file():
            return {"success": False, "error": f"Note '{relative_path}' not found."}

        raw_text = target_path.read_text(encoding="utf-8", errors="replace")
        meta, body = FrontmatterParser.parse(raw_text)
        meta_dict = meta.model_dump()
        meta_dict["status"] = "archived"
        meta_dict["archived_at"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if reason:
            meta_dict["archive_reason"] = reason

        archive_dir = self.root_dir / "03_Archive"
        archive_dir.mkdir(parents=True, exist_ok=True)

        stem = target_path.stem
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_filename = f"{stem}_{ts}.md"
        dest_path = archive_dir / archive_filename
        counter = 1
        while dest_path.exists():
            dest_path = archive_dir / f"{stem}_{ts}_{counter}.md"
            counter += 1

        updated_meta = WikiNoteMeta.model_validate(meta_dict)
        full_text = FrontmatterParser.dump(updated_meta, body)
        dest_path.write_text(full_text, encoding="utf-8")

        if not preserve_source:
            target_path.unlink(missing_ok=True)

        rel_dest = str(dest_path.relative_to(self.root_dir)).replace("\\", "/")
        return {
            "success": True,
            "source_path": relative_path.replace("\\", "/"),
            "archive_path": rel_dest,
            "title": updated_meta.title,
            "status": "archived",
        }

    def write_note(
        self,
        relative_path: str,
        content: str,
        update_frontmatter: Optional[Dict[str, Any]] = None,
        backup_to_archive: bool = False,
    ) -> Dict[str, Any]:
        """
        Non-destructively update an existing note's body, preserving metadata and bumping last_updated.
        Optionally backs up the existing note to 03_Archive/ before writing [CARD-409].
        """
        target_path = self._resolve_safe_path(relative_path)
        if target_path is None:
            return {"success": False, "error": "Invalid or unsafe path."}

        if target_path.is_file():
            if backup_to_archive:
                self.archive_note(relative_path, reason="Backup before update", preserve_source=True)
            raw_text = target_path.read_text(encoding="utf-8", errors="replace")
            meta, _ = FrontmatterParser.parse(raw_text)
            meta_dict = meta.model_dump()
        else:
            meta_dict = WikiNoteMeta(title=target_path.stem.replace("_", " ")).model_dump()
            target_path.parent.mkdir(parents=True, exist_ok=True)

        if update_frontmatter:
            meta_dict.update(update_frontmatter)

        meta_dict["last_updated"] = dt.datetime.now().strftime("%Y-%m-%d")
        updated_meta = WikiNoteMeta.model_validate(meta_dict)

        full_text = FrontmatterParser.dump(updated_meta, content)
        target_path.write_text(full_text, encoding="utf-8")

        return {
            "success": True,
            "path": relative_path.replace("\\", "/"),
            "uid": updated_meta.uid,
            "title": updated_meta.title,
        }

    def delete_note(self, relative_path: str) -> bool:
        """Delete a note from disk."""
        target_path = self._resolve_safe_path(relative_path)
        if target_path and target_path.is_file():
            target_path.unlink()
            return True
        return False

    def delete_folder(self, relative_path: str) -> Dict[str, Any]:
        """
        Delete a subfolder from the wiki vault [REQ-WIKI-024, REQ-WIKI-025].
        Strictly prevents deleting root folders (00_Inbox, 01_Notes, 02_Resources, 03_Archive, or the vault root).
        """
        clean_rel = (relative_path or "").replace("\\", "/").strip().strip("/")
        clean_lower = clean_rel.lower()

        # Hard guard: Protected root folders and root directory itself
        protected_roots = {
            "",
            ".",
            "00_inbox",
            "inbox",
            "01_notes",
            "notes",
            "02_resources",
            "resources",
            "03_archive",
            "archive",
        }
        if not clean_rel or clean_lower in protected_roots:
            return {
                "success": False,
                "error": f"Cannot delete protected root vault folder '{relative_path}'.",
            }

        target_path = self._resolve_safe_path(clean_rel)
        if target_path is None:
            return {"success": False, "error": "Path traversal detected: target path is outside wiki root."}

        resolved_str = str(target_path.resolve())
        root_str = str(self.root_dir.resolve())
        if resolved_str == root_str:
            return {"success": False, "error": "Cannot delete protected root vault directory."}

        for root_name in ["00_Inbox", "01_Notes", "02_Resources", "03_Archive", "inbox", "notes", "resources", "archive"]:
            if resolved_str == str((self.root_dir / root_name).resolve()):
                return {
                    "success": False,
                    "error": f"Cannot delete protected root vault folder '{relative_path}'.",
                }

        if not target_path.exists() or not target_path.is_dir():
            return {"success": False, "error": f"Folder '{relative_path}' not found."}

        try:
            shutil.rmtree(target_path)
            return {"success": True, "path": clean_rel}
        except Exception as e:
            return {"success": False, "error": f"Failed to delete folder '{clean_rel}': {e}"}

    def _resolve_templates_dir(self, create: bool = True) -> Path:
        self.scaffold()
        p1 = self.root_dir / "02_Resources" / "_Templates"
        if p1.exists():
            return p1
        p2 = self.root_dir / "resources" / "templates"
        if p2.exists():
            return p2
        if create:
            p1.mkdir(parents=True, exist_ok=True)
            return p1
        return p1

    def list_templates(self) -> List[Dict[str, Any]]:
        """
        List all available structured note templates in 02_Resources/_Templates/.
        Excludes non-template authority files like tag-authority.md [REQ-WIKI-031].
        Returns lightweight index metadata only (slug, title, description, path, tags) [CARD-353].
        Full body skeleton is retrieved via get_template(slug).
        """
        self.scaffold()
        templates_dir = self.root_dir / "02_Resources" / "_Templates"
        if not templates_dir.exists():
            templates_dir = self.root_dir / "resources" / "templates"
            if not templates_dir.exists():
                return []

        results = []
        for file in sorted(templates_dir.glob("*.md")):
            if file.name.lower() in ("tag-authority.md", "tag_authority.md"):
                continue
            slug = file.stem.replace("_", "-")
            content = file.read_text(encoding="utf-8", errors="replace")
            meta, _ = FrontmatterParser.parse(content)
            title = meta.title if meta.title and meta.title != "Untitled Note" else slug.replace("-", " ").title()
            description = meta.summary or "Structured note template."
            results.append({
                "slug": slug,
                "title": title,
                "description": description,
                "path": str(file.relative_to(self.root_dir)).replace("\\", "/"),
                "tags": meta.tags or [],
            })
        return results

    def get_template(self, slug: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific structured template by its slug or filename [REQ-WIKI-031].
        Returns complete template metadata, skeleton content, and raw template text [CARD-353].
        """
        self.scaffold()
        target_slug = slug.lower().replace("_", "-").replace(".md", "")
        templates_dir = self.root_dir / "02_Resources" / "_Templates"
        if not templates_dir.exists():
            templates_dir = self.root_dir / "resources" / "templates"
            if not templates_dir.exists():
                return None

        for file in sorted(templates_dir.glob("*.md")):
            if file.name.lower() in ("tag-authority.md", "tag_authority.md"):
                continue
            file_slug = file.stem.replace("_", "-").lower()
            if file_slug == target_slug:
                content = file.read_text(encoding="utf-8", errors="replace")
                meta, body = FrontmatterParser.parse(content)
                title = meta.title if meta.title and meta.title != "Untitled Note" else file_slug.replace("-", " ").title()
                description = meta.summary or "Structured note template."
                return {
                    "slug": file_slug,
                    "title": title,
                    "description": description,
                    "path": str(file.relative_to(self.root_dir)).replace("\\", "/"),
                    "content": body.strip(),
                    "raw_template": content,
                    "tags": meta.tags or [],
                }
        return None

    def create_template(
        self,
        slug: str,
        title: str,
        description: str,
        content: str,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new structured note template strictly under the templates directory [CARD-349].
        Fails closed if a template with this slug already exists.
        """
        clean_slug = str(slug or "").strip().lower().replace(" ", "-").replace("_", "-")
        if clean_slug.endswith(".md"):
            clean_slug = clean_slug[:-3]
        clean_slug = re.sub(r"[^a-z0-9\-]", "", clean_slug)
        if not clean_slug:
            return {"success": False, "error": "Invalid or empty template slug."}

        templates_dir = self._resolve_templates_dir(create=True)
        target_file = templates_dir / f"{clean_slug}.md"
        rel_path = str(target_file.relative_to(self.root_dir)).replace("\\", "/")

        if target_file.exists():
            return {
                "success": False,
                "error": f"Template with slug '{clean_slug}' already exists at '{rel_path}'. Use wiki_template_update to modify existing templates.",
                "path": rel_path,
            }

        clean_tags = list(tags) if tags is not None else ["wiki", "template"]
        if "template" not in clean_tags:
            clean_tags.append("template")

        clean_title = (title or "").strip() or clean_slug.replace("-", " ").title()
        clean_desc = (description or "").strip() or "Structured note template."

        meta_dict = {
            "uid": dt.datetime.now().strftime("%Y%m%d-%H%M%S"),
            "title": clean_title,
            "document_type": "template",
            "type": "template",
            "summary": clean_desc,
            "description": clean_desc,
            "tags": clean_tags,
            "domain": "general",
            "topic": "template",
            "status": "template",
            "created_at": dt.datetime.now().strftime("%Y-%m-%d"),
            "last_updated": dt.datetime.now().strftime("%Y-%m-%d"),
            "schema_version": "1.0",
        }

        body = (content or "").strip()
        serialized = FrontmatterParser.dump(meta_dict, body)
        if "type: template" not in serialized:
            serialized = serialized.replace("document_type: template", "document_type: template\ntype: template")

        target_file.write_text(serialized, encoding="utf-8")
        return {
            "success": True,
            "slug": clean_slug,
            "title": clean_title,
            "path": rel_path,
        }

    def update_template(
        self,
        slug: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Update an existing structured note template [CARD-349].
        Fails closed if the template with this slug does not exist.
        """
        clean_slug = str(slug or "").strip().lower().replace(" ", "-").replace("_", "-")
        if clean_slug.endswith(".md"):
            clean_slug = clean_slug[:-3]
        clean_slug = re.sub(r"[^a-z0-9\-]", "", clean_slug)
        if not clean_slug:
            return {"success": False, "error": "Invalid or empty template slug."}

        templates_dir = self._resolve_templates_dir(create=False)
        target_file = templates_dir / f"{clean_slug}.md"
        if not target_file.exists():
            alt_dir = self.root_dir / "resources" / "templates"
            if (alt_dir / f"{clean_slug}.md").exists():
                target_file = alt_dir / f"{clean_slug}.md"

        if not target_file.exists():
            return {
                "success": False,
                "error": f"Template with slug '{clean_slug}' not found. Use wiki_template_create to author new templates.",
            }

        raw_text = target_file.read_text(encoding="utf-8", errors="replace")
        meta, existing_body = FrontmatterParser.parse(raw_text)
        meta_dict = meta.model_dump()
        meta_dict["type"] = "template"
        meta_dict["document_type"] = "template"

        if title is not None:
            meta_dict["title"] = title.strip()
        if description is not None:
            meta_dict["summary"] = description.strip()
            meta_dict["description"] = description.strip()
        if tags is not None:
            meta_dict["tags"] = list(tags)

        meta_dict["last_updated"] = dt.datetime.now().strftime("%Y-%m-%d")

        new_body = content.strip() if content is not None else existing_body.strip()
        serialized = FrontmatterParser.dump(meta_dict, new_body)
        if "type: template" not in serialized:
            serialized = serialized.replace("document_type: template", "document_type: template\ntype: template")

        target_file.write_text(serialized, encoding="utf-8")
        rel_path = str(target_file.relative_to(self.root_dir)).replace("\\", "/")
        return {
            "success": True,
            "slug": clean_slug,
            "title": meta_dict.get("title", clean_slug),
            "path": rel_path,
        }


    def organize_note(
        self,
        source_path: str,
        target_domain: str,
        target_topic: str,
        document_type: str = "atomic_note",
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        new_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Move a note (e.g. from inbox/ to notes/<domain>/<topic>/) and hydrate frontmatter.
        """
        source_file = self._resolve_safe_path(source_path)
        if not source_file or not source_file.is_file():
            return {"success": False, "error": f"Source note '{source_path}' does not exist."}

        raw_text = source_file.read_text(encoding="utf-8", errors="replace")
        meta, body = FrontmatterParser.parse(raw_text)
        meta_dict = meta.model_dump()

        safe_domain = _SLUG_CLEAN_PATTERN.sub("_", (target_domain or "general").lower()).strip("_")
        safe_topic = _SLUG_CLEAN_PATTERN.sub("_", (target_topic or "general").lower()).strip("_")
        slug = source_file.stem

        target_rel = f"notes/{safe_domain}/{safe_topic}/{slug}.md"
        target_file = self._resolve_safe_path(target_rel)
        if target_file is None:
            return {"success": False, "error": "Invalid destination path."}

        # Update metadata
        meta_dict["domain"] = safe_domain
        meta_dict["topic"] = safe_topic
        meta_dict["category"] = "notes"
        meta_dict["document_type"] = document_type
        meta_dict["status"] = "final"
        if new_title:
            meta_dict["title"] = new_title
        if summary:
            meta_dict["summary"] = summary
        if tags is not None:
            meta_dict["tags"] = tags
        meta_dict["last_updated"] = dt.datetime.now().strftime("%Y-%m-%d")

        word_count = compute_word_count(body)
        meta_dict["word_count"] = word_count
        meta_dict["context_tokens"] = compute_context_tokens(body)

        updated_meta = WikiNoteMeta.model_validate(meta_dict)
        full_text = FrontmatterParser.dump(updated_meta, body)

        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(full_text, encoding="utf-8")

        # Remove source if different from destination
        if source_file.resolve() != target_file.resolve():
            source_file.unlink(missing_ok=True)

        return {
            "success": True,
            "source_path": source_path,
            "target_path": target_rel,
            "title": updated_meta.title,
            "domain": safe_domain,
            "topic": safe_topic,
            "document_type": updated_meta.document_type,
            "tags": updated_meta.tags,
            "summary": updated_meta.summary,
        }

    def list_notes(
        self,
        category: Optional[str] = None,
        domain: Optional[str] = None,
        topic: Optional[str] = None,
        status: Optional[str] = None,
        tag: Optional[str] = None,
        author: Optional[str] = None,
        pinned: Optional[bool] = None,
        priority: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List markdown notes across the wiki matching folder or frontmatter filters."""
        if not self.root_dir.is_dir():
            return []

        out = []
        for file_path in sorted(self.root_dir.rglob("*.md")):
            rel = str(file_path.relative_to(self.root_dir)).replace("\\", "/")
            if rel.startswith("."):
                continue

            # Category filter (e.g. inbox, notes, resources)
            if category:
                cat_lower = category.lower().strip()
                if not rel.lower().startswith(cat_lower):
                    continue

            raw_text = file_path.read_text(encoding="utf-8", errors="replace")
            meta, body = FrontmatterParser.parse(raw_text)

            # Metadata domain filter
            if domain and meta.domain.lower() != domain.lower().strip():
                continue

            # Metadata topic filter
            if topic and meta.topic.lower() != topic.lower().strip():
                continue

            # Metadata status filter
            if status and meta.status.lower() != status.lower().strip():
                continue

            # Metadata tag filter
            if tag and not any(tag.lower().strip() == t.lower() for t in meta.tags):
                continue

            # Metadata author filter
            if author and meta.author.lower() != author.lower().strip():
                continue

            # Metadata pinned filter
            if pinned is not None and meta.pinned != pinned:
                continue

            # Metadata priority filter
            if priority and meta.priority.lower() != priority.lower().strip():
                continue

            out.append(
                {
                    "path": rel,
                    "title": meta.title,
                    "domain": meta.domain,
                    "topic": meta.topic,
                    "document_type": meta.document_type,
                    "tags": meta.tags,
                    "status": meta.status,
                    "priority": meta.priority,
                    "author": meta.author,
                    "pinned": meta.pinned,
                    "summary": meta.summary,
                    "preview": body[:200],
                    "last_updated": meta.last_updated,
                    "word_count": meta.word_count,
                    "context_tokens": meta.context_tokens,
                    "content_hash": meta.content_hash,
                }
            )
        return out

    def cleanup_vault(self) -> Dict[str, Any]:
        """
        Clean up misplaced templates, organize weekly worklogs to 01_Notes/weekly/,
        and ensure canonical templates live in 02_Resources/_Templates/ [CARD-173, CARD-406].
        """
        self.scaffold()
        actions = []

        # 1. Clean misplaced templates inside legacy notes/
        notes_dir = self.root_dir / "notes"
        if notes_dir.exists():
            for f in list(notes_dir.rglob("*.md")):
                f_name = f.name.lower()
                parent_name = f.parent.name.lower()
                if "template" in f_name or "templates" == parent_name:
                    f.unlink(missing_ok=True)
                    actions.append(f"Deleted misplaced template: {f.name}")

        # 2. Relocate legacy weekly logs to 01_Notes/weekly/
        legacy_weekly = self.root_dir / "notes" / "weekly"
        ops_worklog = self.root_dir / "01_Notes" / "weekly"
        if legacy_weekly.exists() and legacy_weekly.is_dir():
            ops_worklog.mkdir(parents=True, exist_ok=True)
            for f in list(legacy_weekly.glob("*.md")):
                dest = ops_worklog / f.name
                if not dest.exists():
                    f.rename(dest)
                    actions.append(f"Moved weekly note to 01_Notes/weekly: {f.name}")
                else:
                    f.unlink(missing_ok=True)
            try:
                legacy_weekly.rmdir()
            except Exception:
                pass

        # 3. Clean legacy unnumbered directories via migrate_legacy_vault
        migration = self.migrate_legacy_vault(ensure_scaffold=False)
        actions.extend(migration.get("actions", []))

        # Clean up empty legacy notes/ tree if left behind
        notes_dir = self.root_dir / "notes"
        if notes_dir.exists():
            for d in sorted(notes_dir.rglob("*"), reverse=True):
                if d.is_dir():
                    try:
                        d.rmdir()
                    except Exception:
                        pass
            try:
                notes_dir.rmdir()
            except Exception:
                pass

        # 4. Ensure single canonical template in 02_Resources/_Templates/note_template.md
        tmpl_dir = self.root_dir / "02_Resources" / "_Templates"
        tmpl_dir.mkdir(parents=True, exist_ok=True)
        canonical_tmpl = tmpl_dir / "note_template.md"
        if not canonical_tmpl.exists():
            tmpl_content = (
                "---\n"
                "uid: \"YYYYMMDD-HHMMSS\"\n"
                "title: \"Standard Note Template\"\n"
                "aliases: []\n"
                "document_type: \"template\"\n"
                "domain: \"general\"\n"
                "topic: \"notes\"\n"
                "tags: []\n"
                "summary: \"1-2 sentence overview of this note.\"\n"
                "status: \"template\"\n"
                "priority: \"medium\"\n"
                "sensitivity: \"internal\"\n"
                "confidence_score: 1.0\n"
                "pinned: false\n"
                "parent: \"\"\n"
                "related: []\n"
                "moc: \"\"\n"
                "source: \"manual\"\n"
                "author: \"autoreiv\"\n"
                "model: \"\"\n"
                "content_hash: \"\"\n"
                "date_created: \"YYYY-MM-DD\"\n"
                "last_updated: \"YYYY-MM-DD\"\n"
                "last_accessed: \"YYYY-MM-DD\"\n"
                "access_count: 0\n"
                "word_count: 0\n"
                "context_tokens: 0\n"
                "schema_version: \"1.0\"\n"
                "---\n\n"
                "# ${TITLE}\n\n"
                "## Context\n"
                "${CONTEXT}\n\n"
                "## Details\n"
                "${DETAILS}\n\n"
                "## References\n"
                "- \n"
            )
            canonical_tmpl.write_text(tmpl_content, encoding="utf-8")
            actions.append("Created canonical template at 02_Resources/_Templates/note_template.md")

        return {"success": True, "actions": actions}

    def search_notes(
        self,
        query: str = "",
        limit: int = 5,
        tags: Optional[List[str]] = None,
        domain: Optional[str] = None,
        topic: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Progressive search scoring terms across note titles, tags, and summary snippets,
        with optional structured filtering by tags, domain, topic, and document_type [CARD-353].
        Returns lightweight summaries without full document bodies.
        """
        terms = {w.lower() for w in _WORD_PATTERN.findall(query or "")}
        normalized_tags = [t.lower().strip() for t in (tags or []) if t and t.strip()]

        scored = []
        include_templates = document_type == "template" or (domain and "template" in domain.lower())
        for note in self.list_notes():
            note_path = str(note.get("path", "")).lower()
            if not include_templates and (
                "_templates" in note_path
                or "templates/" in note_path
                or note_path.endswith("tag-authority.md")
            ):
                continue
            # Domain filter
            if domain and note.get("domain", "").lower() != domain.lower().strip():
                continue

            # Topic filter
            if topic and note.get("topic", "").lower() != topic.lower().strip():
                continue

            # Document type filter
            if document_type and note.get("document_type", "").lower() != document_type.lower().strip():
                continue

            # Tag filter
            note_tags = [t.lower().strip() for t in note.get("tags", [])]
            if normalized_tags:
                if not any(req_t in note_tags for req_t in normalized_tags):
                    continue

            # Scoring
            if terms:
                title_words = {w.lower() for w in _WORD_PATTERN.findall(note.get("title", ""))}
                body_words = {
                    w.lower() for w in _WORD_PATTERN.findall(note.get("preview", "") + " " + note.get("summary", ""))
                }
                tag_words = set(note_tags)

                score = len(terms & title_words) * 3 + len(terms & tag_words) * 2 + len(terms & body_words)
                if score > 0:
                    scored.append((score, note))
            else:
                # If no query keyword provided, all metadata-matching notes match
                tag_bonus = sum(1 for req_t in normalized_tags if req_t in note_tags)
                scored.append((1 + tag_bonus, note))

        scored.sort(key=lambda x: -x[0])
        return [item for _, item in scored[:limit]]

    def get_graph(self) -> Dict[str, Any]:
        """
        Extract [[wikilink]] references across all notes and generate directed graph nodes and edges.
        """
        notes = [n for n in self.list_notes() if "_Templates" not in n["path"] and "templates" not in n["path"]]
        by_slug = {p["path"].rsplit("/", 1)[-1][:-3].lower(): p for p in notes}
        by_title = {p["title"].lower(): p for p in notes}

        nodes = [
            {
                "id": p["path"],
                "title": p["title"],
                "domain": p["domain"],
                "topic": p["topic"],
                "size": max(1, p["word_count"] // 100),
            }
            for p in notes
        ]

        edges = []
        for p in notes:
            target_path = self._resolve_safe_path(p["path"])
            if not target_path or not target_path.is_file():
                continue
            raw = target_path.read_text(encoding="utf-8", errors="replace")
            _, body = FrontmatterParser.parse(raw)

            for target in _LINK_PATTERN.findall(body):
                target_clean = target.strip()
                t_lower = target_clean.lower()
                dest_note = by_title.get(t_lower) or by_slug.get(slugify(target_clean))
                if dest_note and dest_note["path"] != p["path"]:
                    edges.append(
                        {
                            "source": p["path"],
                            "target": dest_note["path"],
                            "target_title": dest_note["title"],
                        }
                    )

        return {"nodes": nodes, "edges": edges}

    def get_mindmap(self, include_tags: bool = True, include_taxonomy: bool = True) -> Dict[str, Any]:
        """
        Extract multi-dimensional knowledge graph for Obsidian-style Mind Map.
        Returns nodes (note, tag, domain, topic) and typed edges (wikilink, has_tag, in_topic, in_domain).
        """
        self.scaffold()
        notes = [n for n in self.list_notes() if "_Templates" not in n["path"] and "templates" not in n["path"]]

        by_title = {n["title"].lower(): n for n in notes}
        by_slug = {slugify(n["title"]): n for n in notes}

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        tag_counts: Dict[str, int] = {}
        domain_counts: Dict[str, int] = {}
        topic_counts: Dict[str, int] = {}

        # 1. Note Nodes
        for p in notes:
            nodes.append(
                {
                    "id": p["path"],
                    "label": p["title"],
                    "type": "note",
                    "domain": p["domain"],
                    "topic": p["topic"],
                    "tags": p["tags"],
                    "words": p["word_count"],
                    "tokens": p["context_tokens"],
                    "path": p["path"],
                }
            )

            # Tally tags
            for t in p["tags"]:
                t_clean = t.strip().lower()
                if t_clean:
                    tag_counts[t_clean] = tag_counts.get(t_clean, 0) + 1

            # Tally taxonomy
            if p["domain"]:
                domain_counts[p["domain"]] = domain_counts.get(p["domain"], 0) + 1
            if p["domain"] and p["topic"]:
                top_key = f"{p['domain']}:{p['topic']}"
                topic_counts[top_key] = topic_counts.get(top_key, 0) + 1

        # 2. Tag Nodes & Edges
        if include_tags:
            for tag, count in sorted(tag_counts.items()):
                tag_node_id = f"tag:{tag}"
                nodes.append(
                    {
                        "id": tag_node_id,
                        "label": f"#{tag}",
                        "type": "tag",
                        "count": count,
                    }
                )

            for p in notes:
                for t in p["tags"]:
                    t_clean = t.strip().lower()
                    if t_clean:
                        edges.append(
                            {
                                "source": p["path"],
                                "target": f"tag:{t_clean}",
                                "type": "has_tag",
                                "label": "tagged",
                            }
                        )

        # 3. Taxonomy Nodes & Edges
        if include_taxonomy:
            for dom, count in sorted(domain_counts.items()):
                dom_node_id = f"domain:{dom}"
                nodes.append(
                    {
                        "id": dom_node_id,
                        "label": f"🎓 {dom}",
                        "type": "domain",
                        "count": count,
                    }
                )

            for top_key, count in sorted(topic_counts.items()):
                dom, top = top_key.split(":", 1)
                top_node_id = f"topic:{dom}:{top}"
                nodes.append(
                    {
                        "id": top_node_id,
                        "label": f"📖 {top}",
                        "type": "topic",
                        "count": count,
                    }
                )
                # Edge topic -> domain
                edges.append(
                    {
                        "source": top_node_id,
                        "target": f"domain:{dom}",
                        "type": "in_domain",
                        "label": "part_of",
                    }
                )

            for p in notes:
                if p["domain"] and p["topic"]:
                    edges.append(
                        {
                            "source": p["path"],
                            "target": f"topic:{p['domain']}:{p['topic']}",
                            "type": "in_topic",
                            "label": "categorized_in",
                        }
                    )

        # 4. Wikilink Edges
        for p in notes:
            target_path = self._resolve_safe_path(p["path"])
            if not target_path or not target_path.is_file():
                continue
            raw = target_path.read_text(encoding="utf-8", errors="replace")
            _, body = FrontmatterParser.parse(raw)

            for target in _LINK_PATTERN.findall(body):
                target_clean = target.strip()
                t_lower = target_clean.lower()
                dest_note = by_title.get(t_lower) or by_slug.get(slugify(target_clean))
                if dest_note and dest_note["path"] != p["path"]:
                    edges.append(
                        {
                            "source": p["path"],
                            "target": dest_note["path"],
                            "type": "wikilink",
                            "label": "links_to",
                            "target_title": dest_note["title"],
                        }
                    )

        return {"nodes": nodes, "edges": edges}

    def get_tree(self) -> Dict[str, Any]:
        """
        Build nested category tree for UI sidebar explorer.
        """
        self.scaffold()
        notes = self.list_notes()

        tree: Dict[str, Any] = {
            "inbox": [],
            "notes": {},  # domain -> topic -> list of notes
            "resources": {
                "operating_manuals": [],
                "templates": [],
            },
            "archive": [],
            "00_Inbox": [],
            "01_Notes": {},
            "02_Resources": {
                "operating_manuals": [],
                "templates": [],
            },
            "03_Archive": [],
        }

        for n in notes:
            path_parts = n["path"].split("/")
            raw_root = path_parts[0]
            clean_root = re.sub(r"^\d+_", "", raw_root).lower()

            if clean_root == "inbox" or raw_root.lower() == "inbox":
                tree["inbox"].append(n)
                tree["00_Inbox"].append(n)
            elif clean_root in ("resources", "templates", "operating_manuals") or raw_root.lower() == "resources":
                sub = "operating_manuals"
                if len(path_parts) >= 3:
                    sub = re.sub(r"^\d+_", "", path_parts[1]).lower()
                    if sub.startswith("_"):
                        sub = sub.lstrip("_").lower()
                elif clean_root in ("templates", "_templates"):
                    sub = "templates"
                tree["resources"].setdefault(sub, []).append(n)
                tree["02_Resources"].setdefault(sub, []).append(n)
            elif clean_root == "archive" or raw_root.lower() == "archive":
                tree["archive"].append(n)
                tree["03_Archive"].append(n)
            elif clean_root in ("notes", "projects", "areas") or raw_root.lower() == "notes":
                if len(path_parts) >= 4:
                    domain = path_parts[1]
                    topic = path_parts[2]
                elif len(path_parts) == 3:
                    domain = path_parts[1]
                    topic = n.get("topic") if n.get("topic") and n.get("topic") != "general" else domain
                elif len(path_parts) == 2:
                    domain = "general"
                    topic = n.get("topic") or "general"
                else:
                    domain = "general"
                    topic = "general"
                tree["notes"].setdefault(domain, {}).setdefault(topic, []).append(n)
                tree["01_Notes"].setdefault(domain, {}).setdefault(topic, []).append(n)
            else:
                domain = raw_root
                topic = path_parts[1] if len(path_parts) >= 3 else "general"
                tree["notes"].setdefault(domain, {}).setdefault(topic, []).append(n)
                tree["01_Notes"].setdefault(domain, {}).setdefault(topic, []).append(n)

        return tree

    def get_overview(self, max_items: int = 20) -> str:
        """
        Generate a compact, prompt-ready text inventory under 150 tokens.
        """
        notes = self.list_notes()
        if not notes:
            return "Wiki is currently empty. Direct the Librarian to file notes."

        lines = [f"Wiki Vault: {len(notes)} total notes."]
        by_cat: Dict[str, List[Dict[str, Any]]] = {}
        for n in notes:
            root = n["path"].split("/")[0]
            by_cat.setdefault(root, []).append(n)

        for cat, items in sorted(by_cat.items()):
            lines.append(f"- {cat}/ ({len(items)} notes):")
            for item in items[: max(2, max_items // max(1, len(by_cat)))]:
                lines.append(f"  * {item['title']} (path: {item['path']})")

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics across the wiki."""
        notes = self.list_notes()
        total_words = sum(n["word_count"] for n in notes)
        total_tokens = sum(n["context_tokens"] for n in notes)
        by_category: Dict[str, int] = {}
        for n in notes:
            root = n["path"].split("/")[0]
            by_category[root] = by_category.get(root, 0) + 1

        return {
            "total_notes": len(notes),
            "total_words": total_words,
            "total_tokens": total_tokens,
            "by_category": by_category,
        }
