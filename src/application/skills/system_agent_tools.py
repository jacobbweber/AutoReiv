"""
System Agent Tools for Platform Health, Root-Cause Diagnostics & Telemetry Inspection [REQ-AGENTS-006, REQ-AGENTS-007].
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import httpx

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.observability.log_buffer import SystemLogBuffer
from src.application.telemetry.collector import TelemetryCollector
from src.domain.agents.profiles import BUILTIN_PROFILES
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class SystemAgentTools:
    """
    Tool group providing deep system health inspection, error root-cause diagnostics,
    session transcript analysis, and LLM network connectivity probing.
    """

    def __init__(self, store: SQLiteStateStore, telemetry: TelemetryCollector):
        self.store = store
        self.telemetry = telemetry

    def inspect_system_health(self) -> Dict[str, Any]:
        """
        Inspect the database connectivity, query response, and platform KPIs.
        """
        db_status = "healthy"
        try:
            sessions = self.store.list_sessions()
            _ = len(sessions)
        except Exception as e:
            db_status = f"error: {e}"

        kpis = self.telemetry.get_global_kpis()
        return {
            "database_status": db_status,
            "total_turns": kpis["total_turns"],
            "total_tool_calls": kpis["total_tool_calls"],
            "total_tokens": kpis["total_tokens"],
            "global_error_rate": kpis["global_error_rate"],
        }

    def get_agent_usage_summary(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Return token usage, turn counts, and success rates for a specific agent or all agents.
        """
        if agent_id:
            return self.telemetry.get_agent_metrics(agent_id)

        all_agent_metrics = {}
        for profile in BUILTIN_PROFILES:
            all_agent_metrics[profile.id] = self.telemetry.get_agent_metrics(profile.id)
        return all_agent_metrics

    def get_tool_health_matrix(self) -> Dict[str, Dict[str, Any]]:
        """
        Return execution counts, success/failure counts, and error rates for all tools.
        """
        return self.telemetry.get_tool_metrics()

    def get_recent_errors(
        self,
        limit: int = 10,
        agent_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve recent failed execution spans, tool errors, and turn exceptions.
        """
        return self.telemetry.get_recent_errors(limit=limit, agent_id=agent_id)

    def get_agent_sessions(
        self,
        agent_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        List active and recent session IDs for a specific agent.
        """
        all_sessions = self.store.list_sessions(agent_id=agent_id)
        return [
            {
                "id": s.id,
                "agent_id": s.agent_id,
                "title": s.title,
                "created_at": s.created_at.isoformat() if hasattr(s.created_at, "isoformat") else str(s.created_at),
                "updated_at": s.updated_at.isoformat() if hasattr(s.updated_at, "isoformat") else str(s.updated_at),
            }
            for s in all_sessions[:limit]
        ]

    def get_session_transcript(
        self,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Read the recent conversation turns, prompts, tool outputs, and assistant replies for a session.
        """
        target_session = session_id
        if not target_session and agent_id:
            sessions = self.store.list_sessions(agent_id=agent_id)
            if sessions:
                target_session = sessions[0].id

        if not target_session:
            return {
                "success": False,
                "error": "No session ID provided and no prior session found for agent.",
            }

        messages = self.store.get_messages(session_id=target_session)
        trimmed = messages[-limit:] if messages else []
        return {
            "success": True,
            "session_id": target_session,
            "total_messages": len(messages),
            "messages": [
                {
                    "role": m.role.value,
                    "content": m.content,
                    "name": m.name,
                    "tool_call_id": m.tool_call_id,
                    "tool_calls": [tc.model_dump() for tc in m.tool_calls] if m.tool_calls else None,
                }
                for m in trimmed
            ],
        }

    def test_provider_connectivity(
        self,
        provider_id: str = "ollama",
        host_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Probe local or LAN LLM provider endpoints to measure round-trip latency and model availability.
        """
        providers_cfg = self.store.get_setting("provider_settings") or {}
        target_url = host_url
        if not target_url:
            if provider_id.lower() == "ollama":
                target_url = providers_cfg.get("ollama_host") or os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
            elif provider_id.lower() == "openai":
                target_url = providers_cfg.get("openai_base_url") or os.environ.get(
                    "OPENAI_BASE_URL", "https://api.openai.com/v1"
                )
            else:
                target_url = "http://127.0.0.1:11434"

        t_start = time.perf_counter()
        try:
            if "ollama" in provider_id.lower():
                tags_url = target_url.rstrip("/") + "/api/tags"
                resp = httpx.get(tags_url, timeout=5.0)
                dur_ms = round((time.perf_counter() - t_start) * 1000, 2)
                if resp.status_code == 200:
                    models = [m.get("name") for m in resp.json().get("models", [])]
                    return {
                        "reachable": True,
                        "provider_id": provider_id,
                        "endpoint": target_url,
                        "latency_ms": dur_ms,
                        "status_code": resp.status_code,
                        "available_models": models,
                    }
                return {
                    "reachable": False,
                    "provider_id": provider_id,
                    "endpoint": target_url,
                    "latency_ms": dur_ms,
                    "status_code": resp.status_code,
                    "error": resp.text,
                }
            else:
                models_url = target_url.rstrip("/") + "/models"
                headers = {}
                api_key = providers_cfg.get("openai_api_key") or os.environ.get("OPENAI_API_KEY", "")
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                resp = httpx.get(models_url, headers=headers, timeout=5.0)
                dur_ms = round((time.perf_counter() - t_start) * 1000, 2)
                if resp.status_code == 200:
                    models = [m.get("id") for m in resp.json().get("data", [])]
                    return {
                        "reachable": True,
                        "provider_id": provider_id,
                        "endpoint": target_url,
                        "latency_ms": dur_ms,
                        "status_code": resp.status_code,
                        "available_models": models,
                    }
                return {
                    "reachable": False,
                    "provider_id": provider_id,
                    "endpoint": target_url,
                    "latency_ms": dur_ms,
                    "status_code": resp.status_code,
                    "error": resp.text,
                }
        except Exception as e:
            dur_ms = round((time.perf_counter() - t_start) * 1000, 2)
            return {
                "reachable": False,
                "provider_id": provider_id,
                "endpoint": target_url,
                "latency_ms": dur_ms,
                "error": str(e),
            }

    def get_system_logs(
        self,
        lines: int = 50,
        level: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return the most recent application runtime logs from the in-memory buffer.
        """
        buf = SystemLogBuffer.get_instance()
        return buf.get_logs(limit=lines, level=level)

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        """Register System Agent diagnostic and health tools."""
        registry.register_tool(
            name="inspect_system_health",
            description="Inspect platform database connectivity, total turns, tokens, and error rates.",
            parameters={"type": "object"},
            handler=self.inspect_system_health,
        )

        registry.register_tool(
            name="get_agent_usage_summary",
            description="Get token consumption and performance metrics per agent.",
            parameters={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Optional agent ID to filter (e.g. general-assistant)",
                    },
                },
            },
            handler=self.get_agent_usage_summary,
        )

        registry.register_tool(
            name="get_tool_health_matrix",
            description="Get tool reliability stats, failure counts, and execution latency.",
            parameters={"type": "object"},
            handler=self.get_tool_health_matrix,
        )

        registry.register_tool(
            name="get_recent_errors",
            description="Get recent runtime errors, tool failures, and turn exceptions with details.",
            parameters={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max errors to return", "default": 10},
                    "agent_id": {"type": "string", "description": "Optional agent ID to filter"},
                },
            },
            handler=self.get_recent_errors,
        )

        registry.register_tool(
            name="get_agent_sessions",
            description="List recent active conversation sessions for any agent.",
            parameters={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent ID (e.g. librarian, general-assistant)"},
                    "limit": {"type": "integer", "description": "Max sessions to return", "default": 10},
                },
                "required": ["agent_id"],
            },
            handler=self.get_agent_sessions,
        )

        registry.register_tool(
            name="get_session_transcript",
            description="Read the conversation transcript messages and tool outputs for a session.",
            parameters={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Optional explicit session ID"},
                    "agent_id": {"type": "string", "description": "Optional agent ID to read latest session"},
                    "limit": {"type": "integer", "description": "Max messages to return", "default": 20},
                },
            },
            handler=self.get_session_transcript,
        )

        registry.register_tool(
            name="test_provider_connectivity",
            description="Test network connectivity to LLM provider (Ollama / OpenAI), ping latency, and model availability.",
            parameters={
                "type": "object",
                "properties": {
                    "provider_id": {
                        "type": "string",
                        "description": "Provider ID (ollama or openai)",
                        "default": "ollama",
                    },
                    "host_url": {"type": "string", "description": "Optional custom host URL to probe"},
                },
            },
            handler=self.test_provider_connectivity,
        )

        registry.register_tool(
            name="get_system_logs",
            description="Get recent system runtime and daemon log lines.",
            parameters={
                "type": "object",
                "properties": {
                    "lines": {"type": "integer", "description": "Number of log lines", "default": 50},
                    "level": {"type": "string", "description": "Optional log level filter (INFO, WARN, ERROR)"},
                },
            },
            handler=self.get_system_logs,
        )
