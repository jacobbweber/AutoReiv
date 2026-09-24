"""
Agent Kernel ReAct Loop & Event Streamer [REQ-KERNEL-003, REQ-KERNEL-006].
"""

import json
import logging
import time
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional, Sequence, Set

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.kernel.context_compactor import (
    ContextCompactor,
    resolve_agent_context_limit,
    resolve_max_tool_chars,
)
from src.application.kernel.cycle_detector import CycleDetector
from src.application.kernel.hitl_engine import HITLApprovalEngine
from src.application.kernel.telemetry_attribution import (
    calculate_timing_attribution,
    calculate_token_attribution,
)
from src.application.kernel.json_safe import dumps_jsonable, dumps_tool_output
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.orchestration.capability_detector import CapabilityDetector
from src.application.orchestration.handoff_engine import looks_like_provider_failure
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.errors import RateLimitError
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    Role,
    ToolCall,
)
from src.domain.kernel.models import (
    AgentProfile,
    KernelEvent,
    KernelEventType,
    ToolResult,
)
from src.domain.orchestration.models import ReactState
from src.infrastructure.memory.repositories.capability_gaps import CapabilityGapRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

logger = logging.getLogger(__name__)

# Nested run_turn (handoffs, routines) must not inherit Chat's 131k window.
# Live CARD-001 complete() at num_ctx=131072 sent zero bytes for 90s+ and
# tripped the Ollama read timeout. 32k returns a tool call in seconds.
NESTED_COMPLETE_MAX_CTX = 32768
NESTED_COMPLETE_MAX_TOKENS = 8192

# ADR-0054 / CARD-362: Demand-Paged Capability Engine constants
MAX_ACTIVE_TOOLS_PER_TURN: int = 8
BASELINE_COORDINATION_TOOLS: frozenset[str] = frozenset(
    {
        "activate_skill",
        "ask_clarification",
        "handoff_to_agent",
        "get_session_info",
        "lookup_agents",
        "skill_view",
    }
)


def _capability_authoring_requested(text: str) -> bool:
    """True when this turn is asking Developer to scaffold or propose a capability [CARD-429]."""
    raw = (text or "").lower()
    if "capability-authoring" in raw or "build-agent-pack" in raw:
        return True
    if "propose" in raw and "skill" in raw:
        return True
    if "commit" in raw and "skill" in raw:
        return True
    if "scaffold" in raw and ("agent" in raw or "pack" in raw):
        return True
    from src.application.agent_packs.schema import CAPABILITY_AUTHORING_TOOL_NAMES

    for tool in CAPABILITY_AUTHORING_TOOL_NAMES:
        if tool in raw or tool.replace("_", " ") in raw:
            return True
    return False


def parse_nested_park_payload(content: str):
    """Return a nested HITL park dict, or None."""
    try:
        parsed = json.loads(content or "")
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(parsed, dict) and parsed.get("status") == "approval_required" and parsed.get("approval_id"):
        return parsed
    return None


class AgentKernel:
    """
    Orchestrates the ReAct execution loop, scoped tool dispatching,
    conversation state persistence, and telemetry collection.
    """

    def __init__(
        self,
        gateway: MultiProviderGateway,
        tool_registry: ScopedToolRegistry,
        state_store: SQLiteStateStore,
        telemetry: TelemetryCollector,
        hitl_engine: Optional[HITLApprovalEngine] = None,
        data_dir: Optional[str] = None,
        user_skill_catalog: Optional[Any] = None,
        tool_policy_gate: Optional[Any] = None,
    ):
        self.gateway = gateway
        self.tool_registry = tool_registry
        self.state_store = state_store
        self.telemetry = telemetry
        self.hitl_engine = hitl_engine
        if tool_policy_gate is not None:
            self.tool_policy_gate = tool_policy_gate
        else:
            from src.application.safety.tool_policy_gate import ToolPolicyGate

            self.tool_policy_gate = ToolPolicyGate(store=state_store)
        self.react_state: Optional[ReactState] = None
        self.data_dir = data_dir
        self.user_skill_catalog = user_skill_catalog
        self.ace_pack_id: Optional[str] = None
        self._ace_tool_errors: List[Dict[str, Any]] = []
        from src.application.orchestration.jit_synthesizer import JitToolSynthesizer

        self.jit_synthesizer = JitToolSynthesizer(data_dir=self._resolve_ace_data_dir())
        self.capability_gap_repo = CapabilityGapRepository(state_store)

    def _resolve_ace_data_dir(self) -> Optional[str]:
        if self.data_dir:
            return str(self.data_dir)
        try:
            from src.infrastructure.data.resolver import DataDirResolver

            return str(DataDirResolver().resolve().root)
        except Exception:
            return None

    def _get_scrubber(self) -> Any:
        from src.domain.security.scrubber import TranscriptScrubber

        scrubber = TranscriptScrubber()
        if self.state_store and hasattr(self.state_store, "list_credentials"):
            try:
                creds = self.state_store.list_credentials(include_secret=True)
                scrubber.add_secrets([c.get("secret") for c in creds if c.get("secret")])
            except Exception:
                pass
        return scrubber

    async def execute_and_scrub_tool(
        self,
        tool_call: ToolCall,
        agent: AgentProfile,
        session_id: Optional[str] = None,
        approval_mode: Optional[str] = None,
        job_id: Optional[str] = None,
        active_skills: Optional[Sequence[str]] = None,
    ) -> ToolResult:
        tool_res = await self.tool_registry.execute(
            tool_call,
            agent,
            session_id=session_id,
            approval_mode=approval_mode,
            job_id=job_id,
            state_store=self.state_store,
            active_skills=active_skills,
        )
        scrubber = self._get_scrubber()
        if tool_res.output is not None:
            tool_res.output = scrubber.scrub_object(tool_res.output)
        if tool_res.error is not None:
            tool_res.error = scrubber.scrub(str(tool_res.error))
        return tool_res

    def _resolve_ace_pack_id(self) -> Optional[str]:
        explicit = (self.ace_pack_id or "").strip()
        if explicit:
            return explicit
        names = [str(item.get("tool_name") or "") for item in self._ace_tool_errors]
        catalog = self.user_skill_catalog
        if catalog is None:
            data_dir = self._resolve_ace_data_dir()
            if data_dir:
                from pathlib import Path as _Path

                from src.application.skills.user_catalog import UserSkillCatalog

                catalog = UserSkillCatalog(skills_dir=_Path(data_dir) / "skills")
        if catalog is None:
            return None
        try:
            manifests = catalog.list_manifests()
        except Exception:
            return None
        for manifest in manifests:
            slug = str(manifest.id).replace("-", "_").lower()
            if slug and any(slug in n.lower().replace("-", "_") for n in names if n):
                return manifest.id
        return None

    def _ace_note_tool(self, tool_name: str, success: bool, error: Optional[str]) -> None:
        if success:
            return
        if error and str(error).startswith("approval_required:"):
            return
        self._ace_tool_errors.append({"tool_name": tool_name, "error": error or "Tool execution error"})

    def _ace_flush_failed_turn(
        self,
        *,
        session_id: str,
        agent_id: str,
        failed: bool,
        error_message: Optional[str] = None,
    ) -> None:
        """Post-turn Reflector hook. Never raises into the turn [REQ-IMPROVE-001]."""
        errors = list(self._ace_tool_errors or [])
        if not failed and not errors:
            return
        try:
            from src.application.orchestration.ace_online import record_failed_turn_delta

            pack_id = self._resolve_ace_pack_id()
            data_dir = self._resolve_ace_data_dir()
            if not pack_id or not data_dir:
                return
            record_failed_turn_delta(
                self.state_store,
                pack_id=pack_id,
                data_dir=data_dir,
                session_id=session_id,
                agent_id=agent_id,
                error_message=error_message,
                tool_errors=errors,
                catalog=self.user_skill_catalog,
            )
        except Exception as exc:
            logger.debug("online ACE skipped: %s", exc)
        finally:
            self._ace_tool_errors = []

    def _transition_react_state(
        self,
        state: ReactState,
        turn_idx: int,
        *,
        phase_id: Optional[str] = None,
        job_id: Optional[str] = None,
        assigned_agent_id: Optional[str] = None,
    ) -> Optional[KernelEvent]:
        """Overlay ReAct state and persist when phase_id is in scope [REQ-KERNEL-001]."""
        if self.react_state == state:
            return None
        self.react_state = state
        job_status = None
        phase_name = None
        resolved_job_id = job_id
        resolved_agent = assigned_agent_id
        if phase_id:
            try:
                get_phase = getattr(self.state_store, "get_phase", None)
                update_phase = getattr(self.state_store, "update_phase", None)
                if get_phase and update_phase:
                    phase = get_phase(phase_id)
                    phase.react_state = state
                    update_phase(phase)
                    phase_name = phase.name
                    resolved_job_id = resolved_job_id or phase.job_id
                    resolved_agent = resolved_agent or phase.assigned_agent_id
                    get_job = getattr(self.state_store, "get_job", None)
                    if get_job:
                        try:
                            job = get_job(phase.job_id)
                            status = job.status
                            job_status = status.value if hasattr(status, "value") else str(status)
                        except Exception:
                            pass
            except Exception as exc:
                logger.debug("react_state persist skipped for phase %s: %s", phase_id, exc)
        return KernelEvent(
            event_type=KernelEventType.REACT_STATE,
            react={
                "react_state": state.value,
                "turn_idx": turn_idx,
                "job_id": resolved_job_id,
                "phase_id": phase_id,
                "assigned_agent_id": resolved_agent,
                "job_status": job_status,
                "phase_name": phase_name,
            },
        )

    def _matched_capability_ids_for_job(self, job_id: Optional[str], phase_id: Optional[str] = None) -> Optional[list]:
        """Resolve locked matched IDs from durable checkpoint when job/phase-bound [CARD-221/224, CARD-362]."""
        jid = (job_id or "").strip()
        pid = (phase_id or "").strip()
        if not jid and not pid:
            return None
        if pid and self.state_store and not jid:
            getter_phase = getattr(self.state_store, "get_phase", None)
            if callable(getter_phase):
                try:
                    ph = getter_phase(pid)
                    if ph and getattr(ph, "job_id", None):
                        jid = ph.job_id
                except Exception:
                    pass
        if not jid:
            return None
        getter = getattr(self.state_store, "get_latest_job_phase_checkpoint", None)
        if not callable(getter):
            return None
        try:
            cp = getter(jid)
        except Exception:
            return None
        if cp is None:
            return None
        ids = getattr(cp, "matched_capability_ids", None) or []
        return [str(x) for x in ids]

    def _gate_tool_call(
        self,
        tc: ToolCall,
        session_id: str,
        agent: AgentProfile,
        approval_mode: str = "ask",
        routine_id: Optional[str] = None,
        matched_capability_ids: Optional[list] = None,
        job_id: Optional[str] = None,
    ) -> Optional[ToolResult]:
        """
        Tool policy gate [CARD-221]: ALLOW / REQUIRE_CONFIRM / BLOCK before executor.
        Registry listing ≠ authorization. Extends HITL + DangerousCommandFilter.
        """
        gate = self.tool_policy_gate
        if gate is None:
            # Fail closed if miswired — never silent-run.
            return ToolResult(
                call_id=tc.id,
                tool_name=tc.name,
                output=None,
                success=False,
                error="tool_policy_blocked:ToolPolicyGate missing",
            )
        registry_names = set()
        try:
            registry_names = {d.name for d in self.tool_registry.list_tools()}
        except Exception:
            registry_names = set(getattr(agent, "allowed_tool_names", []) or [])
        decision = gate.evaluate(
            tc,
            agent,
            matched_capability_ids=matched_capability_ids,
            registry_tool_names=registry_names or None,
        )
        return gate.apply_to_tool_result(
            decision,
            tc,
            session_id=session_id,
            agent=agent,
            hitl_engine=self.hitl_engine,
            approval_mode=approval_mode,
            routine_id=routine_id,
            job_id=job_id,
        )

    @staticmethod
    def _is_model_compatible_with_provider(model: str, provider_id: str) -> bool:
        if not model or model == "default":
            return False
        if "/" in model:
            pid, _ = model.split("/", 1)
            return pid.lower() == provider_id.lower()
        if provider_id == "ollama":
            return True
        # Non-ollama providers do not use colon tags like qwen3.8:latest
        if ":" in model:
            return False
        return True

    def _resolve_model(self, agent: AgentProfile) -> str:
        """
        Simplified Provider & Model Cascade Resolution [REQ-MODEL-003]:
        1. Agent explicit provider and model (if not 'default')
        2. Agent explicit model override (if not 'default')
        3. Global Default provider + model from Settings (provider_settings)
        4. Gateway default_model_id / fallback
        """
        KNOWN_PROVIDERS = {
            "ollama",
            "gemini",
            "openai",
            "anthropic",
            "lmstudio",
            "vllm",
            "openrouter",
            "deepseek",
            "groq",
        }
        agent_provider = getattr(agent, "provider", "default")
        raw_agent_provider = str(agent_provider or "").strip().lower()
        raw_agent_model = str(agent.model or "").strip()

        # 1. Agent explicit provider override [CARD-214]
        if raw_agent_provider and raw_agent_provider != "default":
            # 1a. Concrete model override
            if (
                raw_agent_model
                and raw_agent_model.lower() != "default"
                and raw_agent_model.lower() not in KNOWN_PROVIDERS
            ):
                if "/" in raw_agent_model:
                    return raw_agent_model
                return f"{raw_agent_provider}/{raw_agent_model}"

            # 1b. Model left as "default": check if provider has a configured default_model_id in Settings
            if self.state_store:
                prov_data = self.state_store.get_setting("provider_settings")
                if isinstance(prov_data, dict):
                    provider_map = prov_data.get("providers") or {}
                    p_cfg = provider_map.get(raw_agent_provider) or {}
                    p_model = p_cfg.get("default_model_id")
                    if isinstance(p_model, str) and p_model and p_model != "default":
                        if "/" in p_model:
                            return p_model
                        return f"{raw_agent_provider}/{p_model}"

            # 1c. Provider default (never fall through to platform default)
            return f"{raw_agent_provider}/default"

        # 2. Agent explicit model override (without explicit provider)
        if raw_agent_model and raw_agent_model.lower() != "default" and raw_agent_model.lower() not in KNOWN_PROVIDERS:
            return raw_agent_model

        # 3. Global Default provider + model from Settings Studio
        if self.state_store:
            prov_data = self.state_store.get_setting("provider_settings")
            if isinstance(prov_data, dict):
                def_model = prov_data.get("default_model_id")
                if isinstance(def_model, str) and def_model and def_model != "default":
                    return def_model
                def_prov = prov_data.get("default_provider_id")
                if isinstance(def_prov, str) and def_prov and def_prov != "default":
                    return f"{def_prov}/default"

        # 4. Gateway defaults
        if self.gateway:
            gw_def = getattr(self.gateway, "default_model_id", None)
            if isinstance(gw_def, str) and gw_def and gw_def != "default":
                return gw_def
            gw_prov = getattr(self.gateway, "default_provider_id", None)
            if isinstance(gw_prov, str) and gw_prov:
                return f"{gw_prov}/default"
        return "default"

    def _ensure_agent_provider_adapter(self, agent: AgentProfile) -> None:
        """Register or update custom provider adapter for agent if configured [CARD-156]."""
        if not self.gateway:
            return
        prov = getattr(agent, "provider", "default")
        if not prov or prov == "default":
            return
        api_base_url = getattr(agent, "api_base_url", None)
        api_key = getattr(agent, "api_key", None)
        if not api_base_url and not api_key:
            return

        clean_prov = str(prov).strip().lower()
        clean_url = (api_base_url or "").strip()
        clean_key = (api_key or "").strip()

        from src.application.gateway.ports import LLMProviderPort
        from src.infrastructure.gateway.anthropic_adapter import AnthropicProviderAdapter
        from src.infrastructure.gateway.ollama_adapter import OllamaProviderAdapter
        from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter

        adapter: LLMProviderPort
        if clean_prov == "ollama" or ":11434" in clean_url:
            adapter = OllamaProviderAdapter(base_url=clean_url or "http://127.0.0.1:11434", provider_id=clean_prov)
        elif clean_prov == "anthropic":
            adapter = AnthropicProviderAdapter(
                base_url=clean_url or "https://api.anthropic.com/v1",
                api_key=clean_key,
                provider_id=clean_prov,
            )
        else:
            adapter = OpenAIProviderAdapter(
                base_url=clean_url or "https://api.openai.com/v1",
                api_key=clean_key,
                provider_id=clean_prov,
            )
        self.gateway.register_provider(adapter)

    def _resolve_context_limit(self, agent: Optional[AgentProfile] = None, model_name: Optional[str] = None) -> int:
        """Unified 3-tier Context Limit Resolution Cascade [CARD-162]."""
        return resolve_agent_context_limit(
            agent=agent,
            state_store=self.state_store,
            fallback_model=model_name,
        )

    def _build_effective_system_message(
        self,
        agent: AgentProfile,
        user_content: Optional[str] = None,
    ) -> ChatMessage:
        """
        Constructs system prompt enriched with auto-recalled episodic facts [REQ-EPISODIC-003].
        """
        tones_lookup = None
        if self.state_store and hasattr(self.state_store, "list_tones"):
            try:
                tones_list = self.state_store.list_tones()
                tones_lookup = {t.id: t.directive for t in tones_list}
            except Exception:
                tones_lookup = None
        base_prompt = agent.get_effective_system_prompt(tones_lookup=tones_lookup)
        from src.application.skills.user_catalog import render_skill_index

        skill_block = render_skill_index(
            getattr(agent, "allowed_skill", None),
            self.user_skill_catalog,
            agent_id=getattr(agent, "id", None),
        )
        if skill_block:
            base_prompt = f"{base_prompt}\n\n{skill_block}"
        if user_content and self.state_store and hasattr(self.state_store, "search_facts"):
            try:
                matched_facts = self.state_store.search_facts(query=user_content, limit=4)
                if matched_facts:
                    from src.application.skills.memory_tools import render_memory_context

                    memory_block = render_memory_context(matched_facts)
                    if memory_block:
                        base_prompt = f"{base_prompt}\n\n{memory_block}"
            except Exception as e:
                logger.debug(f"Episodic memory auto-recall skipped: {e}")

        # Cognitive Memory Brain Injection [CARD-116, CARD-405]
        if getattr(agent, "memory_enabled", True) and getattr(agent, "id", None) != "direct":
            try:
                from src.application.memory.assembler import MemoryContextAssembler
                from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

                agent_repo = AgentMemoryRepository(agent_id=agent.id, data_dir=self.data_dir)
                agent_repo.initialize_schema()
                model_name = self._resolve_model(agent)
                ctx_limit = self._resolve_context_limit(agent, model_name)
                assembler = MemoryContextAssembler(repository=agent_repo)
                cog_block = assembler.assemble(
                    context_limit=ctx_limit,
                    user_query=user_content,
                    pinned_override=getattr(agent, "pinned_memory", None),
                )
                memory_preamble = (
                    f"[Agent Brain - Cognitive Memory System]\n"
                    f"You have a dedicated cognitive memory database ({agent.id}_memory.db) that retains user preferences, "
                    f"domain facts, and session milestones across conversations.\n"
                    f"You have two cognitive memory tools: `recall_agent_memory` to search stored facts and past milestones, "
                    f"and `memorize_fact` to persist key learnings or user preferences into your database."
                )
                if cog_block:
                    base_prompt = f"{base_prompt}\n\n{memory_preamble}\n\n{cog_block}"
                else:
                    base_prompt = f"{base_prompt}\n\n{memory_preamble}"
            except Exception as e:
                logger.debug(f"Per-agent cognitive memory assembly skipped: {e}")

        # Active Selected Project Context [Projects Studio / SDLC]
        # Skill-gated: only agents possessing project tools (or developer) receive workspace grounding.
        if self.state_store:
            try:
                from pathlib import Path

                from src.application.sdlc.projects_service import ProjectsService

                is_developer = getattr(agent, "id", None) == "developer"
                allowed_tools: set[str] = set(getattr(agent, "allowed_tool_names", None) or [])
                if not is_developer and hasattr(self, "tool_registry") and hasattr(self.tool_registry, "get_tools_for_agent"):
                    try:
                        agent_tools = self.tool_registry.get_tools_for_agent(agent)
                        allowed_tools.update(t.name for t in agent_tools)
                    except Exception:
                        pass
                has_project_tools = bool(
                    allowed_tools.intersection(
                        {"read_project_file", "write_project_file", "list_project_dir", "cli_exec", "git_status", "git_diff"}
                    )
                )

                if is_developer or has_project_tools:
                    proj_svc = ProjectsService(store=self.state_store)
                    selected_proj = proj_svc.get_selected()
                    if selected_proj and selected_proj.get("path"):
                        proj_name = selected_proj.get("name") or selected_proj.get("slug") or "Active Project"
                        proj_path = selected_proj.get("path")
                        has_write = is_developer or bool(
                            allowed_tools.intersection({"write_project_file", "cli_exec"})
                        )
                        tool_guidance = (
                            "Use write_project_file, read_project_file, and list_project_dir to manage files inside this project, and cli_exec to run tests and scripts directly within this directory."
                            if has_write
                            else "Use read_project_file and list_project_dir to inspect and review files inside this project."
                        )
                        project_context = (
                            "## Active Selected Project\n"
                            f"- Name: {proj_name}\n"
                            f"- Path: {proj_path}\n"
                            f"All project code, tests, scripts, and CLI commands should target this project directory unless explicitly instructed otherwise. {tool_guidance}"
                        )
                        extra_lines = []
                        root_path = Path(proj_path)
                        if (root_path / "AGENTS.md").is_file():
                            extra_lines.append("Governance: AGENTS.md present at project root.")
                        cards_dir = root_path / ".agents" / "cards"
                        if not cards_dir.is_dir():
                            cards_dir = root_path / "docs" / "cards"
                        if cards_dir.is_dir():
                            card_files = [p.name for p in cards_dir.glob("CARD-*.md") if p.is_file()]
                            if card_files:
                                recent = sorted(card_files)[-5:]
                                extra_lines.append(f"Active Work Cards ({len(card_files)} total): Recent: {', '.join(recent)}")
                        if extra_lines:
                            project_context = project_context + "\n" + "\n".join(f"- {line}" for line in extra_lines)
                        base_prompt = f"{base_prompt}\n\n{project_context}"
            except Exception as e:
                logger.debug(f"Active project context injection skipped: {e}")

        # ADR-0054 / CARD-362 / CARD-377: Compact 1-line capability index when direct mode is not active
        if getattr(agent, "id", None) != "direct":
            cap_lines = [
                "## Available Capabilities & Skills (Demand-Paged)",
                "Use `activate_skill` to load full tool schemas for any domain:",
                "- `wiki`: Local-first knowledge base notes, markdown documents, and PARA vault search.",
                "- `coding`: File reading, writing, editing, and terminal script execution in the active project.",
                "- `diagnostics`: System health checks, hardware metrics, and background service diagnostics.",
                "- `tasks`: Routine automation, cron schedule management, and standing background jobs.",
                "- `mcp-engineering`: FastMCP server development, JSON-RPC protocol testing, Docker container deployment, and AutoReiv mounting.",
            ]
            discovered_mcp: dict[str, int] = {}
            if hasattr(self, "tool_registry") and hasattr(self.tool_registry, "_tools"):
                for t_name in self.tool_registry._tools:
                    if t_name.startswith("mcp_"):
                        parts = t_name.split("_")
                        if len(parts) >= 3:
                            srv_name = parts[1]
                            discovered_mcp[srv_name] = discovered_mcp.get(srv_name, 0) + 1
            for srv in getattr(agent, "mcp_servers", []) or []:
                s_name = srv.name if hasattr(srv, "name") else (srv.get("name") if isinstance(srv, dict) else "")
                if s_name and s_name not in discovered_mcp:
                    discovered_mcp[s_name] = 0

            for srv_name, count in sorted(discovered_mcp.items()):
                tools_str = f" ({count} tools)" if count > 0 else ""
                cap_lines.append(
                    f"- `{srv_name}`: External integration tools via {srv_name.capitalize()} MCP server{tools_str}. "
                    f"Use `activate_skill(['{srv_name}'])` or ask directly."
                )

            capability_index = "\n".join(cap_lines)
            base_prompt = f"{base_prompt}\n\n{capability_index}"

        self._last_progressive_skills = [skill_block] if skill_block else []
        self._last_episodic_memory = [
            m
            for m in [
                memory_block if "memory_block" in locals() else None,
                cog_block if "cog_block" in locals() else None,
            ]
            if m
        ]

        return ChatMessage(role=Role.SYSTEM, content=base_prompt)

    def _get_discovered_mcp_domains(self) -> List[str]:
        """Return unique MCP server names discovered from registered tools [CARD-377]."""
        domains: set[str] = set()
        if hasattr(self, "tool_registry") and hasattr(self.tool_registry, "_tools"):
            for t_name in self.tool_registry._tools:
                if t_name.startswith("mcp_"):
                    parts = t_name.split("_")
                    if len(parts) >= 3:
                        domains.add(parts[1].lower())
        return sorted(domains)

    @classmethod
    def _match_intent_skills(
        cls,
        user_content: Optional[str],
        extra_domains: Optional[Sequence[str]] = None,
    ) -> List[str]:
        """
        Layer 1 Fast-Path Intent Matcher [CARD-339, ADR-0052, CARD-377].
        0ms regex/keyword triggers to pre-mount specialized platform skills based on user prompt.
        """
        if not user_content:
            return []
        text = str(user_content).lower()
        matched: List[str] = []
        import re

        # Wiki knowledge base intent
        if re.search(r"\b(wiki|knowledge\s*base|notes?|documentation)\b", text):
            matched.append("wiki")

        # Diagnostics & homelab health intent
        if re.search(
            r"\b(diagnostics?|health|system\s*status|metrics?|telemetry|ollama|gpu|cpu|ram|memory\s*usage|disk\s*space)\b",
            text,
        ):
            matched.append("diagnostics")

        # Tasks, routines, jobs intent
        if re.search(r"\b(tasks?|routines?|jobs?|cron|schedule|scheduled)\b", text):
            matched.append("wiki_tasks")

        # Coding, repository, files intent
        if re.search(
            r"\b(code|coding|git|repo|repository|commit|diff|patch|refactor|tests?|pytest|script)\b", text
        ) or re.search(r"\b(read|write|edit)\s+(file|code|script)\b", text):
            matched.append("coding")

        # MCP server engineering intent [CARD-394]
        if re.search(r"\b(mcp|fastmcp|mcp-engineering)\b", text) and any(
            w in text for w in ("scaffold", "server", "deploy", "register", "test", "container", "service")
        ):
            matched.append("mcp-engineering")

        # Native custom tool lane [CARD-423]
        if re.search(r"\b(native-tool-engineering|register_native_tool|plan_native_folder)\b", text) or (
            "native" in text and "tool" in text
        ):
            matched.append("native-tool-engineering")

        # External MCP server domains [CARD-377]
        for domain in extra_domains or []:
            clean_dom = str(domain).strip().lower()
            if clean_dom and re.search(rf"\b{re.escape(clean_dom)}\b", text):
                if clean_dom not in matched:
                    matched.append(clean_dom)

        return matched

    def _resolve_active_tools(
        self,
        agent: AgentProfile,
        user_content: Optional[str] = None,
        matched_capability_ids: Optional[list] = None,
        active_skills: Optional[Sequence[str]] = None,
    ) -> List[Any]:
        """
        RBAC allowlist and dynamic demand-paged capability scoping [CARD-339, CARD-362, ADR-0054].
        - For 'direct': returns [] (zero tools pass-through).
        - For 'autoreiv': by default mounts ONLY 5 lean platform primitives (<800 tokens),
          plus any dynamically activated skills from Layer 1 intent or Layer 2 activate_skill.
        - For specialist agents: mounts their declared allowed_skills and pack_tools.
        - Enforces Rule of 7: clamps visible tools to MAX_ACTIVE_TOOLS_PER_TURN (8).
        """
        if getattr(agent, "id", None) == "direct":
            return []

        _ = user_content  # query ranking is not used at turn time
        ids = matched_capability_ids
        if ids is None:
            ids = getattr(self, "_turn_matched_capability_ids", None)

        # CARD-362 / ADR-0054: extract skill capabilities into active_skills for dynamic demand paging
        if ids:
            derived_skills = [str(cid).strip()[len("skill.") :] for cid in ids if str(cid).strip().startswith("skill.")]
            if derived_skills:
                active_skills = list(dict.fromkeys(list(active_skills or []) + derived_skills))

        tools = list(self.tool_registry.get_tools_for_agent(agent, active_skills=active_skills))
        try:
            from src.application.safety.tool_policy_gate import (
                EDUCATION_FORBIDDEN_WIKI_TOOLS,
                _capability_tool_names,
            )

            subset = _capability_tool_names(ids)
            if subset is not None:
                tools = [t for t in tools if getattr(t, "name", "") in subset] or tools
            else:
                # Still strip Education-forbidden ghosts when Education skills matched.
                id_list = [str(x) for x in (ids or [])]
                if any(s.endswith("education-priming") or s.endswith("education-dual-coding") for s in id_list):
                    tools = [t for t in tools if getattr(t, "name", "") not in EDUCATION_FORBIDDEN_WIKI_TOOLS]
        except Exception:
            pass

        # CARD-362 / ADR-0054 / CARD-377: Rule of 7 entropy budget clamping (MAX_ACTIVE_TOOLS_PER_TURN = 8)
        if len(tools) > MAX_ACTIVE_TOOLS_PER_TURN:
            active_skill_set = {str(s).strip().lower() for s in (active_skills or [])}
            import re
            user_tokens = set(re.findall(r"\b[a-z]{3,}\b", (user_content or "").lower())) if user_content else set()

            from src.application.agent_packs.schema import (
                CAPABILITY_AUTHORING_TOOL_NAMES,
                DYNAMIC_SKILL_TOOLS,
                PLATFORM_SKILL_TOOLS,
            )
            from src.application.tools.native_packaging import AUTHORING_TOOL_NAMES, load_native_tool_names

            native_names = load_native_tool_names(self.state_store)
            text_l = (user_content or "").lower()

            def _tool_priority(t: Any) -> tuple[int, int, str]:
                name = getattr(t, "name", "")
                desc = (getattr(t, "description", "") or "").lower()
                name_words = set(re.findall(r"\b[a-z]{3,}\b", name.lower()))
                desc_words = set(re.findall(r"\b[a-z]{3,}\b", desc))
                overlap = len((name_words | desc_words) & user_tokens)

                # Named native custom tools and the authoring tools stay visible [CARD-423].
                if name and name.lower() in text_l and (name in native_names or name in AUTHORING_TOOL_NAMES):
                    return (0, -overlap, name)

                # Opening a named allowlisted runbook keeps skill_view inside the turn cap [CARD-427].
                if name == "skill_view":
                    allowed_ids = {
                        str(sid).strip().lower()
                        for sid in (getattr(agent, "allowed_skill", None) or [])
                        if str(sid).strip()
                    }
                    if any(sid in text_l for sid in allowed_ids):
                        return (0, 0, name)

                # Naming the catalog tool keeps it inside the turn cap [CARD-428].
                if name == "list_user_skill_packs" and "list_user_skill_packs" in text_l:
                    return (0, 0, name)

                # Builder HITL stays off the default eight until the turn asks for it [CARD-429].
                # "scaffold an agent pack" must keep scaffold_agent_pack inside the cap [CARD-431].
                if name in CAPABILITY_AUTHORING_TOOL_NAMES:
                    if _capability_authoring_requested(text_l):
                        named = name in text_l or name.replace("_", " ") in text_l
                        if (
                            name == "scaffold_agent_pack"
                            and "scaffold" in text_l
                            and ("agent" in text_l or "pack" in text_l)
                        ):
                            named = True
                        return (0, 0 if named else 1, name)
                    return (3, 0, name)

                # Priority 0: Tools matching active skill prefix/names (including mcp_<skill>_ and declared tool sets)
                is_active = any(
                    name in DYNAMIC_SKILL_TOOLS.get(sk, ())
                    or name in PLATFORM_SKILL_TOOLS.get(sk, ())
                    or name.startswith(f"{sk}_")
                    or name.startswith(f"mcp_{sk}_")
                    or f"_{sk}_" in name.lower()
                    for sk in active_skill_set
                )
                if is_active:
                    boost = 1 if any(k in name for k in ("execute", "info", "list", "get", "status")) else 0
                    score = -(overlap * 2 + boost)
                    return (0, score, name)

                # Priority 1: Core baseline coordination primitives
                if name in BASELINE_COORDINATION_TOOLS:
                    return (1, 0, name)
                # Priority 2: Other generic / unactivated tools (ranked by query overlap)
                return (2, -overlap, name)

            tools.sort(key=_tool_priority)
            tools = tools[:MAX_ACTIVE_TOOLS_PER_TURN]

        return tools

    async def run_turn(
        self,
        agent: AgentProfile,
        session_id: str,
        user_content: Optional[str] = None,
        save_to_history: bool = True,
        approval_mode: str = "ask",
        resume: bool = False,
        routine_id: Optional[str] = None,
        phase_id: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> ChatMessage:
        """
        Execute a full synchronous/batched ReAct agent turn with tool execution.

        When resume=True, continue from persisted history without appending a USER message.
        """
        self._ace_tool_errors = []
        self._turn_matched_capability_ids = self._matched_capability_ids_for_job(job_id=job_id, phase_id=phase_id)
        if resume:
            user_content = None
        if user_content and save_to_history:
            user_msg = ChatMessage(role=Role.USER, content=user_content)
            self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=user_msg)

        history = list(self.state_store.get_messages(session_id=session_id))
        if user_content and not save_to_history:
            history.append(ChatMessage(role=Role.USER, content=user_content))

        turn_active_skills: Set[str] = set(
            self._match_intent_skills(user_content, extra_domains=self._get_discovered_mcp_domains())
        )
        system_msg = self._build_effective_system_message(agent, user_content)
        active_tools = self._resolve_active_tools(
            agent,
            user_content,
            matched_capability_ids=self._turn_matched_capability_ids,
            active_skills=list(turn_active_skills) if agent.id == "autoreiv" else None,
        )
        tool_schema_chars = (
            sum(
                len(dumps_jsonable(t.model_dump(mode="json") if hasattr(t, "model_dump") else getattr(t, "__dict__", {})))
                for t in active_tools
            )
            if active_tools
            else 0
        )
        self._last_turn_tool_stats = {
            "active_tool_count": len(active_tools),
            "tool_schema_chars": tool_schema_chars,
        }
        model_name = self._resolve_model(agent)

        cycle_detector = CycleDetector(max_repeats=3)
        react_ctx = {
            "phase_id": phase_id,
            "job_id": job_id,
            "assigned_agent_id": agent.id,
        }

        trace_id = session_id or str(uuid.uuid4())
        provider_name = getattr(agent, "provider", None) or (agent.model.split("/")[0] if "/" in agent.model else None)
        turn_span_id = None
        self._ensure_agent_provider_adapter(agent)
        last_turn_end = None

        for turn_idx in range(agent.max_turns):
            turn_start = time.perf_counter()
            inter_step_latency_ms = ((turn_start - last_turn_end) * 1000) if last_turn_end is not None else None
            self._transition_react_state(ReactState.THINKING, turn_idx, **react_ctx)
            context_limit = self._resolve_context_limit(agent, model_name)
            nested_ctx = min(context_limit, NESTED_COMPLETE_MAX_CTX)
            scaled_tool_chars = resolve_max_tool_chars(nested_ctx)
            compacted_messages = ContextCompactor.compact(
                [system_msg] + history,
                model_name=model_name,
                max_tokens=max(1000, int(nested_ctx * 0.75)),
                keep_last_n_turns=4,
                max_tool_chars=scaled_tool_chars,
                preserve_root_intent=True,
            )
            req = CompletionRequest(
                model=model_name,
                messages=compacted_messages,
                tools=active_tools or None,
                num_ctx=nested_ctx,
                max_tokens=NESTED_COMPLETE_MAX_TOKENS,
            )
            prep_end = time.perf_counter()
            harness_prep_ms = (prep_end - turn_start) * 1000

            resp: Optional[CompletionResponse] = None
            try:
                resp = await self.gateway.complete(req)
                turn_dur_ms = (time.perf_counter() - turn_start) * 1000

                prompt_tokens = (
                    resp.usage.get("prompt_tokens", 0)
                    if isinstance(resp.usage, dict)
                    else (getattr(resp.usage, "prompt_tokens", 0) if resp.usage else 0)
                )
                comp_tokens = (
                    resp.usage.get("completion_tokens", 0)
                    if isinstance(resp.usage, dict)
                    else (getattr(resp.usage, "completion_tokens", 0) if resp.usage else 0)
                )

                effective_user_prompt = user_content or ""
                if not effective_user_prompt:
                    for m in reversed(history):
                        if m.role == Role.USER and m.content:
                            effective_user_prompt = m.content
                            break

                history_msgs = [
                    m for m in compacted_messages if m.role != Role.SYSTEM and m.content != effective_user_prompt
                ]
                tool_results = [m.content for m in compacted_messages if m.role == Role.TOOL and m.content]

                token_breakdown = calculate_token_attribution(
                    user_prompt=effective_user_prompt,
                    agent_persona=getattr(agent, "system_prompt", ""),
                    tool_definitions=active_tools,
                    progressive_skills=getattr(self, "_last_progressive_skills", None),
                    episodic_memory=getattr(self, "_last_episodic_memory", None),
                    compacted_history=history_msgs,
                    tool_results_injected=tool_results,
                    completion=resp.message.content if resp.message else "",
                    reasoning=getattr(resp, "reasoning_content", None),
                )
                timing_breakdown = calculate_timing_attribution(
                    harness_prep_ms=harness_prep_ms,
                    ttft_ms=None,
                    total_round_trip_ms=turn_dur_ms,
                    completion_tokens=comp_tokens or token_breakdown.completion,
                    inter_step_latency_ms=inter_step_latency_ms,
                )

                turn_span = self.telemetry.record_turn_span(
                    agent_id=agent.id,
                    session_id=session_id,
                    model=resp.model,
                    provider=provider_name,
                    duration_ms=turn_dur_ms,
                    prompt_tokens=prompt_tokens or token_breakdown.total_prompt_tokens,
                    completion_tokens=comp_tokens or token_breakdown.completion,
                    success=True,
                    trace_id=trace_id,
                    metadata={
                        "token_breakdown": token_breakdown.to_dict(),
                        "timing_breakdown": timing_breakdown.to_dict(),
                        "active_tool_count": len(active_tools),
                        "tool_schema_chars": tool_schema_chars,
                        "step_context": {
                            "job_id": job_id,
                            "phase_id": phase_id,
                        },
                    },
                )
                turn_span_id = turn_span.id
            except Exception as e:
                turn_dur_ms = (time.perf_counter() - turn_start) * 1000
                timing_breakdown = calculate_timing_attribution(
                    harness_prep_ms=harness_prep_ms if "harness_prep_ms" in locals() else 0.0,
                    ttft_ms=None,
                    total_round_trip_ms=turn_dur_ms,
                    completion_tokens=0,
                    inter_step_latency_ms=inter_step_latency_ms,
                )
                self.telemetry.record_turn_span(
                    agent_id=agent.id,
                    session_id=session_id,
                    model=model_name,
                    provider=provider_name,
                    duration_ms=turn_dur_ms,
                    success=False,
                    error_message=str(e),
                    trace_id=trace_id,
                    metadata={"timing_breakdown": timing_breakdown.to_dict()},
                )
                self._transition_react_state(ReactState.FAILED, turn_idx, **react_ctx)
                self._ace_flush_failed_turn(session_id=session_id, agent_id=agent.id, failed=True, error_message=str(e))
                if isinstance(e, RateLimitError):
                    rate_limit_text = (
                        f"⚠️ Rate limit reached on {provider_name} ({model_name}): {e.message}. "
                        "Please wait or update provider configuration."
                    )
                    rate_limit_msg = ChatMessage(role=Role.ASSISTANT, content=rate_limit_text)
                    if save_to_history:
                        self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=rate_limit_msg)
                    return rate_limit_msg
                raise

            assistant_msg = resp.message

            # Text generation repetition loop check [REQ-RESIL-003]
            if assistant_msg.content and cycle_detector.record_and_check_text(assistant_msg.content):
                self._transition_react_state(ReactState.FAILED, turn_idx, **react_ctx)
                cycle_msg = ChatMessage(
                    role=Role.ASSISTANT,
                    content="Execution terminated: Detected repetitive text generation loop.",
                )
                if save_to_history:
                    self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=cycle_msg)
                self._ace_flush_failed_turn(
                    session_id=session_id,
                    agent_id=agent.id,
                    failed=True,
                    error_message=cycle_msg.content,
                )
                return cycle_msg

            # If no tool calls, turn is complete
            if not assistant_msg.tool_calls:
                user_req_text = user_content or ""
                if not user_req_text and history:
                    for hm in reversed(history):
                        if hm.role == Role.USER and hm.content:
                            user_req_text = hm.content
                            break

                gap = CapabilityDetector.detect(user_prompt=user_req_text, assistant_response=assistant_msg.content)
                if gap:
                    try:
                        self.capability_gap_repo.create_gap(
                            agent_id=agent.id,
                            user_prompt=gap.user_prompt,
                            missing_capability=gap.missing_capability,
                            context_summary=gap.context_summary,
                            suggested_tool_name=gap.suggested_tool_name,
                            session_id=session_id,
                        )
                    except Exception as e:
                        logger.warning("Failed to record capability gap: %s", e)

                self._transition_react_state(ReactState.DONE, turn_idx, **react_ctx)
                if save_to_history:
                    self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=assistant_msg)
                self._ace_flush_failed_turn(session_id=session_id, agent_id=agent.id, failed=False)
                return assistant_msg

            # Tool call cycle detection [REQ-RESIL-003]
            if cycle_detector.record_and_check(assistant_msg.tool_calls):
                self._transition_react_state(ReactState.FAILED, turn_idx, **react_ctx)
                cycle_msg = ChatMessage(
                    role=Role.ASSISTANT,
                    content="Execution terminated: Detected repetitive cycle calling tools.",
                )
                if save_to_history:
                    self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=cycle_msg)
                self._ace_flush_failed_turn(
                    session_id=session_id,
                    agent_id=agent.id,
                    failed=True,
                    error_message=cycle_msg.content,
                )
                return cycle_msg

            self._transition_react_state(ReactState.CALLING_TOOLS, turn_idx, **react_ctx)

            # Handle tool calls
            if save_to_history:
                self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=assistant_msg)
            history.append(assistant_msg)

            skills_changed = False
            for tc in assistant_msg.tool_calls:
                gated = self._gate_tool_call(
                    tc,
                    session_id,
                    agent,
                    approval_mode=approval_mode,
                    routine_id=routine_id,
                    matched_capability_ids=self._matched_capability_ids_for_job(react_ctx.get("job_id")),
                    job_id=react_ctx.get("job_id"),
                )
                if gated is not None:
                    tool_res = gated
                else:
                    tool_res = await self.execute_and_scrub_tool(
                        tc,
                        agent,
                        session_id=session_id,
                        approval_mode=approval_mode,
                        job_id=react_ctx.get("job_id"),
                        active_skills=list(turn_active_skills),
                    )

                if tc.name == "activate_skill" and tool_res.success:
                    args = tc.arguments if isinstance(tc.arguments, dict) else {}
                    new_skills = args.get("skills", [])
                    if isinstance(new_skills, list):
                        for s in new_skills:
                            s_clean = str(s).strip().lower()
                            if s_clean and s_clean not in turn_active_skills:
                                turn_active_skills.add(s_clean)
                                skills_changed = True

                is_hitl = bool(tool_res.error and str(tool_res.error).startswith("approval_required:"))
                tool_status = "hitl_paused" if is_hitl else ("ok" if tool_res.success else "error")
                tool_success = True if is_hitl else tool_res.success

                if tool_res.success:
                    tool_content = dumps_tool_output(tool_res.output)
                else:
                    tool_content = tool_res.error or "Tool execution error"

                payload_bytes = len((tool_content or "").encode("utf-8"))
                tc_args = getattr(tc, "arguments", None) or getattr(tc, "args", None) or {}

                self.telemetry.record_tool_span(
                    agent_id=agent.id,
                    session_id=session_id,
                    tool_name=tc.name,
                    duration_ms=tool_res.duration_ms,
                    success=tool_success,
                    status=tool_status,
                    error_message=tool_res.error,
                    trace_id=trace_id,
                    parent_span_id=turn_span_id,
                    metadata={"payload_bytes": payload_bytes, "arguments": tc_args},
                )
                self._ace_note_tool(tc.name, tool_res.success, tool_res.error)

                tool_msg = ChatMessage(
                    role=Role.TOOL,
                    content=tool_content,
                    name=tc.name,
                    tool_call_id=tc.id,
                )
                if save_to_history:
                    self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=tool_msg)
                history.append(tool_msg)

                if tool_res.error and str(tool_res.error).startswith("approval_required:"):
                    parked = {
                        "status": "approval_required",
                        "approval_id": tool_res.output.get("approval_id") if isinstance(tool_res.output, dict) else "",
                        "tool_name": tc.name,
                        "arguments": tc.arguments if isinstance(tc.arguments, dict) else {},
                        "message": tool_res.output.get("message")
                        if isinstance(tool_res.output, dict)
                        else "Approval required",
                    }
                    parked_msg = ChatMessage(role=Role.ASSISTANT, content=dumps_jsonable(parked))
                    if save_to_history:
                        self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=parked_msg)
                    self._transition_react_state(ReactState.PARKED, turn_idx, **react_ctx)
                    return parked_msg

            if skills_changed:
                active_tools = self._resolve_active_tools(
                    agent,
                    user_content,
                    matched_capability_ids=self._turn_matched_capability_ids,
                    active_skills=list(turn_active_skills) if agent.id == "autoreiv" else None,
                )
            last_turn_end = time.perf_counter()

        self._transition_react_state(ReactState.FAILED, agent.max_turns, **react_ctx)
        limit_msg = ChatMessage(
            role=Role.ASSISTANT,
            content=f"Execution terminated: Max turn budget of {agent.max_turns} reached.",
        )
        self._ace_flush_failed_turn(
            session_id=session_id, agent_id=agent.id, failed=True, error_message=limit_msg.content
        )
        if save_to_history:
            self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=limit_msg)
        return limit_msg

    async def stream_turn(
        self,
        agent: AgentProfile,
        session_id: str,
        user_content: Optional[str] = None,
        approval_mode: str = "ask",
        resume: bool = False,
        phase_id: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> AsyncIterator[KernelEvent]:
        """
        Execute an asynchronous streaming agent turn with live token and tool lifecycle events.

        When resume=True or user_content is empty, continue from persisted history
        without appending a USER message [REQ-HITL-034].
        """
        self._ace_tool_errors = []
        self._turn_matched_capability_ids = self._matched_capability_ids_for_job(job_id=job_id, phase_id=phase_id)
        if resume:
            user_content = None
        if user_content:
            user_msg = ChatMessage(role=Role.USER, content=user_content)
            self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=user_msg)

        react_ctx = {
            "phase_id": phase_id,
            "job_id": job_id,
            "assigned_agent_id": agent.id,
        }
        history = self.state_store.get_messages(session_id=session_id)
        if resume:
            replay = self._nested_park_replay_events(history)
            if replay:
                parked_ev = self._transition_react_state(ReactState.PARKED, 0, **react_ctx)
                if parked_ev:
                    yield parked_ev
                for ev in replay:
                    yield ev
                return
        turn_active_skills: Set[str] = set(
            self._match_intent_skills(user_content, extra_domains=self._get_discovered_mcp_domains())
        )
        system_msg = self._build_effective_system_message(agent, user_content)
        active_tools = self._resolve_active_tools(
            agent,
            user_content,
            matched_capability_ids=self._turn_matched_capability_ids,
            active_skills=list(turn_active_skills) if agent.id == "autoreiv" else None,
        )
        tool_schema_chars = (
            sum(
                len(dumps_jsonable(t.model_dump(mode="json") if hasattr(t, "model_dump") else getattr(t, "__dict__", {})))
                for t in active_tools
            )
            if active_tools
            else 0
        )
        self._last_turn_tool_stats = {
            "active_tool_count": len(active_tools),
            "tool_schema_chars": tool_schema_chars,
        }
        model_name = self._resolve_model(agent)

        cycle_detector = CycleDetector(max_repeats=3)

        trace_id = session_id or str(uuid.uuid4())
        provider_name = getattr(agent, "provider", None) or (agent.model.split("/")[0] if "/" in agent.model else None)
        turn_span_id = None
        self._ensure_agent_provider_adapter(agent)
        last_turn_end = None

        for turn_idx in range(agent.max_turns):
            thinking_ev = self._transition_react_state(ReactState.THINKING, turn_idx, **react_ctx)
            if thinking_ev:
                yield thinking_ev
            turn_start = time.perf_counter()
            inter_step_latency_ms = ((turn_start - last_turn_end) * 1000) if last_turn_end is not None else None
            first_token_time = None
            ttft_ms = None
            context_limit = self._resolve_context_limit(agent, model_name)
            scaled_tool_chars = resolve_max_tool_chars(context_limit)
            compacted_messages = ContextCompactor.compact(
                [system_msg] + history,
                model_name=model_name,
                max_tokens=max(1000, int(context_limit * 0.75)),
                keep_last_n_turns=4,
                max_tool_chars=scaled_tool_chars,
                preserve_root_intent=True,
            )
            req = CompletionRequest(
                model=model_name,
                messages=compacted_messages,
                tools=active_tools or None,
                num_ctx=context_limit,
                stream=True,
            )
            prep_end = time.perf_counter()
            harness_prep_ms = (prep_end - turn_start) * 1000

            accumulated_content = []
            accumulated_reasoning = []
            collected_tool_calls: List[ToolCall] = []

            # Close the parent LLM HTTP stream BEFORE tools (child handoff complete()).
            stream_gen = None
            try:
                stream_gen = self.gateway.stream(req, demux_reasoning=True)
                async for chunk in stream_gen:
                    if first_token_time is None and (chunk.content or chunk.reasoning_content or chunk.tool_calls):
                        first_token_time = time.perf_counter()
                        ttft_ms = (first_token_time - turn_start) * 1000

                    if chunk.content or chunk.reasoning_content:
                        if chunk.content:
                            accumulated_content.append(chunk.content)
                        if chunk.reasoning_content:
                            accumulated_reasoning.append(chunk.reasoning_content)
                        yield KernelEvent(
                            event_type=KernelEventType.TOKEN,
                            content=chunk.content,
                            reasoning_content=chunk.reasoning_content,
                        )

                    if chunk.tool_calls:
                        collected_tool_calls.extend(chunk.tool_calls)
                    if chunk.is_finished:
                        break
            except Exception as e:
                turn_dur_ms = (time.perf_counter() - turn_start) * 1000
                timing_breakdown = calculate_timing_attribution(
                    harness_prep_ms=harness_prep_ms if "harness_prep_ms" in locals() else 0.0,
                    ttft_ms=ttft_ms,
                    total_round_trip_ms=turn_dur_ms,
                    completion_tokens=0,
                    inter_step_latency_ms=inter_step_latency_ms,
                )
                self.telemetry.record_turn_span(
                    agent_id=agent.id,
                    session_id=session_id,
                    model=model_name,
                    provider=provider_name,
                    duration_ms=turn_dur_ms,
                    success=False,
                    error_message=str(e),
                    trace_id=trace_id,
                    metadata={"timing_breakdown": timing_breakdown.to_dict()},
                )
                failed_ev = self._transition_react_state(ReactState.FAILED, turn_idx, **react_ctx)
                if failed_ev:
                    yield failed_ev
                self._ace_flush_failed_turn(session_id=session_id, agent_id=agent.id, failed=True, error_message=str(e))
                if isinstance(e, RateLimitError):
                    rate_limit_text = (
                        f"⚠️ Rate limit reached on {provider_name} ({model_name}): {e.message}. "
                        "Please wait or update provider configuration."
                    )
                    self.state_store.save_message(
                        session_id=session_id,
                        agent_id=agent.id,
                        message=ChatMessage(role=Role.ASSISTANT, content=rate_limit_text),
                    )
                    yield KernelEvent(event_type=KernelEventType.TOKEN, content=rate_limit_text)
                    yield KernelEvent(event_type=KernelEventType.ERROR, content=rate_limit_text, is_finished=True)
                    return
                yield KernelEvent(event_type=KernelEventType.ERROR, content=str(e), is_finished=True)
                return
            finally:
                closer = getattr(stream_gen, "aclose", None)
                if callable(closer):
                    await closer()

            full_content = "".join(accumulated_content)
            full_reasoning = "".join(accumulated_reasoning) if accumulated_reasoning else None
            turn_dur_ms = (time.perf_counter() - turn_start) * 1000

            effective_user_prompt = user_content
            if not effective_user_prompt:
                last_user = next((m for m in reversed(compacted_messages) if m.role == Role.USER), None)
                effective_user_prompt = last_user.content if last_user else ""

            history_msgs = [
                m for m in compacted_messages if m.role != Role.SYSTEM and m.content != effective_user_prompt
            ]
            tool_results = [m.content for m in compacted_messages if m.role == Role.TOOL and m.content]

            token_breakdown = calculate_token_attribution(
                user_prompt=effective_user_prompt,
                agent_persona=getattr(agent, "system_prompt", ""),
                tool_definitions=active_tools,
                progressive_skills=getattr(self, "_last_progressive_skills", None),
                episodic_memory=getattr(self, "_last_episodic_memory", None),
                compacted_history=history_msgs,
                tool_results_injected=tool_results,
                completion=full_content,
                reasoning=full_reasoning,
            )
            timing_breakdown = calculate_timing_attribution(
                harness_prep_ms=harness_prep_ms,
                ttft_ms=ttft_ms,
                total_round_trip_ms=turn_dur_ms,
                completion_tokens=token_breakdown.completion,
                inter_step_latency_ms=inter_step_latency_ms,
            )

            turn_span = self.telemetry.record_turn_span(
                agent_id=agent.id,
                session_id=session_id,
                model=model_name,
                provider=provider_name,
                duration_ms=turn_dur_ms,
                ttft_ms=ttft_ms,
                prompt_tokens=token_breakdown.total_prompt_tokens,
                completion_tokens=token_breakdown.completion,
                success=True,
                trace_id=trace_id,
                metadata={
                    "token_breakdown": token_breakdown.to_dict(),
                    "timing_breakdown": timing_breakdown.to_dict(),
                    "active_tool_count": len(active_tools),
                    "tool_schema_chars": tool_schema_chars,
                    "step_context": {
                        "job_id": job_id,
                        "phase_id": phase_id,
                    },
                },
            )
            turn_span_id = turn_span.id

            # Text generation repetition loop check [REQ-RESIL-003]
            if full_content and cycle_detector.record_and_check_text(full_content):
                failed_ev = self._transition_react_state(ReactState.FAILED, turn_idx, **react_ctx)
                if failed_ev:
                    yield failed_ev
                cycle_msg = ChatMessage(
                    role=Role.ASSISTANT,
                    content="Execution terminated: Detected repetitive text generation loop.",
                )
                self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=cycle_msg)
                self._ace_flush_failed_turn(
                    session_id=session_id, agent_id=agent.id, failed=True, error_message=cycle_msg.content
                )
                yield KernelEvent(event_type=KernelEventType.TURN_END, content=cycle_msg.content, is_finished=True)
                return

            # If no tool calls returned, stream is complete
            if not collected_tool_calls:
                user_req_text = user_content or ""
                if not user_req_text and history:
                    for hm in reversed(history):
                        if hm.role == Role.USER and hm.content:
                            user_req_text = hm.content
                            break

                gap = CapabilityDetector.detect(user_prompt=user_req_text, assistant_response=full_content)
                if gap:
                    try:
                        self.capability_gap_repo.create_gap(
                            agent_id=agent.id,
                            user_prompt=gap.user_prompt,
                            missing_capability=gap.missing_capability,
                            context_summary=gap.context_summary,
                            suggested_tool_name=gap.suggested_tool_name,
                            session_id=session_id,
                        )
                    except Exception as e:
                        logger.warning("Failed to record capability gap: %s", e)

                done_ev = self._transition_react_state(ReactState.DONE, turn_idx, **react_ctx)
                if done_ev:
                    yield done_ev
                assistant_msg = ChatMessage(
                    role=Role.ASSISTANT,
                    content=full_content,
                    reasoning=full_reasoning,
                )
                self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=assistant_msg)
                self._ace_flush_failed_turn(session_id=session_id, agent_id=agent.id, failed=False)
                yield KernelEvent(event_type=KernelEventType.TURN_END, content=full_content, is_finished=True)
                return

            # Tool call cycle detection [REQ-RESIL-003]
            if cycle_detector.record_and_check(collected_tool_calls):
                failed_ev = self._transition_react_state(ReactState.FAILED, turn_idx, **react_ctx)
                if failed_ev:
                    yield failed_ev
                cycle_msg = ChatMessage(
                    role=Role.ASSISTANT,
                    content="Execution terminated: Detected repetitive cycle calling tools.",
                )
                self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=cycle_msg)
                self._ace_flush_failed_turn(
                    session_id=session_id, agent_id=agent.id, failed=True, error_message=cycle_msg.content
                )
                yield KernelEvent(event_type=KernelEventType.TURN_END, content=cycle_msg.content, is_finished=True)
                return

            # Save assistant message with tool calls (+ reasoning for Thinking drawer [CARD-415])
            assistant_msg = ChatMessage(
                role=Role.ASSISTANT,
                content=full_content,
                tool_calls=collected_tool_calls,
                reasoning=full_reasoning,
            )
            self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=assistant_msg)
            history.append(assistant_msg)

            calling_ev = self._transition_react_state(ReactState.CALLING_TOOLS, turn_idx, **react_ctx)
            if calling_ev:
                yield calling_ev

            # Execute tool calls
            skills_changed = False
            for tc in collected_tool_calls:
                is_handoff_tool = tc.name == "handoff_to_agent"
                if is_handoff_tool:
                    args = tc.arguments if isinstance(tc.arguments, dict) else {}
                    target_id = args.get("target_agent") or args.get("target_agent_id") or "specialist"
                    directive = args.get("task_intent") or args.get("task_directive") or ""
                    yield KernelEvent(
                        event_type=KernelEventType.HANDOFF_START,
                        handoff={
                            "sender": agent.id,
                            "recipient": target_id,
                            "directive": directive,
                        },
                    )

                yield KernelEvent(
                    event_type=KernelEventType.TOOL_START,
                    tool_call={"id": tc.id, "name": tc.name, "arguments": tc.arguments},
                )

                gated = self._gate_tool_call(
                    tc,
                    session_id,
                    agent,
                    approval_mode=approval_mode,
                    matched_capability_ids=self._matched_capability_ids_for_job(react_ctx.get("job_id")),
                    job_id=react_ctx.get("job_id"),
                )
                if gated is not None:
                    tool_res = gated
                    if tool_res.error and str(tool_res.error).startswith("approval_required:"):
                        approval_id = str(
                            tool_res.output.get("approval_id") if isinstance(tool_res.output, dict) else ""
                        )
                        yield KernelEvent(
                            event_type=KernelEventType.APPROVAL_REQUIRED,
                            content=tool_res.output.get("message", "Approval required")
                            if isinstance(tool_res.output, dict)
                            else "Approval required",
                            approval_id=approval_id or None,
                            tool_call={"id": tc.id, "name": tc.name, "arguments": tc.arguments},
                            tool_result=tool_res,
                        )
                else:
                    tool_res = await self.execute_and_scrub_tool(
                        tc,
                        agent,
                        session_id=session_id,
                        approval_mode=approval_mode,
                        job_id=react_ctx.get("job_id"),
                        active_skills=list(turn_active_skills),
                    )
                    nested = tool_res.output if isinstance(tool_res.output, dict) else None
                    if nested and nested.get("status") == "approval_required" and nested.get("approval_id"):
                        yield KernelEvent(
                            event_type=KernelEventType.APPROVAL_REQUIRED,
                            content=nested.get("message") or "Approval required",
                            approval_id=str(nested.get("approval_id")),
                            tool_call={
                                "id": tc.id,
                                "name": nested.get("tool_name") or tc.name,
                                "arguments": nested.get("arguments") or {},
                            },
                            tool_result=tool_res,
                        )

                if tc.name == "activate_skill" and tool_res.success:
                    args = tc.arguments if isinstance(tc.arguments, dict) else {}
                    new_skills = args.get("skills", [])
                    if isinstance(new_skills, list):
                        for s in new_skills:
                            s_clean = str(s).strip().lower()
                            if s_clean and s_clean not in turn_active_skills:
                                turn_active_skills.add(s_clean)
                                skills_changed = True

                is_hitl = bool(tool_res.error and str(tool_res.error).startswith("approval_required:"))
                tool_status = "hitl_paused" if is_hitl else ("ok" if tool_res.success else "error")
                tool_success = True if is_hitl else tool_res.success

                raw_payload = (
                    dumps_tool_output(tool_res.output)
                    if tool_res.success
                    else (tool_res.error or "")
                )
                payload_bytes = len(raw_payload.encode("utf-8"))
                tc_args = getattr(tc, "arguments", None) or getattr(tc, "args", None) or {}

                self.telemetry.record_tool_span(
                    agent_id=agent.id,
                    session_id=session_id,
                    tool_name=tc.name,
                    duration_ms=tool_res.duration_ms,
                    success=tool_success,
                    status=tool_status,
                    error_message=tool_res.error,
                    trace_id=trace_id,
                    parent_span_id=turn_span_id,
                    metadata={"payload_bytes": payload_bytes, "arguments": tc_args},
                )
                self._ace_note_tool(tc.name, tool_res.success, tool_res.error)

                yield KernelEvent(
                    event_type=KernelEventType.TOOL_END,
                    tool_call={"id": tc.id, "name": tc.name, "arguments": tc.arguments},
                    tool_result=tool_res,
                )

                parked = False
                if tool_res.error and str(tool_res.error).startswith("approval_required:"):
                    parked = True
                nested_out = tool_res.output if isinstance(tool_res.output, dict) else None
                if nested_out and nested_out.get("status") == "approval_required" and nested_out.get("approval_id"):
                    parked = True

                if is_handoff_tool:
                    args = tc.arguments if isinstance(tc.arguments, dict) else {}
                    target_id = args.get("target_agent") or args.get("target_agent_id") or "specialist"
                    output_blob = dumps_tool_output(tool_res.output)
                    if parked:
                        handoff_status = "approval_required"
                    elif (
                        (not tool_res.success)
                        or looks_like_provider_failure(output_blob)
                        or looks_like_provider_failure(str(tool_res.error or ""))
                    ):
                        handoff_status = "failed"
                    else:
                        handoff_status = "completed"
                    yield KernelEvent(
                        event_type=KernelEventType.HANDOFF_COMPLETE,
                        handoff={
                            "recipient": target_id,
                            "status": handoff_status,
                            "error": tool_res.error,
                        },
                    )

                if tool_res.success:
                    tool_content = dumps_tool_output(tool_res.output)
                else:
                    tool_content = f"Tool Error: {tool_res.error}"

                tool_msg = ChatMessage(
                    role=Role.TOOL,
                    content=tool_content,
                    tool_call_id=tc.id,
                    name=tc.name,
                )
                self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=tool_msg)
                history.append(tool_msg)

                if parked:
                    parked_ev = self._transition_react_state(ReactState.PARKED, turn_idx, **react_ctx)
                    if parked_ev:
                        yield parked_ev
                    park_text = ""
                    if isinstance(tool_res.output, dict):
                        park_text = str(tool_res.output.get("message") or "")
                    yield KernelEvent(
                        event_type=KernelEventType.TURN_END,
                        content=park_text,
                        is_finished=True,
                    )
                    return

            if skills_changed:
                active_tools = self._resolve_active_tools(
                    agent,
                    user_content,
                    matched_capability_ids=self._turn_matched_capability_ids,
                    active_skills=list(turn_active_skills) if agent.id == "autoreiv" else None,
                )
            last_turn_end = time.perf_counter()

        # If turn limit reached
        failed_ev = self._transition_react_state(ReactState.FAILED, agent.max_turns, **react_ctx)
        if failed_ev:
            yield failed_ev
        limit_msg = ChatMessage(
            role=Role.ASSISTANT,
            content=f"Execution terminated: Max turn budget of {agent.max_turns} reached.",
        )
        self._ace_flush_failed_turn(
            session_id=session_id, agent_id=agent.id, failed=True, error_message=limit_msg.content
        )
        self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=limit_msg)
        yield KernelEvent(
            event_type=KernelEventType.TURN_END,
            content=limit_msg.content,
            is_finished=True,
        )

    def _nested_park_replay_events(self, history: List[ChatMessage]) -> List[KernelEvent]:
        """Re-emit a nested child park on parent resume [REQ-HITL-038]."""
        last_tool = None
        for msg in reversed(list(history or [])):
            if msg.role == Role.TOOL:
                last_tool = msg
                break
        parked = parse_nested_park_payload(last_tool.content if last_tool else "")
        if not parked:
            return []
        tool_name = parked.get("tool_name") or (last_tool.name if last_tool else "tool") or "tool"
        arguments = parked.get("arguments") if isinstance(parked.get("arguments"), dict) else {}
        message = str(parked.get("message") or "Approval required")
        return [
            KernelEvent(
                event_type=KernelEventType.APPROVAL_REQUIRED,
                content=message,
                approval_id=str(parked.get("approval_id")),
                tool_call={
                    "id": (last_tool.tool_call_id if last_tool else "") or "",
                    "name": tool_name,
                    "arguments": arguments,
                },
            ),
            KernelEvent(
                event_type=KernelEventType.HANDOFF_COMPLETE,
                handoff={
                    "recipient": parked.get("recipient_agent_id") or "specialist",
                    "status": "approval_required",
                },
            ),
            KernelEvent(
                event_type=KernelEventType.TURN_END,
                content=message,
                is_finished=True,
            ),
        ]

    async def run_verified_turn(
        self,
        agent: AgentProfile,
        session_id: str,
        user_content: str,
        verifier_tool_name: Optional[str] = None,
        verifier_args: Optional[Dict[str, Any]] = None,
        max_refinements: int = 3,
    ) -> Dict[str, Any]:
        """Execute a self-verifying turn using ReflexionLoopEngine [REQ-VERIFY-003]."""
        from src.application.kernel.reflexion_engine import ReflexionLoopEngine

        engine = ReflexionLoopEngine(kernel=self, tool_registry=self.tool_registry)
        return await engine.run_reflexion_turn(
            agent=agent,
            session_id=session_id,
            user_content=user_content,
            verifier_tool_name=verifier_tool_name,
            verifier_args=verifier_args,
            max_refinements=max_refinements,
        )
