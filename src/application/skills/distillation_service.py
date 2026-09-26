"""
In-Situ Skill Distillation & Runtime Adoption Service [CARD-352, REQ-SKIL-010, REQ-SKIL-013, REQ-SKIL-014].
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.domain.gateway.models import ChatMessage, CompletionRequest, Role
from src.domain.observability.models import LEGACY_TOOL_ESCALATION, TOOL_ESCALATION

logger = logging.getLogger(__name__)

SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


class DistillTurnNotFound(LookupError):
    """The message id is not an agent reply in that chat [CARD-500 REQ-500-003]."""


class AdoptAgentNotFound(LookupError):
    """Adopt named an agent that does not exist [CARD-502 REQ-502-007]."""


class AdoptSkillConflict(ValueError):
    """Adopt would overwrite a platform skill of the same id [CARD-502 REQ-502-008]."""


class SkillDistillationService:
    """Extracts turn context, diagnoses procedural friction, and adopts skills into user packs."""

    def __init__(
        self,
        store: Any,
        gateway: Any = None,
        data_dir: Optional[Union[str, Path]] = None,
        agent_registry: Any = None,
    ):
        self.store = store
        self.gateway = gateway
        self.data_dir = Path(data_dir) if data_dir is not None else None
        self.agent_registry = agent_registry

    async def distill_turn(
        self,
        session_id: str,
        message_id: str,
        guidance: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a conversation turn, diagnose failure modes, and synthesize a SKILL.md proposal.
        """
        turn_data = self._extract_turn_history(session_id, message_id)
        target_agent_id = turn_data["target_agent_id"]
        guidance_text = (guidance or "").strip()

        llm_result = await self._run_llm_distillation(turn_data, guidance_text)
        if llm_result:
            result = self._build_distill_response(target_agent_id, llm_result, guidance_text)
        else:
            # Defensive fallback if LLM is unreachable
            result = self._build_heuristic_distill_response(target_agent_id, turn_data, guidance_text)

        result["session_id"] = session_id
        result["adoption_state"] = "pending"
        result["source_message_id"] = message_id

        # Persist proposal as a first-class chat message [CARD-358, REQ-SKIL-015]
        if self.store and hasattr(self.store, "save_message"):
            proposal_msg = ChatMessage(
                role=Role.SKILL_PROPOSAL,
                content=json.dumps(result),
                name="distill_skill",
            )
            persisted_msg_id = self.store.save_message(
                session_id=session_id,
                agent_id=target_agent_id,
                message=proposal_msg,
            )
            result["message_id"] = persisted_msg_id

        return result

    def adopt_skill(
        self,
        target_agent_id: str,
        skill_id: str,
        runbook_markdown: str,
        data_dir: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """
        Write the runbook to packs/<agent_id>/skills/<skill_id>/SKILL.md and switch the skill on
        through the shared agent save path [CARD-502].
        """
        clean_agent = (target_agent_id or "").strip()
        clean_skill = (skill_id or "").strip()

        if not clean_agent or not clean_skill:
            raise ValueError("Agent ID and Skill ID cannot be empty.")
        if not SAFE_ID_RE.match(clean_agent) or not SAFE_ID_RE.match(clean_skill):
            raise ValueError("Invalid agent or skill identifier (disallowed characters or path traversal).")

        root = Path(data_dir) if data_dir is not None else self.data_dir
        if root is None:
            raise ValueError("Data directory is required for skill adoption.")
        if self.agent_registry is None:
            raise ValueError("Agent registry is required for skill adoption.")

        from src.application.agent_packs.schema import PLATFORM_SKILL_IDS, is_platform_pack
        from src.application.agent_packs.skill_list import add_skill_to_agent
        from src.infrastructure.skills.platform_pack_promotion import (
            keep_customizations_enabled,
            platform_seed_skills,
        )

        # CARD-502 REQ-502-007: never create a folder for an agent that does not exist
        if self.agent_registry.get_agent(clean_agent) is None:
            raise AdoptAgentNotFound(
                f"There is no agent called {clean_agent}. Pick an agent that exists and try again."
            )
        # CARD-502 REQ-502-008: never overwrite a shipped skill with a lesson of the same id
        if clean_skill in PLATFORM_SKILL_IDS or clean_skill in platform_seed_skills(clean_agent):
            raise AdoptSkillConflict(
                f"{clean_agent} already has a platform skill called {clean_skill}. "
                "Rename the lesson and try again."
            )

        skill_dir = root / "packs" / clean_agent / "skills" / clean_skill
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(runbook_markdown, encoding="utf-8")

        skill_title, skill_desc = self._parse_frontmatter(runbook_markdown, clean_skill)
        # CARD-502 REQ-502-001: same save path as Agent Studio so the skill survives restart
        profile, already = add_skill_to_agent(
            self.store,
            self.agent_registry,
            agent_id=clean_agent,
            skill_id=clean_skill,
            data_dir=root,
            skill_entry={"id": clean_skill, "name": skill_title, "description": skill_desc, "tools": []},
        )
        active = clean_skill in list(getattr(profile, "allowed_skill", None) or [])
        return {
            "status": "adopted",
            "target_agent_id": clean_agent,
            "skill_id": clean_skill,
            "name": skill_title,
            "file_path": f"packs/{clean_agent}/skills/{clean_skill}/SKILL.md",
            "active": active,
            "already_adopted": already,
            "resets_on_restart": is_platform_pack(clean_agent) and not keep_customizations_enabled(self.store),
        }

    def _extract_turn_history(self, session_id: str, message_id: str) -> Dict[str, Any]:
        target_agent = "autoreiv"
        user_prompt = ""
        assistant_resp = ""
        tool_calls: List[Dict[str, Any]] = []
        tool_results: List[Dict[str, Any]] = []

        if hasattr(self.store, "get_session"):
            session = self.store.get_session(session_id)
            if session:
                target_agent = (
                    getattr(session, "agent_id", None) or getattr(session, "lead_agent_id", None) or target_agent
                )

        raw_messages = list(self.store.get_messages(session_id)) if hasattr(self.store, "get_messages") else []

        # Also direct query to inspect message IDs if store has connection
        if hasattr(self.store, "_get_connection"):
            try:
                conn = self.store._get_connection()
                cur = conn.cursor()
                cur.execute("SELECT agent_id FROM messages WHERE id = ? LIMIT 1", (message_id,))
                row = cur.fetchone()
                if row and row[0]:
                    target_agent = row[0]
            except Exception:
                pass

        # CARD-500 REQ-500-002/003: distill the clicked reply's turn only; no fallback to "latest".
        roles = [getattr(m.role, "value", str(m.role)).lower() for m in raw_messages]
        clicked = next((i for i, m in enumerate(raw_messages) if getattr(m, "id", None) == message_id), None)
        if clicked is None or roles[clicked] != "assistant":
            raise DistillTurnNotFound("That message is not a reply in this chat. Teach from one of the agent's replies.")
        start = next((i for i in range(clicked - 1, -1, -1) if roles[i] == "user"), -1)
        if start >= 0:
            user_prompt = raw_messages[start].content or ""
        end = clicked
        while end + 1 < len(raw_messages) and roles[end + 1] == "tool":
            end += 1
        for i in range(start + 1, end + 1):
            msg = raw_messages[i]
            if roles[i] == "assistant":
                for tc in getattr(msg, "tool_calls", None) or []:
                    tool_calls.append({"name": tc.name, "arguments": tc.arguments})
                if msg.content and i <= clicked:
                    assistant_resp = msg.content  # the clicked reply wins; else the last non-empty one
            elif roles[i] == "tool":
                tool_results.append({"name": getattr(msg, "name", None) or "tool", "content": (msg.content or "")[:600]})

        return {
            "target_agent_id": target_agent,
            "user_prompt": user_prompt,
            "assistant_response": assistant_resp,
            "tool_calls": tool_calls,
            "tool_results": tool_results,
        }

    async def _run_llm_distillation(self, turn_data: Dict[str, Any], guidance: str) -> Optional[Dict[str, Any]]:
        if not self.gateway:
            return None

        system_prompt = (
            "You are an expert Autonomous Agent Skill Architect. "
            "An agent made an error, hit friction, or received human steering. "
            "Diagnose whether this issue can be prevented via procedural rules in a SKILL.md runbook, "
            "or if the agent fundamentally lacks a native Python/host tool (needs_tool: true). "
            "Return ONLY a JSON object with schema:\n"
            "{\n"
            '  "needs_tool": false,\n'
            '  "skill_id": "kebab-case-slug",\n'
            '  "name": "Title Case Name",\n'
            '  "description": "Short summary under 60 characters",\n'
            '  "plain_summary": {\n'
            '    "observed_slip": "Plain sentence describing what went wrong",\n'
            '    "remedy": "Plain sentence describing what the new rule teaches"\n'
            "  },\n"
            '  "when_to_use": "Exact trigger conditions",\n'
            '  "procedure": ["Step 1", "Step 2"],\n'
            '  "pitfalls": ["Do not X", "Forbidden Y"],\n'
            '  "verification": ["Check Z"]\n'
            "}\n"
            "OR if needs_tool is true:\n"
            "{\n"
            '  "needs_tool": true,\n'
            '  "suggested_tool_name": "snake_case_tool_name",\n'
            '  "plain_summary": { "observed_slip": "...", "remedy": "..." },\n'
            '  "tool_escalation": {\n'
            '    "target_agent_id": "<agent>",\n'
            '    "seed_intent": "<short intent>",\n'
            '    "starter_objectives": ["Obj 1", "Obj 2"],\n'
            '    "deliverable_type": "tool"\n'
            "  }\n"
            "}"
        )

        user_content = (
            f"Target Agent: {turn_data['target_agent_id']}\n"
            f"User Prompt: {turn_data['user_prompt']}\n"
            f"Assistant Output: {turn_data['assistant_response'][:1000]}\n"
            f"Tool Calls: {json.dumps(turn_data['tool_calls'])}\n"
            f"Tool Results: {json.dumps(turn_data['tool_results'])}\n"
            f"Human Guidance / Correction: {guidance or 'Auto-diagnose from turn context'}\n"
        )

        try:
            req = CompletionRequest(
                model=getattr(self.gateway, "default_model_id", "default") or "default",
                messages=[
                    ChatMessage(role=Role.SYSTEM, content=system_prompt),
                    ChatMessage(role=Role.USER, content=user_content),
                ],
                temperature=0.2,
                max_tokens=800,
            )
            resp = await asyncio.wait_for(self.gateway.complete(req), timeout=4.5)
            raw_text = getattr(resp, "text", None) or (
                resp.message.content if getattr(resp, "message", None) else str(resp)
            )
            text = (raw_text or "").strip()
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                return json.loads(match.group(0))
        except Exception as exc:
            logger.warning("LLM distillation call failed or timed out: %s", exc)

        return None

    def _build_distill_response(
        self,
        target_agent_id: str,
        llm_data: Dict[str, Any],
        guidance: str,
    ) -> Dict[str, Any]:
        needs_tool = bool(llm_data.get("needs_tool", False))
        plain_summary = llm_data.get("plain_summary") or {
            "observed_slip": "The agent required steering during this turn.",
            "remedy": guidance or "Add procedural constraints to guide future actions.",
        }

        if needs_tool:
            # CARD-520 REQ-520-002: accept the pre-rename key from the model too.
            escalation = llm_data.get(TOOL_ESCALATION) or llm_data.get(LEGACY_TOOL_ESCALATION) or {
                "target_agent_id": target_agent_id,
                "seed_intent": guidance or "Synthesize missing capability tool",
                "starter_objectives": ["Implement verified tool handler", "Add schema guardrails"],
                "deliverable_type": "tool",
            }
            if "target_agent_id" not in escalation:
                escalation["target_agent_id"] = target_agent_id
            if "suggested_tool_name" in llm_data:
                escalation["suggested_tool_name"] = llm_data["suggested_tool_name"]

            return {
                "status": "ok",
                "target_agent_id": target_agent_id,
                "needs_tool": True,
                "plain_summary": plain_summary,
                TOOL_ESCALATION: escalation,
                "skill_id": None,
                "name": None,
                "description": None,
                "runbook_markdown": None,
            }

        skill_id = self._slugify(llm_data.get("skill_id") or llm_data.get("name") or "agent-procedural-rule")
        name = llm_data.get("name") or skill_id.replace("-", " ").title()
        desc = (llm_data.get("description") or f"Procedural guidance for {target_agent_id}")[:60]

        when_to_use = llm_data.get("when_to_use") or "When executing operations relevant to this domain."
        procedure = llm_data.get("procedure") or ["Follow the approved steps.", "Verify the result."]
        pitfalls = llm_data.get("pitfalls") or ["Do not repeat the unverified action."]
        verification = llm_data.get("verification") or ["Confirm state before concluding."]

        proc_md = "\n".join([f"{i + 1}. {step}" for i, step in enumerate(procedure)])
        pit_md = "\n".join([f"- {pit}" for pit in pitfalls])
        ver_md = "\n".join([f"- {ver}" for ver in verification])

        runbook_markdown = (
            f"---\n"
            f"name: {skill_id}\n"
            f"description: {desc}\n"
            f"---\n\n"
            f"# {name}\n\n"
            f"## When to Use\n{when_to_use}\n\n"
            f"## Procedure\n{proc_md}\n\n"
            f"## Common Pitfalls & Forbidden Paths\n{pit_md}\n\n"
            f"## Verification\n{ver_md}\n"
        )

        return {
            "status": "ok",
            "target_agent_id": target_agent_id,
            "needs_tool": False,
            "skill_id": skill_id,
            "name": name,
            "description": desc,
            "plain_summary": plain_summary,
            "runbook_markdown": runbook_markdown,
            TOOL_ESCALATION: None,
        }

    def _build_heuristic_distill_response(
        self,
        target_agent_id: str,
        turn_data: Dict[str, Any],
        guidance: str,
    ) -> Dict[str, Any]:
        hint = guidance or turn_data["user_prompt"] or "procedural-rule"
        slug = self._slugify(hint[:30]) or "operational-guidance"
        name = slug.replace("-", " ").title()
        desc = f"Procedural instructions for {name}"[:60]

        plain_summary = {
            "observed_slip": f"Agent drifted on '{turn_data['user_prompt'][:100]}'."
            if turn_data["user_prompt"]
            else "Procedural friction observed in turn.",
            "remedy": guidance if guidance else "Enforce explicit steps and forbidden paths.",
        }

        runbook_markdown = (
            f"---\n"
            f"name: {slug}\n"
            f"description: {desc}\n"
            f"---\n\n"
            f"# {name}\n\n"
            f"## When to Use\nWhen performing actions guided by this runbook.\n\n"
            f"## Procedure\n1. Review the requirement.\n2. {guidance or 'Execute verified steps.'}\n\n"
            f"## Common Pitfalls & Forbidden Paths\n- Do not skip validation.\n\n"
            f"## Verification\n- Verify output matches expectations.\n"
        )

        return {
            "status": "ok",
            "target_agent_id": target_agent_id,
            "needs_tool": False,
            "skill_id": slug,
            "name": name,
            "description": desc,
            "plain_summary": plain_summary,
            "runbook_markdown": runbook_markdown,
            TOOL_ESCALATION: None,
        }

    def _slugify(self, text: str) -> str:
        s = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
        return s or "custom-skill"

    def _parse_frontmatter(self, md: str, fallback_id: str) -> tuple[str, str]:
        title = fallback_id.replace("-", " ").title()
        desc = f"Runbook for {fallback_id}"
        m_title = re.search(r"^#\s+(.+)$", md, re.MULTILINE)
        if m_title:
            title = m_title.group(1).strip()
        m_desc = re.search(r"description:\s*(.+)$", md, re.MULTILINE)
        if m_desc:
            desc = m_desc.group(1).strip()
        return title, desc[:60]
