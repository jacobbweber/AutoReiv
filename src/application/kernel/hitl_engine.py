"""
Human-In-The-Loop (HITL) Approval Engine [REQ-SAFE-003, REQ-SAFE-004].
Parks high-risk tool executions in SQLite awaiting operator authorization.
"""

from typing import List, Optional, Set

from src.domain.gateway.models import ToolCall
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class HITLApprovalEngine:
    """Evaluates whether tool executions require operator review and parks state."""

    def __init__(
        self,
        store: SQLiteStateStore,
        high_risk_tools: Optional[List[str]] = None,
    ):
        self.store = store
        self.high_risk_tools: Set[str] = set(
            high_risk_tools
            or [
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
            ]
        )

    def register_high_risk_tool(self, tool_name: str) -> None:
        """Add a tool name to the high risk enforcement set."""
        self.high_risk_tools.add(tool_name)

    def requires_approval(self, tool_call: ToolCall) -> bool:
        """Check whether a tool call requires human-in-the-loop authorization."""
        return tool_call.name in self.high_risk_tools

    def park_tool_call(
        self,
        session_id: str,
        agent_id: str,
        tool_call: ToolCall,
        routine_id: Optional[str] = None,
    ) -> str:
        """Park tool execution in SQLite pending approvals table."""
        return self.store.create_approval(
            session_id=session_id,
            agent_id=agent_id,
            tool_name=tool_call.name,
            arguments=tool_call.arguments or {},
            routine_id=routine_id,
        )
