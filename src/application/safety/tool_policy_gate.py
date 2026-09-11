"""Tool Policy Gate [CARD-221 / REQ-TOOLPOL-001..006].

ALLOW / REQUIRE_CONFIRM / BLOCK after model intent, before executor.
Registry listing is not authorization. Extends HITL + DangerousCommandFilter.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Sequence, Set

from src.application.skills.command_filter import DangerousCommandFilter
from src.domain.gateway.models import ToolCall
from src.domain.kernel.models import ToolResult

logger = logging.getLogger(__name__)

TOOL_POLICY_SETTING_KEY = "tool_policy"

# Default high-risk / write / shell tools → REQUIRE_CONFIRM (mirrors HITL defaults).
_DEFAULT_REQUIRE_CONFIRM: frozenset[str] = frozenset(
    {
        "cli_exec",
        "wiki_note_create",
        "wiki_note_update",
        "wiki_note_organize",
        "save_agent_specification",
        "execute_code",
        "write_card",
        "write_spec",
        "set_card_status",
        "write_project_file",
        "create_project",
        "git_commit",
        "sync_card_issue",
        "execute_agent_database",
    }
)

_DEFAULT_SAFE: frozenset[str] = frozenset(
    {
        "wiki_note_search",
        "wiki_note_get",
        "wiki_note_list",
        "list_available_skills_and_tools",
        "read_document_file",
        "query_agent_database",
        "get_system_info",
        "search_memory",
    }
)


class ToolPolicyVerdict(str, Enum):
    ALLOW = "ALLOW"
    REQUIRE_CONFIRM = "REQUIRE_CONFIRM"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class ToolPolicyDecision:
    verdict: ToolPolicyVerdict
    tool_name: str
    reason: str
    policy_source: str


def _normalize_policy(raw: Any) -> dict[str, set[str]]:
    if not isinstance(raw, dict):
        raw = {}
    def _as_set(key: str) -> set[str]:
        vals = raw.get(key) or []
        if not isinstance(vals, (list, tuple, set)):
            return set()
        return {str(x).strip() for x in vals if str(x).strip()}

    return {
        "block_tools": _as_set("block_tools"),
        "require_confirm_tools": _as_set("require_confirm_tools"),
        "safe_tools": _as_set("safe_tools"),
    }


def _agent_allowed_names(agent: Any) -> set[str]:
    allowed = set(getattr(agent, "allowed_tool_names", None) or [])
    for srv in getattr(agent, "mcp_servers", None) or []:
        srv_name = srv.name if hasattr(srv, "name") else (srv.get("name") if isinstance(srv, dict) else "")
        if srv_name:
            # MCP tools are scoped; allow bare and scoped forms at policy layer.
            allowed.add(str(srv_name))
    if getattr(agent, "storage_enabled", False):
        allowed.add("query_agent_database")
        allowed.add("execute_agent_database")
    return allowed


def _capability_tool_names(matched_capability_ids: Optional[Sequence[str]]) -> Optional[set[str]]:
    if matched_capability_ids is None:
        return None
    names: set[str] = set()
    for raw in matched_capability_ids:
        cid = str(raw or "").strip()
        if not cid:
            continue
        if cid.startswith("tool."):
            names.add(cid[len("tool.") :])
        else:
            # Also accept bare tool names in the subset list.
            names.add(cid)
    return names


class ToolPolicyGate:
    """
    Durable tool authorization gate [REQ-TOOLPOL-001..004].
    Verdict before executor; decision log on apply/log_decision.
    """

    def __init__(self, store: Any) -> None:
        self._store = store
        self._policy = _normalize_policy(None)
        self.reload_policy()

    def reload_policy(self) -> None:
        raw = None
        getter = getattr(self._store, "get_setting", None)
        if callable(getter):
            try:
                raw = getter(TOOL_POLICY_SETTING_KEY)
            except Exception:  # noqa: BLE001
                raw = None
        self._policy = _normalize_policy(raw)

    def evaluate(
        self,
        tool_call: ToolCall,
        agent: Any,
        *,
        matched_capability_ids: Optional[Sequence[str]] = None,
        registry_tool_names: Optional[Set[str]] = None,
    ) -> ToolPolicyDecision:
        name = str(tool_call.name or "").strip()
        if not name:
            return ToolPolicyDecision(
                verdict=ToolPolicyVerdict.BLOCK,
                tool_name=name or "unknown",
                reason="Empty tool name — fail closed",
                policy_source="fail_closed",
            )

        # Explicit durable block list (even if listed/allowlisted) [REQ-TOOLPOL-002].
        if name in self._policy["block_tools"]:
            return ToolPolicyDecision(
                verdict=ToolPolicyVerdict.BLOCK,
                tool_name=name,
                reason=f"Tool '{name}' is blocked by durable tool_policy.block_tools",
                policy_source="settings.block_tools",
            )

        # Unknown to registry → BLOCK [REQ-TOOLPOL-003].
        if registry_tool_names is not None and name not in registry_tool_names:
            # Flexible MCP suffix match
            matched_reg = any(
                (r.startswith("mcp_") and r.endswith(f"_{name}"))
                or (name.startswith("mcp_") and name.endswith(f"_{r}"))
                for r in registry_tool_names
            )
            if not matched_reg:
                return ToolPolicyDecision(
                    verdict=ToolPolicyVerdict.BLOCK,
                    tool_name=name,
                    reason=f"Tool '{name}' is unknown to the tool registry — fail closed",
                    policy_source="registry",
                )

        # Agent allowlist (Forge-managed) — listing ≠ authorization [REQ-TOOLPOL-002/003].
        allowed = _agent_allowed_names(agent)
        if name not in allowed:
            matched_allow = any(
                (a.startswith("mcp_") and a.endswith(f"_{name}"))
                or (name.startswith("mcp_") and name.endswith(f"_{a}"))
                for a in allowed
            )
            if not matched_allow:
                return ToolPolicyDecision(
                    verdict=ToolPolicyVerdict.BLOCK,
                    tool_name=name,
                    reason=f"Tool '{name}' is not in agent allowlist — fail closed",
                    policy_source="agent_allowlist",
                )

        # Matched capability subset when job-bound [REQ-TOOLPOL-003 / CARD-220].
        subset = _capability_tool_names(matched_capability_ids)
        if subset is not None and name not in subset:
            return ToolPolicyDecision(
                verdict=ToolPolicyVerdict.BLOCK,
                tool_name=name,
                reason=(
                    f"Tool '{name}' is out of matched capability subset "
                    f"({sorted(subset)}) — fail closed"
                ),
                policy_source="capability_subset",
            )

        # Prohibited destructive shell patterns → hard BLOCK (not confirm).
        if name == "cli_exec":
            args = tool_call.arguments if isinstance(tool_call.arguments, dict) else {}
            command = str(args.get("command") or args.get("cmd") or "")
            is_bad, reason = DangerousCommandFilter.is_dangerous(command)
            if is_bad:
                return ToolPolicyDecision(
                    verdict=ToolPolicyVerdict.BLOCK,
                    tool_name=name,
                    reason=reason or "Prohibited dangerous command",
                    policy_source="dangerous_command_filter",
                )

        # Durable require_confirm / defaults for write/shell [REQ-TOOLPOL-003].
        require = set(_DEFAULT_REQUIRE_CONFIRM) | self._policy["require_confirm_tools"]
        safe = set(_DEFAULT_SAFE) | self._policy["safe_tools"]

        if name in require and name not in self._policy["safe_tools"]:
            return ToolPolicyDecision(
                verdict=ToolPolicyVerdict.REQUIRE_CONFIRM,
                tool_name=name,
                reason=f"Tool '{name}' requires operator confirmation (write/shell/high-risk)",
                policy_source="settings.require_confirm_tools"
                if name in self._policy["require_confirm_tools"]
                else "default_high_risk",
            )

        if name in safe or name not in require:
            return ToolPolicyDecision(
                verdict=ToolPolicyVerdict.ALLOW,
                tool_name=name,
                reason=f"Tool '{name}' is read/safe under durable policy",
                policy_source="default_safe" if name in safe else "default_allow",
            )

        return ToolPolicyDecision(
            verdict=ToolPolicyVerdict.ALLOW,
            tool_name=name,
            reason=f"Tool '{name}' allowed",
            policy_source="default_allow",
        )

    def log_decision(
        self,
        decision: ToolPolicyDecision,
        *,
        session_id: Optional[str],
        agent_id: Optional[str],
    ) -> str:
        decision_id = f"tpd_{uuid.uuid4().hex[:12]}"
        saver = getattr(self._store, "save_tool_policy_decision", None)
        if callable(saver):
            saver(
                {
                    "id": decision_id,
                    "session_id": session_id,
                    "agent_id": agent_id,
                    "tool_name": decision.tool_name,
                    "verdict": decision.verdict.value
                    if isinstance(decision.verdict, ToolPolicyVerdict)
                    else str(decision.verdict),
                    "reason": decision.reason,
                    "policy_source": decision.policy_source,
                }
            )
        else:
            logger.warning("store lacks save_tool_policy_decision; skipping decision log")
        return decision_id

    def apply_to_tool_result(
        self,
        decision: ToolPolicyDecision,
        tool_call: ToolCall,
        *,
        session_id: str,
        agent: Any,
        hitl_engine: Optional[Any],
        approval_mode: str = "ask",
        routine_id: Optional[str] = None,
        log: bool = True,
    ) -> Optional[ToolResult]:
        """
        Map verdict to executor short-circuit ToolResult.
        ALLOW → None (caller executes). REQUIRE_CONFIRM → park via existing HITL.
        BLOCK → fail-closed ToolResult (never runs).
        """
        if log:
            self.log_decision(
                decision,
                session_id=session_id,
                agent_id=getattr(agent, "id", None),
            )

        if decision.verdict == ToolPolicyVerdict.ALLOW:
            return None

        if decision.verdict == ToolPolicyVerdict.BLOCK:
            return ToolResult(
                call_id=tool_call.id,
                tool_name=tool_call.name,
                output=None,
                success=False,
                error=f"tool_policy_blocked:{decision.reason}",
            )

        # REQUIRE_CONFIRM → existing HITL park/resume [REQ-TOOLPOL-003/005].
        mode = "run" if str(approval_mode or "").strip().lower() == "run" else "ask"
        if mode == "run":
            # Operator chose run-through; still log REQUIRE_CONFIRM but allow execute.
            return None
        if hitl_engine is None:
            return ToolResult(
                call_id=tool_call.id,
                tool_name=tool_call.name,
                output=None,
                success=False,
                error=f"tool_policy_blocked:REQUIRE_CONFIRM but HITL engine missing ({decision.reason})",
            )
        approval_id = hitl_engine.park_tool_call(
            session_id=session_id,
            agent_id=getattr(agent, "id", "unknown"),
            tool_call=tool_call,
            routine_id=routine_id,
        )
        return ToolResult(
            call_id=tool_call.id,
            tool_name=tool_call.name,
            output={
                "status": "parked",
                "approval_id": approval_id,
                "message": (
                    f"Parked for operator approval ({approval_id}). "
                    f"The tool was not executed. [{decision.reason}]"
                ),
                "policy_verdict": ToolPolicyVerdict.REQUIRE_CONFIRM.value,
            },
            success=False,
            error=f"approval_required:{approval_id}",
        )
