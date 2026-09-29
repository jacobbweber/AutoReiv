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

    def _provider_target(self, provider_id: str, providers_cfg: Dict[str, Any]) -> tuple[str, str]:
        """Resolve the base URL to probe for a provider from saved settings [CARD-580].

        Order: the saved per-provider base_url (what Settings shows), the legacy
        ollama_host / openai_base_url keys, the preset default, then OLLAMA_HOST.
        Returns (url, source).
        """
        from src.application.settings.presets import get_preset_by_id

        pid = provider_id.lower()
        saved = (providers_cfg.get("providers") or {}).get(pid) or {}
        if saved.get("base_url"):
            return str(saved["base_url"]), "settings"
        default_pid = str(providers_cfg.get("default_provider_id") or "").lower()
        if pid == "ollama" and providers_cfg.get("ollama_host"):
            return str(providers_cfg["ollama_host"]), "settings"
        if pid == default_pid and pid != "ollama" and providers_cfg.get("openai_base_url"):
            return str(providers_cfg["openai_base_url"]), "settings"
        if pid == "openai" and providers_cfg.get("openai_base_url"):
            return str(providers_cfg["openai_base_url"]), "settings"
        preset = get_preset_by_id(pid)
        if preset and preset.get("default_url"):
            return str(preset["default_url"]), "preset"
        if pid == "ollama" and os.environ.get("OLLAMA_HOST"):
            return os.environ["OLLAMA_HOST"], "OLLAMA_HOST"
        return "http://127.0.0.1:11434", "fallback"

    @staticmethod
    def _normalize_probe_url(url: str, provider_id: str) -> str:
        """Make a probe-able URL: add a scheme, turn a bind address into loopback,
        and add Ollama's default port when none is given [CARD-580]."""
        from urllib.parse import urlsplit, urlunsplit

        url = (url or "").strip()
        if not url.startswith(("http://", "https://")):
            url = f"http://{url}"
        parts = urlsplit(url)
        host = parts.hostname or "127.0.0.1"
        if host in ("0.0.0.0", "::", "[::]"):
            host = "127.0.0.1"
        port = parts.port
        if port is None and "ollama" in provider_id.lower() and parts.scheme == "http":
            port = 11434
        netloc = f"{host}:{port}" if port else host
        return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))

    def test_provider_connectivity(
        self,
        provider_id: Optional[str] = None,
        host_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Probe local or LAN LLM provider endpoints to measure round-trip latency and model availability.

        With no provider_id, probes the configured default provider and every
        per-agent model override with its own endpoint [CARD-580].
        """
        providers_cfg = self.store.get_setting("provider_settings") or {}
        if provider_id or host_url:
            pid = provider_id or str(providers_cfg.get("default_provider_id") or "ollama")
            return self._probe_provider(pid, host_url, providers_cfg)

        default_pid = str(providers_cfg.get("default_provider_id") or "ollama")
        result = self._probe_provider(default_pid, None, providers_cfg)
        result["checked"] = "default provider"
        overrides: List[Dict[str, Any]] = []
        model_settings = self.store.get_setting("agent_model_settings") or {}
        seen = {(default_pid.lower(), result.get("endpoint"))}
        if isinstance(model_settings, dict):
            for agent_id, vals in model_settings.items():
                if not isinstance(vals, dict):
                    continue
                opid = str(vals.get("provider") or vals.get("provider_id") or "")
                if not opid:
                    continue
                ourl = vals.get("api_base_url") or vals.get("base_url") or None
                probe = self._probe_provider(opid, ourl, providers_cfg)
                if vals.get("model"):
                    probe["model"] = vals["model"]
                key = (opid.lower(), probe.get("endpoint"))
                probe["agent_id"] = agent_id
                if key in seen:
                    probe["same_as_default"] = True
                seen.add(key)
                overrides.append(probe)
        if overrides:
            result["agent_overrides"] = overrides
        return result

    def _probe_provider(self, provider_id: str, host_url: Optional[str], providers_cfg: Dict[str, Any]) -> Dict[str, Any]:
        source = "argument"
        target_url = host_url
        if not target_url:
            target_url, source = self._provider_target(provider_id, providers_cfg)
        target_url = self._normalize_probe_url(target_url, provider_id)

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
                        "endpoint_source": source,
                        "latency_ms": dur_ms,
                        "status_code": resp.status_code,
                        "available_models": models,
                    }
                return {
                    "reachable": False,
                    "provider_id": provider_id,
                    "endpoint": target_url,
                    "endpoint_source": source,
                    "latency_ms": dur_ms,
                    "status_code": resp.status_code,
                    "error": resp.text[:500],
                }
            models_url = target_url.rstrip("/") + "/models"
            headers = {}
            api_key = self._provider_api_key(provider_id, providers_cfg)
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
                    "endpoint_source": source,
                    "latency_ms": dur_ms,
                    "status_code": resp.status_code,
                    "available_models": models,
                }
            return {
                "reachable": False,
                "provider_id": provider_id,
                "endpoint": target_url,
                "endpoint_source": source,
                "latency_ms": dur_ms,
                "status_code": resp.status_code,
                "error": resp.text[:500],
            }
        except Exception as e:
            dur_ms = round((time.perf_counter() - t_start) * 1000, 2)
            return {
                "reachable": False,
                "provider_id": provider_id,
                "endpoint": target_url,
                "endpoint_source": source,
                "latency_ms": dur_ms,
                "error": str(e),
            }

    def _provider_api_key(self, provider_id: str, providers_cfg: Dict[str, Any]) -> str:
        pid = provider_id.lower()
        saved = (providers_cfg.get("providers") or {}).get(pid) or {}
        cred_id = saved.get("vault_cred_id") or f"llm-provider-{pid}"
        try:
            cred = self.store.get_credential(cred_id)
            if cred and cred.secret:
                return str(cred.secret)
        except Exception:
            pass
        if pid == str(providers_cfg.get("default_provider_id") or "").lower() and providers_cfg.get("openai_api_key"):
            return str(providers_cfg["openai_api_key"])
        if pid == "openai":
            return os.environ.get("OPENAI_API_KEY", "")
        return ""

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
            description="Inspect platform and app health, database connectivity, total turns, tokens, and error rates.",
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
            description="Test network connectivity to the configured LLM providers: latency and model availability. With no arguments it checks the default provider and each agent's own model override.",
            parameters={
                "type": "object",
                "properties": {
                    "provider_id": {
                        "type": "string",
                        "description": "Provider ID (for example vllm, ollama, openai). Omit to check the configured default provider and every per-agent override.",
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
