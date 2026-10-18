"""
System Prompt Assembly & Turn Tool Scoping [REQ-EPISODIC-003, CARD-562, CARD-675, CARD-712].
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Collection, List, Optional, Tuple

from src.application.agent_skills.allowed_tools import domain_line, resolve_allowed_tools
from src.application.kernel.repeat_guard import rejected_tool_names
from src.application.kernel.reply_rules import REPLY_RULES_BLOCK
from src.application.skills.user_catalog import render_skill_index
from src.domain.agents.product_concepts import AUTOREIV_CONCEPTS
from src.domain.gateway.models import ChatMessage, Role
from src.domain.kernel.models import AgentProfile

logger = logging.getLogger(__name__)


def build_effective_system_message(
    kernel: Any,
    agent: AgentProfile,
    user_content: Optional[str] = None,
    sent_tools: Optional[Collection[str]] = None,
    guidance_fn: Optional[Callable[[set[str] | frozenset[str]], str]] = None,
) -> ChatMessage:
    """
    Construct system prompt enriched with skill index, episodic facts, cognitive memory,
    active project context, and domain/reply rules [REQ-EPISODIC-003, CARD-675].
    """
    tones_lookup = None
    if kernel.state_store and hasattr(kernel.state_store, "list_tones"):
        try:
            tones_list = kernel.state_store.list_tones()
            tones_lookup = {t.id: t.directive for t in tones_list}
        except Exception:
            tones_lookup = None

    base_prompt = agent.get_effective_system_prompt(tones_lookup=tones_lookup)
    base_prompt = f"{base_prompt}\n\n{AUTOREIV_CONCEPTS}"

    skill_block = render_skill_index(
        getattr(agent, "allowed_skill", None),
        kernel.user_skill_catalog,
        agent_id=getattr(agent, "id", None),
        can_open=sent_tools is None or "skill_view" in sent_tools,
    )
    if skill_block:
        base_prompt = f"{base_prompt}\n\n{skill_block}"

    memory_block = None
    if user_content and kernel.state_store and hasattr(kernel.state_store, "search_facts"):
        try:
            matched_facts = kernel.state_store.search_facts(query=user_content, limit=4)
            if matched_facts:
                from src.application.skills.memory_tools import render_memory_context

                memory_block = render_memory_context(matched_facts)
                if memory_block:
                    base_prompt = f"{base_prompt}\n\n{memory_block}"
        except Exception as e:
            logger.debug("Episodic memory auto-recall skipped: %s", e)

    cog_block = None
    if getattr(agent, "memory_enabled", True) and getattr(agent, "id", None) != "direct":
        try:
            from src.application.memory.assembler import MemoryContextAssembler
            from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

            agent_repo = AgentMemoryRepository(agent_id=agent.id, data_dir=kernel.data_dir)
            agent_repo.initialize_schema()
            model_name = kernel._resolve_model(agent)
            ctx_limit = kernel._resolve_context_limit(agent, model_name)
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
            logger.debug("Per-agent cognitive memory assembly skipped: %s", e)

    if kernel.state_store:
        try:
            from src.application.sdlc.projects_service import ProjectsService

            is_developer = getattr(agent, "id", None) == "developer"
            allowed_tools: set[str] = set(resolve_allowed_tools(agent).names)
            has_project_tools = bool(
                allowed_tools.intersection(
                    {"read_project_file", "write_project_file", "list_project_dir", "cli_exec", "git_status", "git_diff"}
                )
            )

            if is_developer or has_project_tools:
                proj_svc = ProjectsService(store=kernel.state_store)
                selected_proj = proj_svc.get_selected()
                if selected_proj and selected_proj.get("path"):
                    proj_name = selected_proj.get("name") or selected_proj.get("slug") or "Active Project"
                    proj_path = selected_proj.get("path")
                    tool_guidance = guidance_fn(allowed_tools) if guidance_fn else ""
                    project_context = (
                        "## Active Selected Project\n"
                        f"- Name: {proj_name}\n"
                        f"- Path: {proj_path}\n"
                        "All project code, tests, scripts, and CLI commands should target this project directory "
                        f"unless explicitly instructed otherwise. {tool_guidance}"
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
                            extra_lines.append(
                                f"Active Work Cards ({len(card_files)} total): Recent: {', '.join(recent)}"
                            )
                    if extra_lines:
                        project_context = project_context + "\n" + "\n".join(f"- {line}" for line in extra_lines)
                    base_prompt = f"{base_prompt}\n\n{project_context}"
        except Exception as e:
            logger.debug("Active project context injection skipped: %s", e)

    if getattr(agent, "id", None) != "direct":
        base_prompt = f"{base_prompt}\n\n## Your domain\n{domain_line(agent)}"
        base_prompt = f"{base_prompt}\n\n{REPLY_RULES_BLOCK}"

    kernel._last_progressive_skills = [skill_block] if skill_block else []
    kernel._last_episodic_memory = [m for m in (memory_block, cog_block) if m]

    return ChatMessage(role=Role.SYSTEM, content=base_prompt)


def turn_tools_and_system_message(
    kernel: Any,
    agent: AgentProfile,
    user_content: Optional[str],
    history: List[Any],
    session_id: Optional[str] = None,
) -> Tuple[List[Any], set[str], ChatMessage]:
    """Resolve this call's tools, their names, and a system message that names only sent tools [CARD-675, CARD-688]."""
    active_tools = kernel._resolve_active_tools(
        agent,
        user_content,
        matched_capability_ids=kernel._turn_matched_capability_ids,
        session_id=session_id,
        history=history,
    )
    rejected_now = rejected_tool_names(history)
    active_tools = [t for t in active_tools if t.name not in rejected_now]
    offered_names = {t.name for t in active_tools}
    system_msg = kernel._build_effective_system_message(agent, user_content, sent_tools=offered_names)
    return active_tools, offered_names, system_msg
