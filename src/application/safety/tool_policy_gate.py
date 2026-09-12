"""Tool Policy Gate [CARD-221 / REQ-TOOLPOL-001..006] [CARD-225 / REQ-MCPGATE-001..006].

ALLOW / REQUIRE_CONFIRM / BLOCK after model intent, before executor.
Registry listing and MCP tools/list are not authorization. Extends HITL +
DangerousCommandFilter. MCP is transport-only — mounted tools still hit
matched capability subset + this gate.
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
        "repo_file_write",
        "repo_file_patch",
        "repo_file_rollback",
    }
)
