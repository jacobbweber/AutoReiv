"""hand_off_card: the one way Architect starts Developer on a Ready card [CARD-563].

Every rule lives here, not in skill text: a selected project, a Ready card in it, Architect as the caller, no other
card In Progress, and a Developer to hand to. Developer gets a fixed directive and the card id only (the card is the
brief). The tool is always an approval prompt (DEFAULT_HIGH_RISK_TOOLS), so each hand-off is one click for Jacob.
When Developer stops, the outcome is read from git and the card file, never taken from the model's summary.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.sdlc.paths import ProjectPathError

HAND_OFF_TOOL = "hand_off_card"
DEVELOPER_ID = "developer"
ARCHITECT_ID = "architect"
CARD_HANDOFF_PAYLOAD_KEY = "card_handoff"


def card_directive(card_id: str) -> str:
    return f"Work card {card_id} to In Review in the active project."


def _failed(msg: str) -> str:
    return f"=== Hand-off refused ===\n{msg}"


def evidence_block(card_text: str) -> List[str]:
    """The tool-written Evidence lines set_card_status(In Review) recorded (CARD-562), or []."""
    from src.application.skills.card_tools import EVIDENCE_AUTO_HEADER

    lines = card_text.replace("\r\n", "\n").split("\n")
    for i, line in enumerate(lines):
        if line.strip() == EVIDENCE_AUTO_HEADER:
            out = [line]
            for nxt in lines[i + 1 :]:
                if not nxt.strip().startswith("- "):
                    break
                out.append(nxt)
            return out
    return []


def card_outcome(root: Path, card_id: str, card_tools: Any, developer_session_id: str = "") -> str:
    """What happened, read from the card file and git (not from Developer's own summary)."""
    from src.application.sdlc.check_record import NO_GIT_HEAD, git_branch, git_dirty_paths, git_head, run_git
    from src.domain.sdlc.agents_contract import parse_agents_md
    from src.domain.sdlc.models import normalize_status, parse_card_frontmatter

    lines = [f"=== Hand-off outcome: {card_id} (read from git and the card file) ==="]
    try:
        path = card_tools._find_card_path(root, card_id=card_id)
        text = path.read_text(encoding="utf-8")
        status = normalize_status(parse_card_frontmatter(text).status or "") or "?"
    except (FileNotFoundError, OSError):
        path, text, status = None, "", "card file not found on this branch"
    lines.append(f"Card status: {status}")
    if git_head(root) != NO_GIT_HEAD:
        agents = root / "AGENTS.md"
        contract = parse_agents_md(agents.read_text(encoding="utf-8", errors="replace") if agents.is_file() else "")
        base = contract.base_branch or "main"
        lines.append(f"Branch: {git_branch(root)} (base {base})")
        log = run_git(root, ["log", "--format=%h %s", f"{base}..HEAD"])
        commits = [c for c in log.stdout.splitlines() if c.strip()] if log.returncode == 0 else []
        lines.append(f"Commits since {base}: " + (str(len(commits)) if commits else "none"))
        lines.extend(f"  {c}" for c in commits)
        dirty = git_dirty_paths(root)
        lines.append("Working tree: clean" if not dirty else "Working tree: uncommitted " + ", ".join(dirty[:8]))
    evidence = evidence_block(text)
    lines.append("Evidence (tool-written):" if evidence else "Evidence: no tool-written Evidence block on the card.")
    lines.extend(evidence[1:] if evidence else [])
    if developer_session_id:
        lines.append(f"Developer conversation: {developer_session_id} (open Developer in Chat to see every step)")
    if status != "In Review":
        lines.append("Developer did not reach In Review. Read the Developer conversation, then decide with Jacob.")
    return "\n".join(lines)


class CardHandoffTools:
    """Registers hand_off_card. Collaborators are passed in so the tool is testable without a server."""

    def __init__(
        self,
        root_resolver: Callable[[Optional[str]], Path],
        card_tools: Any,
        handoff_engine: Any,
        agent_registry: Any = None,
    ):
        self._root_resolver = root_resolver
        self._card_tools = card_tools
        self._engine = handoff_engine
        self._agents = agent_registry if agent_registry is not None else getattr(handoff_engine, "agent_registry", None)
        hooks = getattr(handoff_engine, "parent_tool_outcomes", None)
        if isinstance(hooks, dict):
            hooks[HAND_OFF_TOOL] = self._outcome_after_resume

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        registry.register_tool(
            name=HAND_OFF_TOOL,
            description=(
                "Hand a Ready card in the active project to Developer, who works it to In Review on a card branch. "
                "Asks Jacob to approve, then waits for Developer and returns the outcome read from git and the card."
            ),
            parameters={
                "type": "object",
                "properties": {"card_id": {"type": "string", "description": "The Ready card, e.g. CARD-2."}},
                "required": ["card_id"],
            },
            handler=self.hand_off_card,
        )

    def _developer(self) -> Any:
        if self._agents is None:
            return None
        for getter in ("get_agent", "get_profile"):
            fn = getattr(self._agents, getter, None)
            prof = fn(DEVELOPER_ID) if callable(fn) else None
            if prof is not None:
                return prof
        return None

    def refusal(self, card_id: str, actor: str) -> tuple[str, Optional[Path], str]:
        """(refusal message or "", project root, normalized card id)."""
        from src.domain.sdlc.models import extract_card_id, normalize_status, parse_card_frontmatter

        if actor != ARCHITECT_ID:
            return "Only Architect hands cards to Developer. Ask Architect, or open Developer and say 'Work card CARD-N'.", None, ""
        try:
            root = Path(self._root_resolver(None)).resolve()
        except ProjectPathError as exc:
            return str(exc), None, ""
        cid = (extract_card_id("", str(card_id or "")) or str(card_id or "")).strip().upper()
        if not cid:
            return "card_id is required, e.g. CARD-2.", root, ""
        try:
            path = self._card_tools._find_card_path(root, card_id=cid)
        except (FileNotFoundError, ProjectPathError):
            return f"{cid} is not a card in the active project ({root.name}). list_cards shows the cards here.", root, cid
        status = normalize_status(parse_card_frontmatter(path.read_text(encoding="utf-8")).status or "")
        if status != "Ready":
            return (
                f"{cid} is {status or 'without a status'}, not Ready. Make it Ready first "
                "(set_card_status Ready, once Jacob agrees the card is clear), then hand it off.",
                root,
                cid,
            )
        busy = [
            c.get("id")
            for c in (self._card_tools.list_cards(status="In Progress").get("cards") or [])
            if c.get("id") != cid
        ]
        if busy:
            return (
                f"{', '.join(str(b) for b in busy)} is already In Progress in this project. One card at a time: "
                "let Developer finish it (or Jacob moves it back) before handing off another.",
                root,
                cid,
            )
        dev = self._developer()
        if dev is None or getattr(dev, "enabled", True) is False:
            return "Developer is not available (missing or disabled). Enable Developer in Agents, then try again.", root, cid
        return "", root, cid

    async def hand_off_card(self, card_id: str) -> Any:
        from src.application.kernel.tool_registry import get_tool_context
        from src.application.orchestration.handoff_engine import infer_handoff_depth
        from src.domain.orchestration.models import HandoffEnvelope, HandoffPacket

        ctx = get_tool_context()
        actor = str(ctx.get("agent_id") or "").lower()
        refused, root, cid = self.refusal(card_id, actor)
        if refused:
            return _failed(refused)
        session_id = str(ctx.get("session_id") or "default_session")
        packet = HandoffPacket(
            goal=card_directive(cid),
            facts=[f"card_id: {cid}"],
            constraints=["The card is the brief: read it with read_card before working."],
            done_when=f"{cid} is In Review (set_card_status), or you stop and say why.",
            budget={"max_turns": 40},
        )
        envelope = HandoffEnvelope(
            sender_agent_id=ARCHITECT_ID,
            recipient_agent_id=DEVELOPER_ID,
            session_id=session_id,
            task_intent=packet.goal,
            context_payload={CARD_HANDOFF_PAYLOAD_KEY: cid, "child_session_title": f"{cid}: handed off by Architect"},
            approval_mode="run" if str(ctx.get("approval_mode") or "").lower() == "run" else "ask",
            depth=infer_handoff_depth(session_id),
            max_turns=40,
            packet=packet,
        )
        from src.application.orchestration.handoff_engine import child_session_id_for

        child_id = child_session_id_for(envelope)
        result = await self._engine.execute_handoff(envelope)
        if result.status == "approval_required" and result.approval_id:
            return {
                "status": "approval_required",
                "approval_id": result.approval_id,
                "tool_name": result.parked_tool_name or "tool",
                "arguments": result.parked_arguments or {},
                "message": result.error_message or result.summary,
                "recipient_agent_id": result.recipient_agent_id,
                "developer_session_id": child_id,
            }
        if result.status in ("rejected", "failed", "timed_out"):
            return (
                f"=== Hand-off {result.status}: {cid} ===\n{result.error_message or 'Developer did not finish.'}\n"
                + card_outcome(root, cid, self._card_tools, child_id)
            )
        own = (result.summary or "").strip()
        return card_outcome(root, cid, self._card_tools, child_id) + (
            "\n\nDeveloper's own summary:\n" + own[-1500:] if own else ""
        )

    def _outcome_after_resume(self, arguments: Dict[str, Any], child_session_id: str) -> str:
        """Called by HandoffEngine when a parked Developer run finishes after Jacob's approvals."""
        from src.domain.sdlc.models import extract_card_id

        raw = str((arguments or {}).get("card_id") or "")
        cid = (extract_card_id("", raw) or raw).strip().upper()
        try:
            root = Path(self._root_resolver(None)).resolve()
        except ProjectPathError as exc:
            return f"Outcome unavailable: {exc}"
        return card_outcome(root, cid, self._card_tools, child_session_id)
