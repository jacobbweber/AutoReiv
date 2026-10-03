"""
Agent Kernel ReAct Loop & Event Streamer [REQ-KERNEL-003, REQ-KERNEL-006].
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any, AsyncIterator, Collection, Dict, List, Optional, Tuple

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.kernel.context_compactor import (
    ContextCompactor,
    resolve_agent_context_limit,
    resolve_max_tool_chars,
)
from src.application.kernel.cycle_detector import CycleDetector
from src.application.kernel.empty_reply import (
    EMPTY_REPLY_MESSAGE,
    chat_note,
    is_empty_reply,
    model_history_rows,
)
from src.application.kernel.hitl_engine import HITLApprovalEngine
from src.application.kernel.json_safe import dumps_jsonable, dumps_tool_output, to_jsonable
from src.application.kernel.repeat_guard import (
    LOOP_FALLBACK_MESSAGE,
    LOOP_FINAL_INSTRUCTION,
    TEXT_LOOP_MESSAGE,
    RepeatGuard,
    rejected_tool_names,
)
from src.application.kernel.reply_limits import (
    ReplyLimitStop,
    reply_token_limit,
    resolve_reply_limits,
    resolve_wiki_lookups,
    time_limit_message,
    token_limit_message,
)
from src.application.kernel.reply_rules import (  # CARD-599/600
    CLARIFICATION_SKIPPED_RESULT,
    MEMORIZE_TOOL,
    REPLY_RULES_BLOCK,
    clarification_question,
    clarification_reply,
    describe_tool_run,
    drop_false_not_done,
    failed_tool_note,
    memory_not_done_lines,
    memory_retry_prompt,
    needs_parts_check,
    parse_parts_check,
    parts_check_prompt,
    settle_memory_retry,
    track_failure,
)
from src.application.kernel.telemetry_attribution import (
    calculate_timing_attribution,
    calculate_token_attribution,
)
from src.application.kernel.tool_registry import ScopedToolRegistry, tool_not_offered_error
from src.application.kernel.turn_limit import TURN_LIMIT_INSTRUCTION, TURN_LIMIT_REASON, turn_limit_reply
from src.application.kernel.wiki_budget import WikiLookupBudget
from src.application.orchestration.capability_detector import CapabilityDetector
from src.application.orchestration.handoff_engine import looks_like_provider_failure
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.errors import EmptyModelReplyError, RateLimitError
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

# CARD-576: nested run_turn (routines, plans, resumes) uses the agent's own context window, like stream_turn.
# The old 32k cap (CARD-001 stall at 131072) made Ollama reload the model at another size on every nested run;
# Nimo now serves qwen3.8 at its full 262144 (OLLAMA_CONTEXT_LENGTH). The reply stays capped by max_tokens.

# CARD-578 (ADR-0064): no per-turn tool cap, ranking or pinning. Every allowed tool is sent on every model call.

# CARD-562: the Active Selected Project prompt names only tools this agent may call (it once told Developer to use cli_exec).
_PROJECT_GUIDANCE_TOOLS: tuple[str, ...] = (
    "read_project_file",
    "search_project",
    "list_project_dir",
    "write_project_file",
    "patch_project_file",
)


def project_tool_guidance(allowed_tools: "set[str] | frozenset[str]") -> str:
    """Project tool guidance built only from the agent's resolved allowed tools [CARD-562]."""
    names = [t for t in _PROJECT_GUIDANCE_TOOLS if t in allowed_tools]
    parts: list[str] = []
    if names:
        parts.append(f"Use {', '.join(names)} to work with files inside this project.")
    if "run_project_checks" in allowed_tools:
        parts.append("Run the project's checks (AGENTS.md ## Checks) with run_project_checks.")
    elif "cli_exec" in allowed_tools:
        parts.append("Use cli_exec to run tests and scripts within this directory.")
    return " ".join(parts)


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
        self.ace_skill_id: Optional[str] = None
        self._ace_tool_errors: List[Dict[str, Any]] = []
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
        offered: Optional[Collection[str]] = None,
    ) -> ToolResult:
        tool_res = await self.tool_registry.execute(
            tool_call,
            agent,
            session_id=session_id,
            approval_mode=approval_mode,
            job_id=job_id,
            state_store=self.state_store,
            offered=offered,
        )
        scrubber = self._get_scrubber()
        if tool_res.output is not None:
            tool_res.output = scrubber.scrub_object(tool_res.output)
            # Harden ALL tool outputs (education mastery next_due, session timestamps, …)
            # so accidental raw json.dumps sinks cannot regress Tutor chat (CARD-438).
            tool_res.output = to_jsonable(tool_res.output)
        if tool_res.error is not None:
            tool_res.error = scrubber.scrub(str(tool_res.error))
        return tool_res

    def _resolve_ace_skill_id(self) -> Optional[str]:
        explicit = (self.ace_skill_id or "").strip()
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
        from src.application.orchestration.ace_online import is_ace_lesson_error

        if not is_ace_lesson_error(error):
            return  # approval parks and refusals the tool already explained (CARD-610) are not lessons
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

            skill_id = self._resolve_ace_skill_id()
            data_dir = self._resolve_ace_data_dir()
            if not skill_id or not data_dir:
                return
            record_failed_turn_delta(
                self.state_store,
                skill_id=skill_id,
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

    def _matched_capability_ids_for_job(
        self, job_id: Optional[str], phase_id: Optional[str] = None, agent: Any = None
    ) -> Optional[list]:
        """Resolve locked matched IDs from durable checkpoint when job/phase-bound [CARD-221/224, CARD-362].

        CARD-553: the subset was matched for the agent the job was minted for, so it narrows only that agent. Another
        agent in the job (an Execute phase assigned to Developer, or a handoff target) gets None here: its own
        allowed set (resolve_allowed_tools), narrowed only by per-turn selection; the gate still enforces that set.
        """
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
        agent_id = str(getattr(agent, "id", "") or "").strip() if agent is not None else ""
        if agent_id:
            job_getter = getattr(self.state_store, "get_job", None)
            try:
                job = job_getter(jid) if callable(job_getter) else None
            except Exception:
                job = None
            owner = str(getattr(job, "agent_id", "") or "").strip() if job is not None else ""
            if owner and owner != agent_id:
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

    def _is_planning_phase(self, phase_id: Optional[str]) -> bool:
        """True when ``phase_id`` is a Formulate (planning) phase [CARD-554]."""
        pid = str(phase_id or "").strip()
        getter = getattr(self.state_store, "get_phase", None)
        if not pid or not callable(getter):
            return False
        try:
            from src.application.orchestration.phase_roles import is_planning_phase

            return is_planning_phase(getter(pid))
        except Exception:
            return False

    def _gate_tool_call(
        self,
        tc: ToolCall,
        session_id: str,
        agent: AgentProfile,
        approval_mode: str = "ask",
        routine_id: Optional[str] = None,
        matched_capability_ids: Optional[list] = None,
        job_id: Optional[str] = None,
        planning_phase: bool = False,
        offered: Optional[Collection[str]] = None,
    ) -> Optional[ToolResult]:
        """
        Tool policy gate [CARD-221]: ALLOW / REQUIRE_CONFIRM / BLOCK before executor.
        CARD-578: a tool that was not in the tools sent on this call is refused before any policy or approval.
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
        if offered is not None and tc.name not in offered:
            return ToolResult(
                call_id=tc.id,
                tool_name=tc.name,
                output=None,
                success=False,
                error=tool_not_offered_error(tc.name, offered),
            )
        registry_names = set()
        try:
            registry_names = {d.name for d in self.tool_registry.list_tools()}
        except Exception:
            registry_names = set()
        risk_of = getattr(self.tool_registry, "get_tool_risk", None)
        decision = gate.evaluate(
            tc,
            agent,
            matched_capability_ids=matched_capability_ids,
            registry_tool_names=registry_names or None,
            tool_risk=risk_of(tc.name) if callable(risk_of) else None,
            planning_phase=planning_phase,
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
                from src.application.agent_skills.allowed_tools import resolve_allowed_tools

                allowed_tools: set[str] = set(resolve_allowed_tools(agent).names)
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
                        tool_guidance = project_tool_guidance(allowed_tools)
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

        # CARD-539 D5: the domain line is generated from ticked skills; no hand-written capability block.
        if getattr(agent, "id", None) != "direct":
            from src.application.agent_skills.allowed_tools import domain_line

            base_prompt = f"{base_prompt}\n\n## Your domain\n{domain_line(agent)}"
            base_prompt = f"{base_prompt}\n\n{REPLY_RULES_BLOCK}"  # CARD-599/600

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

    def _resolve_active_tools(
        self,
        agent: AgentProfile,
        user_content: Optional[str] = None,
        matched_capability_ids: Optional[list] = None,
        planning_phase: Optional[bool] = None,
    ) -> List[Any]:
        """
        This call's tools: every tool the agent is allowed (ticked skills + base tools), all at once
        (CARD-578, ADR-0064). No cap, ranking or keyword matching. Only policy narrows: a Formulate
        phase does not get work tools (CARD-554), and a job locked to matched capabilities mounts
        only those (plus the required platform tools), the same set ToolPolicyGate enforces.
        """
        if getattr(agent, "id", None) == "direct":
            return []

        from src.application.agent_skills.allowed_tools import resolve_allowed_tools, ticked_skills
        from src.application.agent_skills.schema import REQUIRED_PLATFORM_TOOLS

        allowed = resolve_allowed_tools(agent)
        ticks = set(ticked_skills(agent))
        ids = matched_capability_ids
        if ids is None:
            ids = getattr(self, "_turn_matched_capability_ids", None)
        phase_skills = {
            str(cid).strip()[len("skill.") :]
            for cid in ids or []
            if str(cid).strip().startswith("skill.") and str(cid).strip()[len("skill.") :] in ticks
        }

        tools = list(self.tool_registry.get_tools_for_agent(agent))
        if planning_phase is None:
            planning_phase = bool(getattr(self, "_turn_planning_phase", False))
        if planning_phase:  # Formulate plans only: handoff and work tools are not mounted [CARD-554]
            from src.application.orchestration.phase_roles import planning_phase_block_reason

            risk_of = getattr(self.tool_registry, "get_tool_risk", None)
            tools = [
                t for t in tools
                if not planning_phase_block_reason(t.name, risk_of(t.name) if callable(risk_of) else None)
            ]
        if phase_skills:  # a phase bound to ticked skills mounts only their tools [REQ-CAP-PAGE-004]
            tools = [
                t for t in tools if phase_skills & set(allowed.skills_for(t.name)) or t.name in REQUIRED_PLATFORM_TOOLS
            ]
        try:
            from src.application.safety.tool_policy_gate import (
                EDUCATION_FORBIDDEN_WIKI_TOOLS,
                _capability_tool_names,
            )

            subset = _capability_tool_names(ids)
            if subset is not None:
                tools = [t for t in tools if t.name in subset or t.name in REQUIRED_PLATFORM_TOOLS]
            else:
                id_list = [str(x) for x in (ids or [])]
                if any(s.endswith("education-priming") or s.endswith("education-dual-coding") for s in id_list):
                    tools = [t for t in tools if getattr(t, "name", "") not in EDUCATION_FORBIDDEN_WIKI_TOOLS]
        except Exception:
            pass
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
        self._turn_matched_capability_ids = self._matched_capability_ids_for_job(job_id=job_id, phase_id=phase_id, agent=agent)
        self._turn_planning_phase = self._is_planning_phase(phase_id)
        if resume:
            user_content = None
        if user_content and save_to_history:
            user_msg = ChatMessage(role=Role.USER, content=user_content)
            self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=user_msg)

        # CARD-475 [REQ-475-006]: empty assistant rows from failed streams are not replayed.
        history = model_history_rows(self.state_store.get_messages(session_id=session_id))
        if user_content and not save_to_history:
            history.append(ChatMessage(role=Role.USER, content=user_content))

        system_msg = self._build_effective_system_message(agent, user_content)
        active_tools = self._resolve_active_tools(
            agent,
            user_content,
            matched_capability_ids=self._turn_matched_capability_ids,
        )
        rejected_now = rejected_tool_names(history)  # CARD-613: not offered again after the operator rejected it
        active_tools = [t for t in active_tools if t.name not in rejected_now]
        offered_names = {t.name for t in active_tools}  # CARD-578: only these may run on this call
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
        repeat_guard = RepeatGuard(rejected_tool_names(history))  # CARD-551/460; CARD-613
        wiki_budget = WikiLookupBudget(resolve_wiki_lookups(self.state_store))  # CARD-605: Settings > Reply limits
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
        last_failure: Optional[Tuple[str, str]] = None  # CARD-600: (tool, error) of the turn's last failed call

        for turn_idx in range(agent.max_turns):
            repeat_guard.next_step()
            turn_start = time.perf_counter()
            inter_step_latency_ms = ((turn_start - last_turn_end) * 1000) if last_turn_end is not None else None
            self._transition_react_state(ReactState.THINKING, turn_idx, **react_ctx)
            context_limit = self._resolve_context_limit(agent, model_name)
            nested_ctx = context_limit  # CARD-576: no smaller override
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
                tools=wiki_budget.offer(active_tools) or None,  # CARD-605: no wiki look-ups once used up
                num_ctx=nested_ctx,
                # CARD-586: child turns get the same generous reply cap as chat replies (was a fixed 8192)
                max_tokens=reply_token_limit(resolve_reply_limits(self.state_store)[0], nested_ctx),
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
                    content=TEXT_LOOP_MESSAGE,  # CARD-460: plain words
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
                if is_empty_reply(assistant_msg.content, None):
                    # CARD-475 [REQ-475-004]: an empty reply is an error, never a saved empty row.
                    self._transition_react_state(ReactState.FAILED, turn_idx, **react_ctx)
                    self._ace_flush_failed_turn(
                        session_id=session_id, agent_id=agent.id, failed=True, error_message=EMPTY_REPLY_MESSAGE
                    )
                    raise EmptyModelReplyError(EMPTY_REPLY_MESSAGE, provider_id=provider_name)
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
                note = failed_tool_note(assistant_msg.content or "", last_failure)  # CARD-600
                if note:
                    assistant_msg.content = f"{(assistant_msg.content or '').rstrip()}\n\n{note}"
                if save_to_history:
                    self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=assistant_msg)
                self._ace_flush_failed_turn(session_id=session_id, agent_id=agent.id, failed=False)
                return assistant_msg

            # Tool call cycle detection [REQ-RESIL-003]
            if cycle_detector.record_and_check(assistant_msg.tool_calls):
                # CARD-551: answer from the tool results already in hand instead of "Execution terminated".
                final_text = await self._final_answer_without_tools(
                    model_name, system_msg, history, nested_ctx, LOOP_FINAL_INSTRUCTION
                )
                self._transition_react_state(ReactState.DONE if final_text else ReactState.FAILED, turn_idx, **react_ctx)
                cycle_text = final_text or LOOP_FALLBACK_MESSAGE
                note = failed_tool_note(cycle_text, last_failure)  # CARD-600
                cycle_msg = ChatMessage(role=Role.ASSISTANT, content=f"{cycle_text}\n\n{note}" if note else cycle_text)
                if save_to_history:
                    self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=cycle_msg)
                self._ace_flush_failed_turn(
                    session_id=session_id,
                    agent_id=agent.id,
                    failed=not final_text,
                    error_message=None if final_text else "repeat_loop",
                )
                return cycle_msg

            self._transition_react_state(ReactState.CALLING_TOOLS, turn_idx, **react_ctx)

            # Handle tool calls
            if save_to_history:
                self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=assistant_msg)
            history.append(assistant_msg)

            clarify_q: Optional[str] = None  # CARD-600: ask_clarification ends the turn
            for tc in assistant_msg.tool_calls:
                if clarify_q is not None:
                    skipped = ChatMessage(role=Role.TOOL, content=CLARIFICATION_SKIPPED_RESULT, name=tc.name, tool_call_id=tc.id)
                    if save_to_history:
                        self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=skipped)
                    history.append(skipped)
                    continue
                gated = wiki_budget.check(tc) or repeat_guard.reuse(tc) or self._gate_tool_call(
                    tc,
                    session_id,
                    agent,
                    approval_mode=approval_mode,
                    routine_id=routine_id,
                    matched_capability_ids=self._matched_capability_ids_for_job(react_ctx.get("job_id"), agent=agent),
                    job_id=react_ctx.get("job_id"),
                    planning_phase=self._is_planning_phase(react_ctx.get("phase_id")),
                    offered=offered_names,
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
                        offered=offered_names,
                    )


                repeat_guard.record(tc, tool_res)
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
                last_failure = track_failure(last_failure, tc.name, tool_res.success, tool_res.error, tool_res.output)
                clarify_q = clarification_question(tc.name, tool_res.success, tool_res.output, tc.arguments)

            if clarify_q is not None:
                # CARD-600: show the question and stop; the next user message answers it.
                self._transition_react_state(ReactState.DONE, turn_idx, **react_ctx)
                question_msg = ChatMessage(
                    role=Role.ASSISTANT, content=clarification_reply(clarify_q, assistant_msg.content or "") or clarify_q
                )
                if save_to_history:
                    self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=question_msg)
                self._ace_flush_failed_turn(session_id=session_id, agent_id=agent.id, failed=False)
                return question_msg

            last_turn_end = time.perf_counter()

        # CARD-461: one last no-tools call summarizes what was done and what is left.
        summary = await self._final_answer_without_tools(
            model_name, system_msg, history, self._resolve_context_limit(agent, model_name), TURN_LIMIT_INSTRUCTION
        )
        self._transition_react_state(ReactState.FAILED, agent.max_turns, **react_ctx)
        limit_msg = ChatMessage(role=Role.ASSISTANT, content=turn_limit_reply(summary, agent.max_turns))
        self._ace_flush_failed_turn(
            session_id=session_id, agent_id=agent.id, failed=True, error_message=TURN_LIMIT_REASON
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
        parts_request: Optional[str] = None,
    ) -> AsyncIterator[KernelEvent]:
        """
        Execute an asynchronous streaming agent turn with live token and tool lifecycle events.

        When resume=True or user_content is empty, continue from persisted history
        without appending a USER message [REQ-HITL-034].
        parts_request: the operator's typed message; when given, a multi-part request gets the CARD-599
        skipped-parts check after the final reply (Chat short turns only).
        """
        self._ace_tool_errors = []
        self._turn_matched_capability_ids = self._matched_capability_ids_for_job(job_id=job_id, phase_id=phase_id, agent=agent)
        self._turn_planning_phase = self._is_planning_phase(phase_id)
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
        # CARD-475 [REQ-475-006]: empty assistant rows from failed streams are not replayed.
        history = model_history_rows(self.state_store.get_messages(session_id=session_id))
        notices_sent: set = set()
        if resume:
            replay = self._nested_park_replay_events(history)
            if replay:
                parked_ev = self._transition_react_state(ReactState.PARKED, 0, **react_ctx)
                if parked_ev:
                    yield parked_ev
                for ev in replay:
                    yield ev
                return
        system_msg = self._build_effective_system_message(agent, user_content)
        active_tools = self._resolve_active_tools(
            agent,
            user_content,
            matched_capability_ids=self._turn_matched_capability_ids,
        )
        rejected_now = rejected_tool_names(history)  # CARD-613: not offered again after the operator rejected it
        active_tools = [t for t in active_tools if t.name not in rejected_now]
        offered_names = {t.name for t in active_tools}  # CARD-578: only these may run on this call
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
        repeat_guard = RepeatGuard(rejected_tool_names(history))  # CARD-551/460; CARD-613
        wiki_budget = WikiLookupBudget(resolve_wiki_lookups(self.state_store))  # CARD-605: Settings > Reply limits

        trace_id = session_id or str(uuid.uuid4())
        provider_name = getattr(agent, "provider", None) or (agent.model.split("/")[0] if "/" in agent.model else None)
        turn_span_id = None
        self._ensure_agent_provider_adapter(agent)
        last_turn_end = None
        last_failure: Optional[Tuple[str, str]] = None  # CARD-600: (tool, error) of the turn's last failed call
        tools_ran: List[str] = []  # CARD-599: what ran this turn, for the skipped-parts check
        pending_not_done: Optional[str] = None  # CARD-604: the check's lines while the memory retry step runs
        tools_before_retry = 0

        for turn_idx in range(agent.max_turns):
            repeat_guard.next_step()
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
            # CARD-567: every streaming call is bounded (tokens and wall-clock seconds).
            reply_max_tokens, reply_max_seconds = resolve_reply_limits(self.state_store)
            reply_max_tokens = reply_token_limit(reply_max_tokens, context_limit)
            req = CompletionRequest(
                model=model_name,
                messages=compacted_messages,
                tools=wiki_budget.offer(active_tools) or None,  # CARD-605: no wiki look-ups once used up
                num_ctx=context_limit,
                max_tokens=reply_max_tokens,
                stream=True,
            )
            prep_end = time.perf_counter()
            harness_prep_ms = (prep_end - turn_start) * 1000

            accumulated_content = []
            accumulated_reasoning = []
            collected_tool_calls: List[ToolCall] = []
            finish_reason: Optional[str] = None

            # Close the parent LLM HTTP stream BEFORE tools (child handoff complete()).
            stream_gen = None
            try:
                stream_gen = self.gateway.stream(req, demux_reasoning=True)
                # CARD-585: the reply time limit starts at the model's first token, so time spent waiting for a
                # generation slot or for the provider to start (queue, prefill, model load) does not count.
                # Before the first token the provider's read timeout bounds silence.
                deadline: Optional[float] = None
                while True:
                    try:
                        if deadline is None:
                            chunk = await stream_gen.__anext__()
                        else:
                            chunk = await asyncio.wait_for(
                                stream_gen.__anext__(), timeout=max(0.0, deadline - time.monotonic())
                            )
                    except StopAsyncIteration:
                        break
                    except asyncio.TimeoutError:
                        raise ReplyLimitStop(time_limit_message(reply_max_seconds)) from None
                    if chunk.notice:
                        # CARD-475: e.g. an image dropped for a text-only model; once per turn.
                        note_text = str(chunk.notice.get("message") or "")
                        if note_text and note_text not in notices_sent:
                            notices_sent.add(note_text)
                            try:  # CARD-482: keep the notice in the thread as a chat note (not model context)
                                self.state_store.save_message(
                                    session_id=session_id, agent_id=agent.id, message=chat_note(chunk.notice, note_text)
                                )
                            except Exception as exc:  # noqa: BLE001 - a lost note must not break the reply
                                logger.warning("chat note not saved: %s", exc)
                            yield KernelEvent(
                                event_type=KernelEventType.NOTICE, content=note_text, notice=dict(chunk.notice)
                            )
                        continue
                    if first_token_time is None and (chunk.content or chunk.reasoning_content or chunk.tool_calls):
                        first_token_time = time.perf_counter()
                        ttft_ms = (first_token_time - turn_start) * 1000
                        deadline = time.monotonic() + reply_max_seconds

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
                    if chunk.finish_reason:
                        finish_reason = chunk.finish_reason
                    if chunk.is_finished:
                        break
                if finish_reason == "length" and not collected_tool_calls:
                    answered = bool("".join(accumulated_content).strip())
                    note = token_limit_message(reply_max_tokens, answered)
                    if not answered:
                        raise ReplyLimitStop(note)
                    accumulated_content.append("\n\n" + note)
                    yield KernelEvent(event_type=KernelEventType.TOKEN, content="\n\n" + note)
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
                if isinstance(e, ReplyLimitStop):
                    self.state_store.save_message(
                        session_id=session_id,
                        agent_id=agent.id,
                        message=ChatMessage(role=Role.ASSISTANT, content=e.message),
                    )
                    yield KernelEvent(event_type=KernelEventType.TOKEN, content="\n\n" + e.message)
                    yield KernelEvent(event_type=KernelEventType.ERROR, content=e.message, is_finished=True)
                    return
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
                    content=TEXT_LOOP_MESSAGE,  # CARD-460: plain words
                )
                self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=cycle_msg)
                self._ace_flush_failed_turn(
                    session_id=session_id, agent_id=agent.id, failed=True, error_message=cycle_msg.content
                )
                yield KernelEvent(event_type=KernelEventType.TURN_END, content=cycle_msg.content, is_finished=True)
                return

            # If no tool calls returned, stream is complete
            if not collected_tool_calls:
                if is_empty_reply(full_content, None):
                    # CARD-475 [REQ-475-004]: an empty reply is an error, never a saved empty row.
                    failed_ev = self._transition_react_state(ReactState.FAILED, turn_idx, **react_ctx)
                    if failed_ev:
                        yield failed_ev
                    self._ace_flush_failed_turn(
                        session_id=session_id, agent_id=agent.id, failed=True, error_message=EMPTY_REPLY_MESSAGE
                    )
                    yield KernelEvent(event_type=KernelEventType.ERROR, content=EMPTY_REPLY_MESSAGE, is_finished=True)
                    return
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

                skipped = ""
                if pending_not_done is not None:
                    skipped = settle_memory_retry(pending_not_done, tools_ran[tools_before_retry:])  # CARD-604
                elif parts_request and not resume:
                    skipped = await self._skipped_parts_note(
                        model_name, parts_request, tools_ran, full_content, context_limit
                    )
                    memory_lines = memory_not_done_lines(skipped)
                    if memory_lines and MEMORIZE_TOOL in offered_names and turn_idx + 2 < agent.max_turns:
                        # CARD-604: a memory ask was skipped; one more step to save it before saying "Not done".
                        pending_not_done, tools_before_retry = skipped, len(tools_ran)
                        first_msg = ChatMessage(role=Role.ASSISTANT, content=full_content, reasoning=full_reasoning)
                        self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=first_msg)
                        history.append(first_msg)
                        history.append(ChatMessage(role=Role.USER, content=memory_retry_prompt(memory_lines)))
                        yield KernelEvent(event_type=KernelEventType.TOKEN, content="\n\n")
                        continue
                done_ev = self._transition_react_state(ReactState.DONE, turn_idx, **react_ctx)
                if done_ev:
                    yield done_ev
                note = "\n".join(x for x in (skipped, failed_tool_note(full_content, last_failure)) if x)
                if note:  # CARD-599 skipped parts, CARD-600 hidden failed tool
                    full_content = f"{full_content.rstrip()}\n\n{note}"
                    yield KernelEvent(event_type=KernelEventType.TOKEN, content=f"\n\n{note}")
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
                # CARD-551: answer from the tool results already in hand instead of "Execution terminated".
                final_text = await self._final_answer_without_tools(
                    model_name, system_msg, history, context_limit, LOOP_FINAL_INSTRUCTION
                )
                end_ev = self._transition_react_state(
                    ReactState.DONE if final_text else ReactState.FAILED, turn_idx, **react_ctx
                )
                if end_ev:
                    yield end_ev
                cycle_text = final_text or LOOP_FALLBACK_MESSAGE
                note = failed_tool_note(cycle_text, last_failure)  # CARD-600
                cycle_msg = ChatMessage(role=Role.ASSISTANT, content=f"{cycle_text}\n\n{note}" if note else cycle_text)
                self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=cycle_msg)
                self._ace_flush_failed_turn(
                    session_id=session_id,
                    agent_id=agent.id,
                    failed=not final_text,
                    error_message=None if final_text else "repeat_loop",
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
            clarify_q: Optional[str] = None  # CARD-600: ask_clarification ends the turn
            for tc in collected_tool_calls:
                if clarify_q is not None:
                    skipped = ChatMessage(role=Role.TOOL, content=CLARIFICATION_SKIPPED_RESULT, tool_call_id=tc.id, name=tc.name)
                    self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=skipped)
                    history.append(skipped)
                    continue
                is_handoff_tool = tc.name in ("handoff_to_agent", "hand_off_card")
                if is_handoff_tool:
                    args = tc.arguments if isinstance(tc.arguments, dict) else {}
                    card_handoff = tc.name == "hand_off_card"  # CARD-563
                    target_id = "developer" if card_handoff else (
                        args.get("target_agent") or args.get("target_agent_id") or "specialist"
                    )
                    directive = (
                        f"Work card {args.get('card_id', '')} to In Review in the active project."
                        if card_handoff
                        else args.get("task_intent") or args.get("task_directive") or ""
                    )
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

                gated = wiki_budget.check(tc) or repeat_guard.reuse(tc) or self._gate_tool_call(
                    tc,
                    session_id,
                    agent,
                    approval_mode=approval_mode,
                    matched_capability_ids=self._matched_capability_ids_for_job(react_ctx.get("job_id"), agent=agent),
                    job_id=react_ctx.get("job_id"),
                    planning_phase=self._is_planning_phase(react_ctx.get("phase_id")),
                    offered=offered_names,
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
                        offered=offered_names,
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


                repeat_guard.record(tc, tool_res)
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
                last_failure = track_failure(last_failure, tc.name, tool_res.success, tool_res.error, tool_res.output)
                tools_ran.append(describe_tool_run(tc.name, tc.arguments, not tool_res.success, tool_res.output))
                clarify_q = clarification_question(tc.name, tool_res.success, tool_res.output, tc.arguments)

            if clarify_q is not None:
                # CARD-600: show the question and stop; the next user message answers it.
                done_ev = self._transition_react_state(ReactState.DONE, turn_idx, **react_ctx)
                if done_ev:
                    yield done_ev
                question = clarification_reply(clarify_q, full_content)
                if question:
                    self.state_store.save_message(
                        session_id=session_id, agent_id=agent.id, message=ChatMessage(role=Role.ASSISTANT, content=question)
                    )
                    yield KernelEvent(
                        event_type=KernelEventType.TOKEN, content=f"\n\n{question}" if full_content.strip() else question
                    )
                self._ace_flush_failed_turn(session_id=session_id, agent_id=agent.id, failed=False)
                yield KernelEvent(
                    event_type=KernelEventType.TURN_END,
                    content=question or full_content,
                    is_finished=True,
                    react={"clarification": True},  # CARD-613: a job step that asks is not done
                )
                return

            last_turn_end = time.perf_counter()

        # If turn limit reached - CARD-461: one last no-tools call summarizes what was done and what is left.
        summary = await self._final_answer_without_tools(
            model_name, system_msg, history, self._resolve_context_limit(agent, model_name), TURN_LIMIT_INSTRUCTION
        )
        failed_ev = self._transition_react_state(ReactState.FAILED, agent.max_turns, **react_ctx)
        if failed_ev:
            yield failed_ev
        limit_msg = ChatMessage(role=Role.ASSISTANT, content=turn_limit_reply(summary, agent.max_turns))
        self._ace_flush_failed_turn(
            session_id=session_id, agent_id=agent.id, failed=True, error_message=TURN_LIMIT_REASON
        )
        self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=limit_msg)
        yield KernelEvent(event_type=KernelEventType.TOKEN, content=limit_msg.content)
        yield KernelEvent(
            event_type=KernelEventType.TURN_END,
            content=limit_msg.content,
            is_finished=True,
        )

    async def _skipped_parts_note(
        self, model_name: str, user_text: str, tools_ran: List[str], reply: str, context_limit: int
    ) -> str:
        """CARD-599 (b): a short no-tools check on the same model; "Not done: ..." lines for skipped parts, else ""."""
        if not needs_parts_check(user_text, reply):
            return ""
        try:
            req = CompletionRequest(
                model=model_name,
                messages=[ChatMessage(role=Role.USER, content=parts_check_prompt(user_text, tools_ran, reply))],
                tools=None,
                num_ctx=context_limit,
                max_tokens=reply_token_limit(resolve_reply_limits(self.state_store)[0], context_limit),  # thinking counts
            )
            resp = await self.gateway.complete(req)
            msg = getattr(resp, "message", None)
            return drop_false_not_done(parse_parts_check(getattr(msg, "content", None) or ""), tools_ran)  # CARD-604
        except Exception as exc:  # noqa: BLE001 - the reply stands without the check
            logger.warning("skipped-parts check failed: %s", exc)
            return ""

    async def _final_answer_without_tools(
        self,
        model_name: str,
        system_msg: ChatMessage,
        history: List[ChatMessage],
        context_limit: int,
        instruction: str,
    ) -> str:
        """CARD-551/461: one last model call with no tools; "" when it fails, is empty or only tries to call tools."""
        try:
            messages = ContextCompactor.compact(
                [system_msg] + list(history),
                model_name=model_name,
                max_tokens=max(1000, int(context_limit * 0.75)),
                keep_last_n_turns=4,
                max_tool_chars=resolve_max_tool_chars(context_limit),
                preserve_root_intent=True,
            )
            messages = list(messages) + [ChatMessage(role=Role.USER, content=instruction)]
            req = CompletionRequest(
                model=model_name,
                messages=messages,
                tools=None,
                num_ctx=context_limit,
                max_tokens=reply_token_limit(resolve_reply_limits(self.state_store)[0], context_limit),
            )
            resp = await self.gateway.complete(req)
            msg = getattr(resp, "message", None)
            text = (getattr(msg, "content", None) or getattr(resp, "text", None) or "").strip()
            return "" if is_empty_reply(text, None) else text
        except Exception as exc:  # the fallback message covers it
            logger.warning("final no-tools answer failed: %s", exc)
            return ""

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
