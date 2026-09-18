"""Factory dispatch and agent pack inspection tools [CARD-355, REQ-FACT-061, REQ-FACT-062].

Provides atomic callables for Forge (and supervisor agents) to:
1. inspect_agent_pack: Inspect a target agent's identity, active tools, skills, and pack path.
2. launch_factory_training: Dispatch a structured capability job to the 8-phase Agent Training Factory.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.domain.orchestration.factory_packets import FactoryJob, FactoryPacket, WorkPacket
from src.infrastructure.memory.repositories.factory_packets import FactoryPacketRepository

logger = logging.getLogger(__name__)


class FactoryDispatchTools:
    """Tools enabling conversational intake and dispatch to Agent Training Factory."""

    def __init__(
        self,
        agent_registry: Any = None,
        store: Any = None,
        tool_registry: Optional[ScopedToolRegistry] = None,
        data_dir: Optional[Union[str, Path]] = None,
        orchestrator: Any = None,
    ) -> None:
        self.agent_registry = agent_registry
        self.store = store
        self.tool_registry = tool_registry
        self.data_dir = Path(data_dir) if data_dir is not None else None
        self.orchestrator = orchestrator

    def _resolved_data_dir(self) -> Path:
        if self.data_dir is not None:
            return Path(self.data_dir)
        try:
            from src.infrastructure.data.resolver import DataDirResolver

            return DataDirResolver().resolve().root
        except Exception:
            return Path.cwd() / "scratch"

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        registry.register_tool(
            name="inspect_agent_pack",
            description=(
                "Inspect an agent's current identity, tools, skills, and pack storage without modifying it. "
                "Use this to understand what the target agent already does before designing new capabilities."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Agent id (slug) to inspect (e.g. autoreiv, developer, tutor, direct).",
                    },
                },
                "required": ["agent_id"],
            },
            handler=self.inspect_agent_pack,
        )

        registry.register_tool(
            name="launch_factory_training",
            description=(
                "Dispatch a verified capability manufacturing job to the 8-phase Agent Training Factory. "
                "Formulates the requirement and triggers the deterministic factory pipeline. "
                "Does NOT author Python directly into user packs. Always ask human confirmation before calling."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "target_agent_id": {
                        "type": "string",
                        "description": "ID of the agent that will receive the new capability.",
                    },
                    "seed_intent": {
                        "type": "string",
                        "description": "High-level description of what capability or task the agent must learn.",
                    },
                    "objectives": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "1 to 3 verifiable, concrete starter objectives.",
                    },
                    "deliverable_type": {
                        "type": "string",
                        "enum": ["auto", "tool", "mcp", "skill"],
                        "description": "Packaging architecture: auto (recommended), tool (native Python), mcp (server), or skill (runbook).",
                    },
                    "reference_docs": {
                        "type": "string",
                        "description": "Pasted API documentation, CLI syntax manuals, or error logs to ground code generation.",
                    },
                    "target_host": {
                        "type": "string",
                        "description": "Target execution host ('local' or remote IP/hostname). Default is 'local'.",
                    },
                    "target_directory": {
                        "type": "string",
                        "description": "Optional host directory path for project grounding.",
                    },
                    "risk_policy": {
                        "type": "string",
                        "enum": ["ask", "deny", "allow"],
                        "description": "Safety deployment policy. Default is 'ask' (requires human approval on promote).",
                    },
                },
                "required": ["target_agent_id"],
            },
            handler=self.launch_factory_training,
        )

    async def inspect_agent_pack(self, agent_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Inspect target agent capabilities, tool names, and skill runbooks [REQ-FACT-062]."""
        clean_id = str(agent_id or "").strip()
        if not clean_id:
            return {"success": False, "error": "agent_id is required."}

        profile = None
        if self.agent_registry is not None and hasattr(self.agent_registry, "get_profile"):
            profile = self.agent_registry.get_profile(clean_id)
        if profile is None and self.agent_registry is not None and hasattr(self.agent_registry, "get_agent"):
            profile = self.agent_registry.get_agent(clean_id)

        if profile is None:
            # Fallback: inspect user data packs directory directly
            packs_dir = self._resolved_data_dir() / "packs" / clean_id
            manifest_file = packs_dir / "pack.json"
            if manifest_file.is_file():
                try:
                    import json

                    data = json.loads(manifest_file.read_text(encoding="utf-8"))
                    tools: list[str] = []
                    skills: list[str] = []
                    for s in data.get("skills", []):
                        if isinstance(s, dict):
                            skills.append(s.get("id", ""))
                            tools.extend(s.get("tools", []))
                        elif isinstance(s, str):
                            skills.append(s)
                    return {
                        "success": True,
                        "agent_id": clean_id,
                        "name": data.get("name", clean_id),
                        "description": data.get("description", ""),
                        "avatar_icon": data.get("avatar_icon", "bot"),
                        "tools": sorted(set(filter(None, tools))),
                        "skills": sorted(set(filter(None, skills))),
                        "pack_path": str(packs_dir),
                    }
                except Exception as exc:
                    logger.warning("Failed reading pack.json for %s: %s", clean_id, exc)

            return {"success": False, "error": f"Agent '{clean_id}' not found in registry or pack store."}

        # Extract tools and skills from profile
        tools_list: list[str] = []
        if getattr(profile, "pack_tool_names", None):
            tools_list.extend(profile.pack_tool_names)
        if getattr(profile, "skills", None):
            for s in profile.skills:
                if hasattr(s, "tools") and s.tools:
                    tools_list.extend(s.tools)
                elif isinstance(s, dict) and "tools" in s:
                    tools_list.extend(s["tools"])
        if not tools_list and getattr(profile, "allowed_tool_names", None):
            tools_list.extend(profile.allowed_tool_names)

        skills_list: list[str] = []
        if getattr(profile, "skills", None):
            for s in profile.skills:
                sid = getattr(s, "id", None) or (s.get("id") if isinstance(s, dict) else str(s))
                if sid:
                    skills_list.append(sid)
        if getattr(profile, "allowed_skill", None):
            skills_list.extend(profile.allowed_skill)

        pack_path = self._resolved_data_dir() / "packs" / clean_id

        return {
            "success": True,
            "agent_id": clean_id,
            "name": getattr(profile, "name", clean_id),
            "description": getattr(profile, "description", ""),
            "avatar_icon": getattr(profile, "avatar_icon", "bot"),
            "tools": sorted(set(filter(None, tools_list))),
            "skills": sorted(set(filter(None, skills_list))),
            "pack_path": str(pack_path) if pack_path.exists() else None,
        }

    async def launch_factory_training(
        self,
        target_agent_id: str,
        seed_intent: str = "",
        objectives: Optional[List[str]] = None,
        deliverable_type: str = "auto",
        reference_docs: str = "",
        target_host: str = "local",
        target_directory: Optional[str] = None,
        risk_policy: str = "ask",
        session_id: Optional[str] = None,
        constraints: Optional[str] = None,
        prerequisites: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Dispatch a capability manufacturing job into Agent Training Factory [REQ-FACT-061]."""
        clean_target = str(target_agent_id or "").strip()
        if not clean_target:
            return {"success": False, "error": "target_agent_id is required."}

        clean_intent = str(seed_intent or "").strip()
        raw_objectives = objectives or []
        clean_objectives = [str(obj).strip() for obj in raw_objectives if str(obj).strip()]

        if not clean_intent and not clean_objectives:
            return {"success": False, "error": "seed_intent or at least one objective is required."}

        # Fallback intent if only objectives provided
        if not clean_intent:
            clean_intent = clean_objectives[0]

        # Use store to persist job and packet
        if self.store is None:
            return {"success": False, "error": "Database state store not available."}

        repo = FactoryPacketRepository(self.store)

        # Resolve session anchor
        actual_session = session_id
        if not actual_session:
            if hasattr(self.store, "list_sessions"):
                autoreiv_sessions = self.store.list_sessions(agent_id="autoreiv")
                if autoreiv_sessions:
                    actual_session = autoreiv_sessions[0].id
                elif hasattr(self.store, "create_session"):
                    new_sess = self.store.create_session(agent_id="autoreiv", title="AutoReiv Control Plane")
                    actual_session = new_sess.id
        if not actual_session:
            actual_session = f"sess_factory_{uuid.uuid4().hex[:8]}"

        job_id = f"fjob_{uuid.uuid4().hex[:12]}"
        job = FactoryJob(
            id=job_id,
            target_agent_id=clean_target,
            session_id=actual_session,
            status="queued",
            seed_intent=clean_intent,
            objectives=clean_objectives,
            target_host=target_host or "local",
            active_graph_id="agent_training_factory_v1",
            current_node_id="intent_distill",
        )
        repo.save_job(job)

        constraints_list = [f"risk_policy={risk_policy}"]
        if deliverable_type and deliverable_type != "auto":
            constraints_list.append(f"deliverable_type={deliverable_type}")
        if constraints:
            constraints_list.append(f"constraints={constraints}")
        if prerequisites:
            constraints_list.append(f"prerequisites={prerequisites}")
        if reference_docs:
            constraints_list.append(f"reference_docs={reference_docs}")

        # Auto-resolve target directory from active project if omitted [REQ-FACT-070]
        resolved_target_dir = str(target_directory or "").strip() or None
        if not resolved_target_dir and self.store is not None:
            if hasattr(self.store, "get_active_project"):
                try:
                    act_proj = self.store.get_active_project()
                    if act_proj and getattr(act_proj, "path", None):
                        resolved_target_dir = str(act_proj.path)
                    elif isinstance(act_proj, dict) and act_proj.get("path"):
                        resolved_target_dir = str(act_proj["path"])
                except Exception:
                    pass
            if not resolved_target_dir and hasattr(self.store, "get_setting"):
                try:
                    p_path = self.store.get_setting("selected_project_path")
                    if p_path:
                        resolved_target_dir = str(p_path)
                except Exception:
                    pass

        work_pkt = WorkPacket(
            goal=clean_intent,
            target_agent_id=clean_target,
            facts=clean_objectives,
            constraints=constraints_list,
            done_when="Seed objectives verified in sandbox battery",
            target_host=target_host or "local",
            target_directory=resolved_target_dir,
        )
        envelope = FactoryPacket(
            id=f"fpkt_{uuid.uuid4().hex[:12]}",
            job_id=job_id,
            packet_type="work",
            sender_role="orchestrator",
            recipient_role="intent_distill",
            node_id="intent_distill",
            payload=work_pkt.model_dump(),
        )
        repo.save_packet(envelope)

        # Trigger factory runner tick if active
        runner = self.orchestrator
        if runner is not None and hasattr(runner, "tick"):
            try:
                import asyncio

                asyncio.create_task(runner.tick())
            except Exception as tick_exc:
                logger.warning("Failed triggering orchestrator tick: %s", tick_exc)

        return {
            "success": True,
            "job_id": job_id,
            "target_agent_id": clean_target,
            "status": "queued",
            "seed_intent": clean_intent,
            "deliverable_type": deliverable_type,
            "message": (
                f"Capability manufacturing job {job_id} queued successfully for agent '{clean_target}'. "
                "The 8-phase pipeline is now active. Switch to Factory Studio to monitor progress."
            ),
        }
