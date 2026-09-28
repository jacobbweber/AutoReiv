"""review_card and finish_review: Architect reviews Developer's In Review work [CARD-564].

Every rule lives here, not in skill text. review_card is read-only: it reads the card, the diff against base and the
commit log itself and re-runs the project's AGENTS.md checks for the current HEAD (the green run is recorded in the
CARD-562 check record; nothing is written in the project). finish_review records the verdict:
- Done needs a written review, the card branch checked out with a clean tree, and a green check for the current HEAD.
- Returned needs written review notes and is refused on the last round (round N = review_rounds + 1; the third of
  max_review_rounds 3 cannot Return): the card goes to Jacob instead.
Both write the review to the card's ``## Review`` section and commit only the card file. Neither asks for approval
(Jacob's merge is the gate, CARD-564 D1) and neither merges, pushes or notifies (D3).
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.sdlc.paths import ProjectPathError

REVIEW_TOOL = "review_card"
FINISH_TOOL = "finish_review"
ARCHITECT_ID = "architect"
MIN_REVIEW_CHARS = 20
DIFF_CAP_CHARS = 12000
CARD_CAP_CHARS = 6000


def _refused(tool: str, msg: str) -> str:
    title = "Review refused" if tool == REVIEW_TOOL else "Verdict refused"
    return f"=== {title} ===\n{msg}"


def evidence_branch(card_text: str) -> str:
    """The branch set_card_status(In Review) wrote into the card's Evidence, or ''."""
    from src.application.skills.card_handoff_tools import evidence_block

    for line in evidence_block(card_text)[1:]:
        m = re.match(r"^- Branch: `([^`]+)`", line.strip())
        if m:
            return m.group(1)
    return ""


def append_review_round(card_text: str, round_no: int, verdict: str, review: str, when: str) -> str:
    """Add '### Round N - verdict (date)' to ## Review (created before ## Findings or at the end); keeps earlier rounds."""
    text = card_text.replace("\r\n", "\n")
    if not text.endswith("\n"):
        text += "\n"
    block = f"### Round {round_no} - {verdict} ({when})\n{review.strip()}\n"
    m = re.search(r"(?m)^##\s+Review\s*$", text)
    if m:
        nxt = re.search(r"(?m)^##\s+", text[m.end():])
        end = m.end() + nxt.start() if nxt else len(text)
        section = text[m.end():end].rstrip("\n")
        return text[: m.end()] + section + "\n\n" + block + ("\n" if nxt else "") + text[end:]
    f = re.search(r"(?m)^##\s+(Findings|Results|Release note)\s*$", text)
    new = "## Review\n\n" + block + "\n"
    if f:
        return text[: f.start()] + new + text[f.start():]
    return text + "\n" + new


class CardReviewTools:
    """Registers review_card and finish_review. Collaborators are passed in so the tools are testable without a server."""

    def __init__(
        self,
        root_resolver: Callable[[Optional[str]], Path],
        card_tools: Any,
        dev_tools: Any,
        check_record: Any = None,
    ):
        from src.application.sdlc.check_record import default_record

        self._root_resolver = root_resolver
        self._cards = card_tools
        self._dev = dev_tools
        self._check_record = check_record or getattr(card_tools, "_check_record", None) or default_record()

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        registry.register_tool(
            name=REVIEW_TOOL,
            description=(
                "Architect: read an In Review card for review. Returns the card, the diff and commits against base, and a "
                "fresh run of the project's checks for the current HEAD. Read-only. Then call finish_review."
            ),
            parameters={
                "type": "object",
                "properties": {"card_id": {"type": "string", "description": "The In Review card, e.g. CARD-3."}},
                "required": ["card_id"],
            },
            handler=self.review_card,
            risk="read",
        )
        registry.register_tool(
            name=FINISH_TOOL,
            description=(
                "Architect: record the review verdict on an In Review card after review_card. verdict Done (every "
                "acceptance item met, checks green) or Returned (what must change). The review is written on the card "
                "and only the card file is committed. Never merges or pushes."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "card_id": {"type": "string", "description": "The In Review card, e.g. CARD-3."},
                    "verdict": {"type": "string", "enum": ["Done", "Returned"]},
                    "review": {
                        "type": "string",
                        "description": "The written review: one line per acceptance item (met or not, with file and "
                        "behaviour). For Returned, the specific changes Developer must make.",
                    },
                },
                "required": ["card_id", "verdict", "review"],
            },
            handler=self.finish_review,
        )

    # --- shared checks --------------------------------------------------------
    def _card_state(self, tool: str, card_id: str) -> Tuple[str, Dict[str, Any]]:
        """(refusal or '', state) for an Architect call on an In Review card with the card branch checked out."""
        from src.application.kernel.tool_registry import get_tool_context
        from src.application.sdlc.check_record import NO_GIT_HEAD, git_branch, git_dirty_paths, git_head
        from src.application.skills.card_tools import CARD_DIRS
        from src.application.skills.git_tools import PROTECTED_COMMIT_BRANCHES
        from src.domain.sdlc.agents_contract import parse_agents_md
        from src.domain.sdlc.models import extract_card_id, normalize_status, parse_card_frontmatter

        actor = str(get_tool_context().get("agent_id") or "").lower()
        if actor != ARCHITECT_ID:
            return "Only Architect reviews cards with this tool. Jacob reviews by hand otherwise.", {}
        try:
            root = Path(self._root_resolver(None)).resolve()
        except ProjectPathError as exc:
            return str(exc), {}
        cid = (extract_card_id("", str(card_id or "")) or str(card_id or "")).strip().upper()
        if not cid:
            return "card_id is required, e.g. CARD-3.", {}
        try:
            path = self._cards._find_card_path(root, card_id=cid)
        except (FileNotFoundError, ProjectPathError):
            return f"{cid} is not a card in the active project ({root.name}). list_cards shows the cards here.", {}
        text = path.read_text(encoding="utf-8")
        fm = parse_card_frontmatter(text)
        status = normalize_status(fm.status or "")
        head = git_head(root)
        if status != "In Review":
            where = git_branch(root) if head != NO_GIT_HEAD else ""
            hint = (
                f" The project is on '{where}': an In Review card lives on its card branch. Architect does not switch "
                "branches; ask Jacob to check out the card branch."
                if where in PROTECTED_COMMIT_BRANCHES
                else ""
            )
            return (
                f"{cid} is {status or 'without a status'}, not In Review. Only In Review cards are reviewed"
                + (" (a Returned card goes back to Developer with hand_off_card)." if status == "Returned" else ".")
                + hint,
                {},
            )
        if head == NO_GIT_HEAD:
            return "The active project is not a git repository with a commit: there is no diff to review.", {}
        branch = git_branch(root)
        want = evidence_branch(text)
        if branch in PROTECTED_COMMIT_BRANCHES or branch in ("", "HEAD") or (want and branch != want):
            return (
                f"The project is on '{branch or 'a detached HEAD'}', not the card branch"
                + (f" '{want}'" if want else "")
                + ". Architect does not switch branches: ask Jacob to check out the card branch, then review again.",
                {},
            )
        card_rel = path.resolve().relative_to(root).as_posix()
        dirty = [p for p in git_dirty_paths(root) if p != card_rel and not any(p.startswith(d + "/") for d in CARD_DIRS)]
        if dirty:
            return (
                "Uncommitted changes in the project (" + ", ".join(dirty[:6]) + "): the review would not match the "
                "branch. Ask Jacob or Developer to commit or discard them, then review again.",
                {},
            )
        agents = root / "AGENTS.md"
        contract = parse_agents_md(agents.read_text(encoding="utf-8", errors="replace") if agents.is_file() else "")
        rounds, max_rounds = fm.review_rounds, fm.max_review_rounds
        return "", {
            "root": root, "cid": cid, "path": path, "text": text, "fm": fm, "head": head, "branch": branch,
            "base": contract.base_branch or "main", "checks": dict(contract.checks), "round": rounds + 1,
            "max_rounds": max_rounds, "card_rel": card_rel,
        }

    # --- review_card ----------------------------------------------------------
    def review_card(self, card_id: str) -> str:
        from src.application.sdlc.check_record import run_git

        refused, st = self._card_state(REVIEW_TOOL, card_id)
        if refused:
            return _refused(REVIEW_TOOL, refused)
        root, base, cid = st["root"], st["base"], st["cid"]
        log = run_git(root, ["log", "--format=%h %s", f"{base}..HEAD"])
        commits = [c for c in log.stdout.splitlines() if c.strip()] if log.returncode == 0 else []
        excl = [":(exclude).agents/cards", ":(exclude)docs/cards", ":(exclude).github/cards"]
        stat = run_git(root, ["diff", "--stat", f"{base}...HEAD", "--", ".", *excl]).stdout.strip()
        patch = run_git(root, ["diff", f"{base}...HEAD", "--", ".", *excl]).stdout
        cut = len(patch) > DIFF_CAP_CHARS
        which = "fast" if "fast" in st["checks"] else "all"
        checks = self._dev.run_project_checks(check=which) if st["checks"] else {
            "success": False, "error": "AGENTS.md has no '## Checks' commands."}
        if checks.get("success"):
            ran = "; ".join(
                f"{r.get('check')} (`{r.get('command')}`): {'passed' if r.get('passed') else 'FAILED'}"
                for r in checks.get("results") or []
            )
            green = bool(checks.get("passed")) and bool(checks.get("green_recorded"))
            check_line = f"Checks for HEAD {st['head'][:12]}: {ran}" + (" - green recorded" if green else "")
            fail_tail = "" if checks.get("passed") else "\n".join(
                (r.get("output_tail") or "")[-1500:] for r in checks.get("results") or [] if not r.get("passed"))
        else:
            check_line, fail_tail = f"Checks could not run: {checks.get('error')}", ""
        last = st["round"] + 1 >= st["max_rounds"]
        card_text = st["text"].replace("\r\n", "\n")
        lines = [
            f"=== Review packet: {cid} (round {st['round']} of {st['max_rounds']}; read from git and the card file) ===",
            "Card status: In Review",
            f"Branch: {st['branch']} (base {base})",
            f"Commits since {base}: " + (str(len(commits)) if commits else "none"),
            *[f"  {c}" for c in commits],
            check_line,
        ]
        if fail_tail:
            lines += ["Failing check output (tail):", fail_tail]
        lines += [
            "",
            "Diff stat (code, card folders excluded):",
            stat or "(no code changes against base)",
            "",
            "Diff" + (f" (first {DIFF_CAP_CHARS} characters; read_project_file for the rest)" if cut else "") + ":",
            patch[:DIFF_CAP_CHARS] or "(empty)",
            "",
            "Card:" + (f" (first {CARD_CAP_CHARS} characters)" if len(card_text) > CARD_CAP_CHARS else ""),
            card_text[:CARD_CAP_CHARS],
            "",
            "Next: compare every acceptance item with the diff and the checks, then call finish_review with verdict "
            "Done or Returned and a written review (one line per acceptance item; for Returned, what must change).",
        ]
        if last:
            lines.append(
                f"This is the last review round ({st['round']} of {st['max_rounds']}): Returned is not possible. "
                "If it is not Done, bring the card to Jacob with your review."
            )
        return "\n".join(lines)

    # --- finish_review --------------------------------------------------------
    def finish_review(self, card_id: str, verdict: str, review: str) -> str:
        from src.domain.sdlc.models import normalize_status, parse_card_frontmatter, serialize_card_frontmatter

        wanted = normalize_status(str(verdict or ""))
        if wanted not in ("Done", "Returned"):
            return _refused(FINISH_TOOL, "verdict must be Done or Returned.")
        refused, st = self._card_state(FINISH_TOOL, card_id)
        if refused:
            return _refused(FINISH_TOOL, refused)
        cid, root, path = st["cid"], st["root"], st["path"]
        notes = (review or "").strip()
        if len(notes) < MIN_REVIEW_CHARS:
            return _refused(
                FINISH_TOOL,
                "Write the review first: one line per acceptance item (met or not, naming file and behaviour)"
                + ("; for Returned, the specific changes Developer must make." if wanted == "Returned" else "."),
            )
        if wanted == "Done":
            rec = self._check_record.get(root) or {}
            if rec.get("head") != st["head"]:
                return _refused(
                    FINISH_TOOL,
                    f"No green check recorded for the current HEAD {st['head'][:12]}. Run review_card {cid} (it re-runs "
                    "the checks), read the result, then finish_review again. Done needs green checks on this HEAD.",
                )
        elif st["round"] + 1 >= st["max_rounds"]:
            return _refused(
                FINISH_TOOL,
                f"This is review round {st['round']} of {st['max_rounds']}: Architect cannot Return {cid} again. "
                "Bring the card to Jacob with your review; Jacob decides (Done, more work, or raise max_review_rounds).",
            )
        text = st["text"]
        fm = parse_card_frontmatter(text)
        if wanted == "Returned":
            fm.return_reason = notes.splitlines()[0][:300]
            fm.review_rounds = fm.review_rounds + 1
        else:
            fm.fields["completed"] = date.today().isoformat()
        fm.status = wanted
        rendered = append_review_round(serialize_card_frontmatter(fm), st["round"], wanted, notes, date.today().isoformat())
        path.write_text(rendered, encoding="utf-8")
        message = f"docs(card): {cid} Done" if wanted == "Done" else f"docs(card): {cid} Returned (round {st['round']})"
        committed = self._cards._commit_card(root, path, cid, message=message)
        if not committed.get("success", True):
            path.write_text(text, encoding="utf-8")
            return _refused(FINISH_TOOL, committed.get("error") or "Committing the card failed.")
        out = [
            f"=== Review {wanted}: {cid} (round {st['round']} of {st['max_rounds']}) ===",
            f"Card status: {wanted}",
            f"Branch: {st['branch']} (base {st['base']})",
            f"Card commit: {committed.get('commit') or '-'} {message}",
            "Review written to the card (## Review).",
        ]
        if wanted == "Done":
            out.append(f"Nothing merged or pushed: Jacob merges {st['branch']} into {st['base']} when he is happy.")
        else:
            out.append(f"Next: when Jacob agrees, hand_off_card {cid} sends it back to Developer to address the notes.")
        return "\n".join(out)
