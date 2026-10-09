"""Read or write: what each platform tool does to the world [CARD-674].

A planning (Formulate) step is sent, and may call, only READ tools (see phase_roles.planning_phase_block_reason).
A tool that is in neither set is unlabeled and is not used while planning (fail closed); the CARD-674 test fails
when a registered platform tool has no label, so a new tool must be labeled here.

READ: looks things up and changes nothing a person would notice (files, notes, cards, settings, other systems).
WRITE: creates, changes, moves or deletes something, runs code or commands, starts work or other agents, or
records a durable result (grades, facts, proposals, plan steps).

This label is only for planning. It is not the registration ``risk`` (CARD-539 D11), which drives per-call
confirmation, so labeling a tool WRITE here does not add an approval card in chat.
"""

from __future__ import annotations

from typing import Optional

READ = "read"
WRITE = "write"

READ_TOOLS: frozenset[str] = frozenset(
    {
        # wiki
        "wiki_graph",
        "wiki_note_list",
        "wiki_note_read",
        "wiki_note_search",
        "wiki_overview",
        "wiki_template_list",
        "wiki_template_read",
        "education_wiki_template_catalog",
        # memory, skills, agents, session
        "recall_agent_memory",
        "query_agent_database",
        "skill_view",
        "list_user_skills",
        "list_available_skills_and_tools",
        "lookup_agents",
        "inspect_agent",
        "ask_clarification",
        "get_active_plan",
        "get_session_info",
        "get_session_transcript",
        "get_session_artifact",
        "get_agent_sessions",
        "read_document_file",
        # education (looks only)
        "education_due_review_list",
        "education_flashcard_next",
        "education_mastery_due",
        "education_progress_courses",
        "education_progress_mastery",
        "education_progress_summary",
        "education_quiz_next",
        # system and observability
        "system_info",
        "inspect_system_health",
        "get_system_logs",
        "get_recent_errors",
        "get_tool_health_matrix",
        "get_agent_usage_summary",
        "test_provider_connectivity",
        "verify_telemetry_consistency",
        "validate_metric_bounds",
        "assert_json_schema",
        "ssh_inspect_environment",
        "ssh_read_file",
        # projects, repo, cards, specs
        "active_project_info",
        "list_project_dir",
        "read_project_file",
        "search_project",
        "read_steering",
        "read_spec",
        "list_cards",
        "read_card",
        "review_card",
        "run_project_checks",
        "git_status",
        "git_diff",
        "git_branch",
        "repo_file_list",
        "repo_file_read",
        # tool authoring and QA (inspect only)
        "view_native_tool",
        "plan_native_folder",
        "test_mcp_server",
        "list_journey_reports",
        "read_journey_report",
        "summarize_journey_failures",
    }
)

WRITE_TOOLS: frozenset[str] = frozenset(
    {
        # wiki
        "wiki_note_create",
        "wiki_note_update",
        "wiki_note_append",
        "wiki_note_archive",
        "wiki_note_organize",
        "wiki_template_create",
        "wiki_template_update",
        "promote_artifact_to_wiki",
        "education_wiki_curate_from_curriculum",
        "education_wiki_curate_from_link",
        # education (records results or starts jobs)
        "education_due_review_complete",
        "education_flashcard_grade",
        "education_mastery_upsert",
        "education_quiz_extract",
        "education_quiz_grade",
        "education_retention_run",
        # memory, plans, delegation, proposals
        "memorize_fact",
        "execute_agent_database",
        "append_plan_step",
        "mark_plan_step_completed",
        "handoff_to_agent",
        "batch_worker_scan",
        "propose_followup",
        "propose_skill",
        "propose_tool",
        "commit_skill",
        # code, shell, remote
        "cli_exec",
        "execute_code",
        "ssh_exec_command",
        "run_journey",
        # projects, repo, cards, specs
        "create_project",
        "write_project_file",
        "patch_project_file",
        "write_card",
        "set_card_status",
        "hand_off_card",
        "finish_review",
        "sync_card_issue",
        "write_spec",
        "git_commit",
        "git_create_branch",
        "repo_file_write",
        "repo_file_patch",
        "repo_file_rollback",
        "repo_create_worktree",
        "repo_remove_worktree",
        # tool authoring
        "register_native_tool",
        "register_mcp_service",
        "scaffold_mcp_server",
        "deploy_mcp_container",
    }
)

_READ_RISKS = frozenset({"read_only", "read", "readonly"})


def tool_access(name: str, declared_risk: Optional[str] = None) -> Optional[str]:
    """READ, WRITE, or None when the tool is unlabeled.

    A risk declared at registration wins (``read_only`` is READ, any other declared tier is WRITE), so an MCP or
    runtime-built tool that declares itself read-only can plan. Otherwise the platform label above.
    """
    risk = str(declared_risk or "").strip().lower()
    if risk:
        return READ if risk in _READ_RISKS else WRITE
    n = str(name or "").strip()
    if n in READ_TOOLS:
        return READ
    if n in WRITE_TOOLS:
        return WRITE
    return None
