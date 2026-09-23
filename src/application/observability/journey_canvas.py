"""Observability Journey Canvas Service & Domain Models [CARD-428].

Provides:
- Canonical architectural journey scenarios across 4 swimlanes.
- Real-time step sequences, state transitions, and execution payloads.
- Secure source snippet retrieval with strict path-traversal boundary enforcement.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def _get_checkout_root() -> Path:
    # Resolve repository root from src/application/observability/journey_canvas.py -> repo root
    return Path(__file__).resolve().parents[3]


class SourceLine(BaseModel):
    line_number: int
    content: str
    is_highlight: bool = False


class SourceSnippetResponse(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    highlight_line: int
    lines: List[SourceLine]
    language: str = "python"
    exists: bool = True


class JourneyStep(BaseModel):
    id: str
    step_index: int
    swimlane: str = Field(description="'ui', 'api', 'orchestrator', or 'storage'")
    swimlane_label: str
    title: str
    description: str
    source_file: str
    source_line: int
    state_transition: str
    duration_ms: float = 0.0
    status: str = Field(default="ok", description="'ok', 'hitl_paused', 'error'")
    payload: Dict[str, Any] = Field(default_factory=dict)


class JourneyScenarioSummary(BaseModel):
    id: str
    title: str
    description: str
    step_count: int = 0
    category: str = "chat"
    default: bool = False


class JourneyScenario(JourneyScenarioSummary):
    steps: List[JourneyStep] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        if self.steps:
            self.step_count = len(self.steps)


class JourneyCanvasService:
    """Orchestrates Journey Canvas scenario catalogs and source snippet extraction."""

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        self.repo_root = repo_root or _get_checkout_root()

    def get_source_snippet(
        self,
        file_path: str,
        line: int = 1,
        range_lines: int = 10,
    ) -> SourceSnippetResponse:
        """Safely extracts code lines surrounding a target line.

        Negative Assertion / Invariant: Path traversal outside repository root is strictly forbidden.
        """
        raw_path = str(file_path or "").strip()
        if not raw_path:
            raise ValueError("file_path is required")

        # Resolve path safely
        candidate = (self.repo_root / raw_path).resolve()
        root_resolved = self.repo_root.resolve()

        try:
            candidate.relative_to(root_resolved)
        except ValueError:
            raise PermissionError(f"Access denied: path '{raw_path}' is outside repository checkout root")

        # Normalize relative path for response
        rel_str = str(candidate.relative_to(root_resolved)).replace("\\", "/")

        if not candidate.is_file():
            return SourceSnippetResponse(
                file_path=rel_str,
                start_line=1,
                end_line=1,
                highlight_line=line,
                lines=[],
                exists=False,
            )

        try:
            content = candidate.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return SourceSnippetResponse(
                file_path=rel_str,
                start_line=1,
                end_line=1,
                highlight_line=line,
                lines=[],
                exists=False,
            )

        all_lines = content.splitlines()
        total_lines = len(all_lines)
        target_line = max(1, min(line, total_lines or 1))

        start_line = max(1, target_line - range_lines)
        end_line = min(total_lines, target_line + range_lines)

        lines_out: List[SourceLine] = []
        for idx in range(start_line, end_line + 1):
            line_str = all_lines[idx - 1] if idx <= total_lines else ""
            lines_out.append(
                SourceLine(
                    line_number=idx,
                    content=line_str,
                    is_highlight=(idx == target_line),
                )
            )

        ext = candidate.suffix.lower()
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".mjs": "javascript",
            ".html": "html",
            ".css": "css",
            ".json": "json",
            ".md": "markdown",
            ".sh": "bash",
            ".sql": "sql",
        }
        language = lang_map.get(ext, "text")

        return SourceSnippetResponse(
            file_path=rel_str,
            start_line=start_line,
            end_line=end_line,
            highlight_line=target_line,
            lines=lines_out,
            language=language,
            exists=True,
        )

    def list_scenarios(self) -> List[JourneyScenarioSummary]:
        scenarios = self._get_canonical_scenarios()
        return [
            JourneyScenarioSummary(
                id=s.id,
                title=s.title,
                description=s.description,
                step_count=len(s.steps),
                category=s.category,
                default=s.default,
            )
            for s in scenarios
        ]

    def get_scenario(self, scenario_id: str) -> Optional[JourneyScenario]:
        for s in self._get_canonical_scenarios():
            if s.id == scenario_id:
                return s
        return None

    def _get_canonical_scenarios(self) -> List[JourneyScenario]:
        return [
            JourneyScenario(
                id="chat_turn_hitl_approval",
                title="Chat Turn with Sensitive Tool & HITL Approval",
                description="User submits a prompt triggering a sensitive file write. Orchestrator parks execution at tool policy gate until operator approves in Chat Studio.",
                category="chat",
                default=True,
                steps=[
                    JourneyStep(
                        id="step-1",
                        step_index=1,
                        swimlane="ui",
                        swimlane_label="1. UI / Browser",
                        title="Chat submit",
                        description="User enters prompt in chat textarea and clicks Send. Store dispatches message to server.",
                        source_file="src/web/static/modules/studios/chat.js",
                        source_line=140,
                        state_transition="IDLE -> SUBMITTING",
                        duration_ms=4.2,
                        status="ok",
                        payload={
                            "action": "chat_send",
                            "session_id": "sess_default_01",
                            "prompt": "Please review the notes and update 00_Inbox/summary.md with the latest metrics",
                            "agent_id": "jarvis",
                        },
                    ),
                    JourneyStep(
                        id="step-2",
                        step_index=2,
                        swimlane="api",
                        swimlane_label="2. API Gateway (FastAPI)",
                        title="POST /api/chat/stream",
                        description="FastAPI router validates bearer token, parses request payload, and opens Server-Sent Events (SSE) stream.",
                        source_file="src/web/routers/chat.py",
                        source_line=88,
                        state_transition="SUBMITTING -> STREAM_START",
                        duration_ms=12.5,
                        status="ok",
                        payload={
                            "route": "POST /api/chat/stream",
                            "client_ip": "127.0.0.1",
                            "sse_headers": {"Content-Type": "text/event-stream", "Cache-Control": "no-cache"},
                        },
                    ),
                    JourneyStep(
                        id="step-3",
                        step_index=3,
                        swimlane="orchestrator",
                        swimlane_label="3. Orchestrator State Machine (ReAct Loop)",
                        title="LLM Plan & Decompose",
                        description="AgentRuntime loads system persona, injects active tools and skills, queries Ollama/vLLM, and parses tool call JSON.",
                        source_file="src/application/chat/runtime.py",
                        source_line=112,
                        state_transition="STREAM_START -> PLANNING",
                        duration_ms=840.0,
                        status="ok",
                        payload={
                            "provider": "ollama",
                            "model": "qwen2.5:14b",
                            "tool_calls": [
                                {
                                    "name": "write_file",
                                    "arguments": {"path": "00_Inbox/summary.md", "content": "# Metrics Summary\n..."},
                                }
                            ],
                            "tokens": {"prompt": 1450, "completion": 48},
                        },
                    ),
                    JourneyStep(
                        id="step-4",
                        step_index=4,
                        swimlane="storage",
                        swimlane_label="4. Storage & Policy",
                        title="Tool Policy Gate flagged sensitive write_file",
                        description="ToolPolicy checks permissions for 'write_file'. Flags filesystem write as sensitive, creating parked approval item.",
                        source_file="src/infrastructure/tools/policy.py",
                        source_line=48,
                        state_transition="PLANNING -> AWAITING_APPROVAL",
                        duration_ms=2.1,
                        status="hitl_paused",
                        payload={
                            "tool_name": "write_file",
                            "policy_rule": "FS_WRITE_REQUIRES_OPERATOR_APPROVAL",
                            "status": "parked",
                            "approval_id": "hitl_9821a",
                            "arguments": {"path": "00_Inbox/summary.md"},
                        },
                    ),
                    JourneyStep(
                        id="step-5",
                        step_index=5,
                        swimlane="ui",
                        swimlane_label="1. UI / Browser",
                        title="HITL Decision Modal Rendered",
                        description="Browser SSE listener receives hitl_paused event. Chat Studio renders interactive approval modal with diff inspection.",
                        source_file="src/web/static/modules/chat/approval_modal.js",
                        source_line=35,
                        state_transition="AWAITING_APPROVAL -> OPERATOR_REVIEW",
                        duration_ms=18.0,
                        status="ok",
                        payload={
                            "event": "tool_approval_required",
                            "tool_name": "write_file",
                            "approval_id": "hitl_9821a",
                            "modal_state": "visible",
                        },
                    ),
                    JourneyStep(
                        id="step-6",
                        step_index=6,
                        swimlane="api",
                        swimlane_label="2. API Gateway (FastAPI)",
                        title="POST /api/chat/approve-tool",
                        description="Operator clicks Approve in modal. API marks approval decision and resumes paused loop.",
                        source_file="src/web/routers/chat.py",
                        source_line=210,
                        state_transition="OPERATOR_REVIEW -> TOOL_APPROVED",
                        duration_ms=14.2,
                        status="ok",
                        payload={
                            "route": "POST /api/chat/approve-tool",
                            "approval_id": "hitl_9821a",
                            "decision": "approved",
                        },
                    ),
                    JourneyStep(
                        id="step-7",
                        step_index=7,
                        swimlane="orchestrator",
                        swimlane_label="3. Orchestrator State Machine (ReAct Loop)",
                        title="Execute Tool & Feed Observation",
                        description="Runtime executes write_file, records file changes, and appends observation into conversation context.",
                        source_file="src/application/chat/runtime.py",
                        source_line=195,
                        state_transition="TOOL_APPROVED -> EXECUTING",
                        duration_ms=22.4,
                        status="ok",
                        payload={
                            "tool_executed": "write_file",
                            "bytes_written": 412,
                            "observation": "Successfully wrote 412 bytes to 00_Inbox/summary.md",
                        },
                    ),
                    JourneyStep(
                        id="step-8",
                        step_index=8,
                        swimlane="storage",
                        swimlane_label="4. Storage & Policy",
                        title="Persist Telemetry Spans & State",
                        description="Saves TelemetrySpan into autoreiv.db SQLite database and updates conversation checkpoints.",
                        source_file="src/infrastructure/memory/repositories/telemetry.py",
                        source_line=44,
                        state_transition="EXECUTING -> PERSISTED",
                        duration_ms=3.8,
                        status="ok",
                        payload={
                            "table": "telemetry_spans",
                            "span_type": "tool",
                            "db_path": "%LOCALAPPDATA%/AutoReiv/database/autoreiv.db",
                            "status": "ok",
                        },
                    ),
                    JourneyStep(
                        id="step-9",
                        step_index=9,
                        swimlane="ui",
                        swimlane_label="1. UI / Browser",
                        title="Response Stream Complete",
                        description="Agent delivers confirmation message. UI scroll stickiness maintains bottom view and unparks input box.",
                        source_file="src/web/static/modules/studios/chat.js",
                        source_line=260,
                        state_transition="PERSISTED -> IDLE",
                        duration_ms=15.0,
                        status="ok",
                        payload={
                            "event": "done",
                            "total_turn_duration_ms": 1120.0,
                            "final_state": "idle",
                        },
                    ),
                ],
            ),
            JourneyScenario(
                id="routine_wiki_execution",
                title="Scheduled Routine & Wiki Note Generation",
                description="Background timer triggers scheduled observation routine. Lead agent reads telemetry metrics and writes a structured report to 00_Inbox/.",
                category="routine",
                default=False,
                steps=[
                    JourneyStep(
                        id="step-r1",
                        step_index=1,
                        swimlane="orchestrator",
                        swimlane_label="3. Orchestrator State Machine (ReAct Loop)",
                        title="Cron Scheduler Triggers Routine",
                        description="Routine scheduler checks cron expression '0 * * * *'. Fired routine dispatches task to lead agent.",
                        source_file="src/application/routines/scheduler.py",
                        source_line=65,
                        state_transition="SLEEPING -> TRIGGERED",
                        duration_ms=2.5,
                        status="ok",
                        payload={
                            "routine_id": "rtn_hourly_metrics",
                            "cron": "0 * * * *",
                            "lead_agent": "jarvis",
                        },
                    ),
                    JourneyStep(
                        id="step-r2",
                        step_index=2,
                        swimlane="orchestrator",
                        swimlane_label="3. Orchestrator State Machine (ReAct Loop)",
                        title="Dispatch Observability Audit Skill",
                        description="Agent loads SKILL.md for metric analysis and runs aggregation functions against telemetry database.",
                        source_file="src/application/routines/execution.py",
                        source_line=110,
                        state_transition="TRIGGERED -> EXECUTING_SKILL",
                        duration_ms=45.0,
                        status="ok",
                        payload={
                            "skill": "observability-audit",
                            "parameters": {"lookback_hours": 1},
                        },
                    ),
                    JourneyStep(
                        id="step-r3",
                        step_index=3,
                        swimlane="storage",
                        swimlane_label="4. Storage & Policy",
                        title="Synthesize & Format Markdown Report",
                        description="Service formats KPIs into Frontmatter-annotated markdown report note.",
                        source_file="src/application/wiki/service.py",
                        source_line=82,
                        state_transition="EXECUTING_SKILL -> WRITING_NOTE",
                        duration_ms=18.0,
                        status="ok",
                        payload={
                            "note_title": "Hourly Telemetry Report",
                            "dest_folder": "00_Inbox",
                            "word_count": 340,
                        },
                    ),
                    JourneyStep(
                        id="step-r4",
                        step_index=4,
                        swimlane="storage",
                        swimlane_label="4. Storage & Policy",
                        title="Write Markdown File to Local Vault",
                        description="Atomic write ensures zero partial corruption in user data wiki folder.",
                        source_file="src/infrastructure/wiki/vault.py",
                        source_line=54,
                        state_transition="WRITING_NOTE -> VAULT_UPDATED",
                        duration_ms=4.1,
                        status="ok",
                        payload={
                            "target_path": "%LOCALAPPDATA%/AutoReiv/wiki/00_Inbox/report_20260923.md",
                            "bytes": 1824,
                        },
                    ),
                    JourneyStep(
                        id="step-r5",
                        step_index=5,
                        swimlane="ui",
                        swimlane_label="1. UI / Browser",
                        title="Observability Studio Refresh",
                        description="Web client automatically receives telemetry notification and refreshes dashboard widgets.",
                        source_file="src/web/static/modules/studios/observability.js",
                        source_line=70,
                        state_transition="VAULT_UPDATED -> OBSERVED",
                        duration_ms=8.0,
                        status="ok",
                        payload={
                            "studio": "observability",
                            "action": "kpi_refresh",
                            "status": "ready",
                        },
                    ),
                ],
            ),
            JourneyScenario(
                id="react_multi_turn_reasoning",
                title="Multi-Turn ReAct Reasoning & Skill Execution",
                description="Complex goal decomposition using sequential thoughts, actions, and observations across multiple tool gates.",
                category="react",
                default=False,
                steps=[
                    JourneyStep(
                        id="step-m1",
                        step_index=1,
                        swimlane="ui",
                        swimlane_label="1. UI / Browser",
                        title="Operator Triggers Complex Goal",
                        description="User enters a research goal requiring multiple steps across wiki and local data.",
                        source_file="src/web/static/modules/studios/chat.js",
                        source_line=145,
                        state_transition="IDLE -> GOAL_ACTIVE",
                        duration_ms=3.5,
                        status="ok",
                        payload={"mode": "goal", "goal": "Audit project documentation and identify stale ADRs"},
                    ),
                    JourneyStep(
                        id="step-m2",
                        step_index=2,
                        swimlane="api",
                        swimlane_label="2. API Gateway (FastAPI)",
                        title="POST /api/chat/stream (Goal Mode)",
                        description="API initiates persistent execution session with high turn budget.",
                        source_file="src/web/routers/chat.py",
                        source_line=92,
                        state_transition="GOAL_ACTIVE -> STREAMING",
                        duration_ms=10.2,
                        status="ok",
                        payload={"turn_budget": 10, "session_mode": "goal"},
                    ),
                    JourneyStep(
                        id="step-m3",
                        step_index=3,
                        swimlane="orchestrator",
                        swimlane_label="3. Orchestrator State Machine (ReAct Loop)",
                        title="Phase 1: Explore & Query Search",
                        description="Agent generates thought, invokes wiki search tool to find ADR files.",
                        source_file="src/application/chat/runtime.py",
                        source_line=130,
                        state_transition="STREAMING -> EXPLORING",
                        duration_ms=520.0,
                        status="ok",
                        payload={"phase": "discovery", "action": "wiki_search", "query": "ADR"},
                    ),
                    JourneyStep(
                        id="step-m4",
                        step_index=4,
                        swimlane="storage",
                        swimlane_label="4. Storage & Policy",
                        title="Read Pack Database & Index",
                        description="SQLite query scans wiki index and retrieves note paths and frontmatter tags.",
                        source_file="src/infrastructure/memory/sqlite_store.py",
                        source_line=88,
                        state_transition="EXPLORING -> DATA_LOADED",
                        duration_ms=6.4,
                        status="ok",
                        payload={"results_count": 14, "table": "wiki_notes"},
                    ),
                    JourneyStep(
                        id="step-m5",
                        step_index=5,
                        swimlane="orchestrator",
                        swimlane_label="3. Orchestrator State Machine (ReAct Loop)",
                        title="Phase 2: Synthesize Multi-Source Answers",
                        description="Agent evaluates ADR status, identifies superseded decisions, and formulates concise answer.",
                        source_file="src/application/chat/runtime.py",
                        source_line=175,
                        state_transition="DATA_LOADED -> SYNTHESIZING",
                        duration_ms=910.0,
                        status="ok",
                        payload={"tokens_generated": 320, "findings": 2},
                    ),
                    JourneyStep(
                        id="step-m6",
                        step_index=6,
                        swimlane="ui",
                        swimlane_label="1. UI / Browser",
                        title="Interactive Findings Rendered",
                        description="Chat stream closes and interactive markdown card renders in user conversation viewport.",
                        source_file="src/web/static/modules/studios/chat.js",
                        source_line=320,
                        state_transition="SYNTHESIZING -> COMPLETE",
                        duration_ms=12.0,
                        status="ok",
                        payload={"status": "complete", "render_mode": "markdown"},
                    ),
                ],
            ),
        ]
