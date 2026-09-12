"""Repo/code fail-closed grounding [CARD-262].

Code-aware Homelab-class asks must use catalog repo_file_read / repo_file_list.
Jobs may claim only what was actually read — never invent-about-checkout.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

logger = logging.getLogger(__name__)

ACTION_SKIP = "skip_not_repo"
ACTION_REQUIRE_READ = "require_tool_read"
ACTION_HONEST_FAIL = "honest_fail_no_read"

REPO_NEED_READ_REASON = "repo_need_tool_read"

_REPO_ASK_RE = re.compile(
    r"\b(agents\.md|repo_file_read|repo_file_list|checkout|source file|"
    r"source code|codebase|repository|what does .+ say about|"
    r"\.github/cards|read (the )?(file|repo|checkout))\b",
    re.IGNORECASE,
)
_SOURCE_DEP_RE = re.compile(
    r"\b(using repo_file_read|via repo_file_read|cite(d|s)? (only )?content|"
    r"only (content |what )?returned by|what does (AGENTS\.md|.+\.md) say|"
    r"from (the )?(checkout|repo|AGENTS\.md)|ground(ed)? on (repo|checkout))\b",
    re.IGNORECASE,
)
# Checkout-relative path claims (not Wiki 00_Inbox).
_PATH_RE = re.compile(
    r"(?P<path>(?:AGENTS\.md|CHANGELOG\.md|README\.md|"
    r"(?:src|tests|docs|notes|scripts|steering|platform-packs|\.github|"
    r"\.agents|deploy|skills|packs)"
    r"(?:/[\w.\-]+)+|"
    r"[\w.\-]+\.md))",
    re.IGNORECASE,
)
_FAKE_OR_MISSING_HINT = re.compile(
    r"TotallyFake|does not exist|File not found|not found|failed to read",
    re.IGNORECASE,
)

_PROVENANCE_TOOLS = frozenset(
    {
        "repo_file_read",
        "repo_file_list",
        "tool.repo_file_read",
        "tool.repo_file_list",
    }
)


@dataclass(frozen=True)
class RepoGroundingDecision:
    """Deterministic code-awareness grounding decision [REQ-REPO-003]."""

    action: str
    reason: str
    topic_query: str
    require_tool: bool = True
    source_dependent: bool = False
    suggested_paths: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "reason": self.reason,
            "topic_query": self.topic_query,
            "require_tool": self.require_tool,
            "source_dependent": self.source_dependent,
            "suggested_paths": list(self.suggested_paths),
            "need_repo_read": self.action == ACTION_REQUIRE_READ,
        }


def is_repo_code_ask(intent: str | None) -> bool:
    text = (intent or "").strip()
    if not text:
        return False
    if _REPO_ASK_RE.search(text):
        return True
    lower = text.lower()
    return "repo_file_" in lower or "agents.md" in lower


def is_repo_source_dependent_ask(intent: str | None) -> bool:
    text = (intent or "").strip()
    if not text:
        return False
    return bool(_SOURCE_DEP_RE.search(text)) or is_repo_code_ask(text)


def extract_suggested_repo_paths(intent: str | None) -> tuple[str, ...]:
    text = intent or ""
    out: list[str] = []
    for m in _PATH_RE.finditer(text):
        p = normalize_repo_path(m.group("path"))
        if p and p not in out and "..." not in p:
            out.append(p)
    # Always suggest AGENTS.md when mentioned.
    if "agents.md" in text.lower() and "AGENTS.md" not in out:
        out.insert(0, "AGENTS.md")
    return tuple(out)


def normalize_repo_path(path: str | None) -> str:
    p = (path or "").strip().replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p.lstrip("/")


def assess_repo_code_grounding(
    intent: str | None,
    *,
    provenanced_paths: Sequence[str] | None = None,
    read_failed: bool = False,
) -> RepoGroundingDecision:
    """Decide grounding posture for a code-aware ask.

    - Not repo-related => skip
    - Repo-related (mint / pre-tool) => require_tool_read + constraint
    - Source-dependent + failed/missing read => honest_fail_no_read
    """
    text = (intent or "").strip()
    if not is_repo_code_ask(text):
        return RepoGroundingDecision(
            action=ACTION_SKIP,
            reason="not_repo_code_ask",
            topic_query="",
            require_tool=False,
            source_dependent=False,
        )
    suggested = extract_suggested_repo_paths(text)
    topic = " ".join(suggested) if suggested else "checkout"
    source_dep = is_repo_source_dependent_ask(text)
    provenanced = [normalize_repo_path(p) for p in (provenanced_paths or []) if normalize_repo_path(p)]

    if read_failed or (source_dep and provenanced_paths is not None and not provenanced):
        return RepoGroundingDecision(
            action=ACTION_HONEST_FAIL,
            reason="repo_read_failed_or_missing",
            topic_query=topic,
            require_tool=True,
            source_dependent=source_dep,
            suggested_paths=suggested,
        )
    return RepoGroundingDecision(
        action=ACTION_REQUIRE_READ,
        reason=REPO_NEED_READ_REASON,
        topic_query=topic,
        require_tool=True,
        source_dependent=source_dep,
        suggested_paths=suggested,
    )


def format_repo_grounding_constraint_block(decision: RepoGroundingDecision) -> str:
    """Inject into Formulate/Execute — must use repo tools; no invent."""
    suggested = (
        ", ".join(f"`{p}`" for p in decision.suggested_paths)
        if decision.suggested_paths
        else "(use repo_file_list then repo_file_read)"
    )
    return (
        "REPO / CODE GROUNDING CONSTRAINT [CARD-262 / fail-closed]:\n"
        f"- action={decision.action}; reason={decision.reason}\n"
        f"- Suggested checkout paths: {suggested}\n"
        "- You MUST call catalog tool `repo_file_read` (and/or `repo_file_list`) "
        "before claiming anything about checkout files.\n"
        "- Claim ONLY content/paths returned by those tools in this Job.\n"
        "- If a read fails or the file is missing: honest fail / park — "
        "never invent AGENTS.md or source contents (Homelab-class ban)."
    )


def format_repo_honest_fail_message(
    decision: RepoGroundingDecision,
    *,
    job_id: str | None = None,
    error: str | None = None,
) -> str:
    job_bit = f" Job {job_id}." if job_id else ""
    err_bit = f" Error: {error}." if error else ""
    paths = ", ".join(f"`{p}`" for p in decision.suggested_paths) or "(unknown)"
    return (
        f"Not done — checkout read missing or failed.{job_bit}{err_bit} "
        f"Requested path(s): {paths}. "
        "Fail-closed repo grounding: will not invent checkout file contents. "
        "Use repo_file_read on a real path under the checkout, then resume."
    )


def collect_provenanced_repo_paths_from_tool_result(
    tool_name: str | None,
    result: Any,
) -> list[str]:
    """Extract checkout paths from successful *repo_file_read* only.

    repo_file_list can prove directory inventory but must NOT satisfy
    content grounding for source-dependent asks (CARD-262).
    """
    name = (tool_name or "").strip()
    if name not in {"repo_file_read", "tool.repo_file_read"} and not name.endswith(
        "repo_file_read"
    ):
        return []
    payload: Any = result
    if isinstance(result, str):
        text = result.strip()
        try:
            payload = json.loads(text)
        except Exception:
            return []
    paths: list[str] = []
    if isinstance(payload, Mapping):
        if payload.get("success") is False:
            return []
        for key in ("path", "relative_path"):
            p = normalize_repo_path(str(payload.get(key) or ""))
            if p and p != "." and p not in paths:
                paths.append(p)
    return paths


def extract_claimed_repo_paths(text: str | None) -> list[str]:
    out: list[str] = []
    for m in _PATH_RE.finditer(text or ""):
        p = normalize_repo_path(m.group("path"))
        if not p or "..." in p:
            continue
        # Skip pure Wiki-looking inbox paths — those are CARD-260.
        if p.lower().startswith(("00_inbox/", "01_notes/", "02_resources/")):
            continue
        if p not in out:
            out.append(p)
    return out


def ungrounded_claimed_repo_paths(
    text: str | None,
    provenanced: Sequence[str] | None,
) -> list[str]:
    allowed = {normalize_repo_path(p).lower() for p in (provenanced or []) if normalize_repo_path(p)}
    bad: list[str] = []
    for claim in extract_claimed_repo_paths(text):
        if claim.lower() not in allowed and claim not in bad:
            bad.append(claim)
    return bad


def format_ungrounded_repo_claim_honesty(
    ungrounded: Sequence[str],
    provenanced: Sequence[str] | None = None,
    *,
    job_id: str | None = None,
) -> str:
    job_bit = f" Job {job_id}." if job_id else ""
    bad = ", ".join(f"`{p}`" for p in ungrounded) or "(unknown)"
    ok = ", ".join(f"`{p}`" for p in (provenanced or []) if p) or "(none)"
    return (
        f"Not done — ungrounded checkout path claim.{job_bit} "
        f"Invented/unprovenanced path(s): {bad}. "
        f"Tool-provenanced paths this Job: {ok}. "
        "Fail-closed: only claim paths returned by repo_file_read / repo_file_list."
    )


def apply_standing_repo_code_grounding(
    orch: Any,
    job: Any,
    *,
    intent: str | None = None,
) -> RepoGroundingDecision:
    """Assess + persist decision on orchestrator for standing Chat [REQ-REPO-003]."""
    goal = intent if intent is not None else getattr(job, "goal", None) or ""
    decision = assess_repo_code_grounding(goal)
    try:
        store = getattr(orch, "_decisions", None)
        if store is None:
            orch._repo_grounding_by_job = getattr(orch, "_repo_grounding_by_job", {})
            orch._repo_grounding_by_job[getattr(job, "id", "")] = decision
        else:
            store[getattr(job, "id", "")] = decision
    except Exception:
        logger.warning("repo grounding persist soft-fail", exc_info=True)
    try:
        facts = getattr(orch, "append_job_fact", None) or getattr(orch, "record_fact", None)
        # Best-effort durable note via existing helpers if present
        lines = [
            f"repo_code_grounding: action={decision.action}",
            f"repo_code_grounding: reason={decision.reason}",
            f"repo_code_grounding: suggested={list(decision.suggested_paths)[:8]}",
        ]
        ckpt = getattr(orch, "update_checkpoint", None)
        if callable(ckpt):
            try:
                ckpt(
                    getattr(job, "id", None),
                    kind="repo_code_grounding",
                    payload=decision.as_dict(),
                )
            except TypeError:
                pass
        logger.info(" | ".join(lines))
    except Exception:
        pass
    return decision


def grounding_for_job(orch: Any, job_id: str) -> Optional[RepoGroundingDecision]:
    by_job = getattr(orch, "_repo_grounding_by_job", None) or {}
    dec = by_job.get(job_id)
    if isinstance(dec, RepoGroundingDecision):
        return dec
    return None


def should_honest_fail_after_turn(
    intent: str | None,
    provenanced_paths: Sequence[str] | None,
    final_content: str | None = None,
) -> bool:
    """True when source-dependent code ask ended with no successful repo_file_read.

    If the ask named specific checkout paths, at least one must appear in
    repo_file_read provenance — list-only grounding does not count.
    """
    if not is_repo_source_dependent_ask(intent):
        return False
    provenanced = {
        normalize_repo_path(p).lower()
        for p in (provenanced_paths or [])
        if normalize_repo_path(p)
    }
    suggested = {
        normalize_repo_path(p).lower()
        for p in extract_suggested_repo_paths(intent)
        if normalize_repo_path(p)
    }
    if suggested:
        if provenanced.intersection(suggested):
            return False
        return True
    if provenanced:
        return False
    _ = final_content
    return True


__all__ = [
    "ACTION_HONEST_FAIL",
    "ACTION_REQUIRE_READ",
    "ACTION_SKIP",
    "REPO_NEED_READ_REASON",
    "RepoGroundingDecision",
    "apply_standing_repo_code_grounding",
    "assess_repo_code_grounding",
    "collect_provenanced_repo_paths_from_tool_result",
    "extract_claimed_repo_paths",
    "extract_suggested_repo_paths",
    "format_repo_grounding_constraint_block",
    "format_repo_honest_fail_message",
    "format_ungrounded_repo_claim_honesty",
    "grounding_for_job",
    "is_repo_code_ask",
    "is_repo_source_dependent_ask",
    "normalize_repo_path",
    "should_honest_fail_after_turn",
    "ungrounded_claimed_repo_paths",
]
