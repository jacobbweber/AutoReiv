"""
Context Window Compactor [REQ-MEMORY-001, REQ-MEMORY-002, REQ-COMPACT-001 - REQ-COMPACT-004].
Implements sliding-window truncation, large tool output pruning, root intent preservation,
and model-aware dynamic token budget management.
"""

from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from src.domain.gateway.models import ChatMessage, Role


@dataclass
class CompactionMetrics:
    original_tokens: int
    compacted_tokens: int
    turns_compacted: int
    tools_truncated: int
    compression_ratio: float
    compaction_applied: bool


# CARD-524: an unconfigured or unrecognised model is budgeted at 32k (was 8192).
UNCONFIGURED_CONTEXT_BASELINE = 32768


def _override_context_limit(raw: str, model_overrides: Optional[dict]) -> Optional[int]:
    """Settings Studio per-model window for this model name, if one is set."""
    name = raw.lower()
    candidates = []
    if raw:
        candidates.append(raw)
        candidates.append(name)
        if "/" in name:
            candidates.append(name.split("/", 1)[1])
    overrides = model_overrides or {}
    for key in candidates:
        if key in overrides:
            try:
                parsed = int(overrides[key])
            except (TypeError, ValueError):
                continue
            if parsed > 0:
                return parsed
        for stored_key, stored_val in overrides.items():
            if str(stored_key).lower() == key:
                try:
                    parsed = int(stored_val)
                except (TypeError, ValueError):
                    continue
                if parsed > 0:
                    return parsed
    return None


def _family_context_limit(name: str) -> Optional[int]:
    """Window guessed from an explicit size tag or the model family; None when unrecognised."""
    if not name or name == "default":
        return None
    if "1m" in name or "gemini-1.5" in name or "gemini-2.0" in name:
        return 1000000
    if "256k" in name or "262k" in name or "262144" in name or "nemotron" in name:
        return 262144
    if (
        "128k" in name
        or "gpt-4o" in name
        or "claude-3-5" in name
        or "claude-3-7" in name
        or "llama3.3" in name
        or "llama-3.3" in name
        or "deepseek" in name
    ):
        return 128000
    if "65k" in name or "64k" in name:
        return 65536
    # qwen3.8 / qwen35 native window is 262144; Ollama on a 24GB card
    # typically serves 32k. Budget the served window unless the tag
    # already named a larger explicit size above.
    if (
        "32k" in name
        or "qwen2.5" in name
        or "qwen-2.5" in name
        or "qwen3.8" in name
        or "qwen35" in name
        or "mistral" in name
        or "codestral" in name
    ):
        return 32768
    if "16k" in name or "gpt-3.5-turbo-16k" in name:
        return 16384
    if "8k" in name or "llama3.2" in name:
        return 8192
    if "4k" in name:
        return 4096
    return None


def get_model_context_limit(
    model_name: str,
    default_override: Optional[int] = None,
    model_overrides: Optional[dict] = None,
) -> int:
    """
    Returns context limit in tokens [REQ-COMPACT-001].
    Settings overrides win, then explicit size tags, then family guesses,
    then the 32k unconfigured baseline [CARD-524].
    """
    raw = (model_name or "").strip()
    override = _override_context_limit(raw, model_overrides)
    if override:
        return override
    if default_override:
        try:
            parsed = int(default_override)
        except (TypeError, ValueError):
            parsed = 0
        if parsed > 0:
            return parsed
    family = _family_context_limit(raw.lower())
    return family if family is not None else UNCONFIGURED_CONTEXT_BASELINE


def resolve_agent_context_limit(
    agent: Optional[Any] = None,
    state_store: Optional[Any] = None,
    fallback_model: Optional[str] = None,
) -> int:
    """
    Unified 3-tier Context Limit Resolution Cascade [CARD-162]:
    Tier 1 (Per-Agent Explicit): If agent has context_window > 0, use it.
    Tier 2 (Per-Agent Model Default): If blank, and agent specifies a custom model/provider,
           check model overrides or model name architecture defaults.
    Tier 3 (Platform Settings Fallback): If agent uses default provider/model (or custom model
           has no override), fall back to platform default_context_window (Settings Studio),
           then platform default model limit, then the 32768 baseline [CARD-524].
    """
    # 1. Tier 1: Per-Agent explicit context window override
    if agent and getattr(agent, "context_window", None) is not None:
        try:
            cw = int(agent.context_window)
            if cw > 0:
                return cw
        except (TypeError, ValueError):
            pass

    # Read platform settings if store is available
    default_ctx_override = None
    model_overrides = None
    platform_def_model = None

    if state_store and hasattr(state_store, "get_setting"):
        matrix_data = state_store.get_setting("purpose_matrix")
        if isinstance(matrix_data, dict):
            raw_def = matrix_data.get("default_context_window")
            if raw_def is not None:
                try:
                    parsed_def = int(raw_def)
                    if parsed_def > 0:
                        default_ctx_override = parsed_def
                except (TypeError, ValueError):
                    pass
            raw_windows = matrix_data.get("model_context_windows")
            if isinstance(raw_windows, dict):
                model_overrides = raw_windows
            matrix_model = matrix_data.get("default_model")
            if isinstance(matrix_model, str) and matrix_model and matrix_model != "default":
                platform_def_model = matrix_model

        prov_data = state_store.get_setting("provider_settings")
        if isinstance(prov_data, dict):
            prov_model = prov_data.get("default_model_id")
            if isinstance(prov_model, str) and prov_model and prov_model != "default":
                platform_def_model = prov_model

    # 2. Tier 2: Per-Agent explicit model / provider
    agent_model = getattr(agent, "model", None) if agent else None
    if not agent_model and fallback_model:
        agent_model = fallback_model

    raw_agent_model = str(agent_model or "").strip()
    is_custom_model = bool(
        raw_agent_model
        and raw_agent_model.lower() != "default"
        and raw_agent_model.lower() not in {
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
    )

    if is_custom_model:
        # Check explicit model override dictionary first
        if model_overrides and raw_agent_model in model_overrides:
            try:
                parsed_mo = int(model_overrides[raw_agent_model])
                if parsed_mo > 0:
                    return parsed_mo
            except (TypeError, ValueError):
                pass

        # Use model's native limit heuristic without injecting platform default override.
        # An unrecognised model defers to the platform default window when one is set.
        known_limit = _override_context_limit(raw_agent_model, model_overrides) or _family_context_limit(
            raw_agent_model.lower()
        )
        if known_limit:
            return known_limit
        if not default_ctx_override:
            return UNCONFIGURED_CONTEXT_BASELINE

    # 3. Tier 3: Agent on default provider / model -> Platform settings fallback
    if default_ctx_override and default_ctx_override > 0:
        return default_ctx_override

    if platform_def_model:
        return get_model_context_limit(
            platform_def_model,
            default_override=default_ctx_override,
            model_overrides=model_overrides,
        )

    return get_model_context_limit(
        "default",
        default_override=default_ctx_override,
        model_overrides=model_overrides,
    )


def resolve_max_tool_chars(
    context_limit: Optional[int],
    *,
    min_chars: int = 8000,
    max_chars: int = 120000,
    char_ratio: float = 1.0,
) -> int:
    """
    Resolves the maximum character budget for an individual tool return [REQ-TOOL-BUDGET-001].
    Scales dynamically with the model's context window:
    - Minimum floor: 8,000 characters (~2,000 tokens) for models <= 8,192
    - Dynamic scaling: roughly 1 char per token of context limit (approx 25% of character capacity)
    - Maximum ceiling: 120,000 characters (~30,000 tokens) to guard against runaway payloads
    """
    if context_limit is None:
        return min_chars
    try:
        limit = int(context_limit)
    except (TypeError, ValueError):
        return min_chars

    if limit <= 8192:
        return min_chars

    scaled = int(limit * char_ratio)
    return max(min_chars, min(max_chars, scaled))


class ContextCompactor:
    SUMMARY_MARKER = "[Summary of earlier conversation:"

    """
    Manages conversational working memory to prevent context overflow.
    Preserves system instructions, root intent, condenses intermediate turns,
    and keeps recent turns verbatim.
    """

    SUMMARY_LINES = 10

    @staticmethod
    def _pinned_intermediate(intermediate: List[ChatMessage]) -> dict:
        """CARD-524: index -> message kept verbatim out of the compacted history.

        Keeps the latest user message and the latest skill_view call with its tool return.
        A pinned assistant message keeps only the skill_view call, so no call is left without a return.
        """
        pinned: dict = {}
        for idx in range(len(intermediate) - 1, -1, -1):
            if intermediate[idx].role == Role.USER:
                pinned[idx] = intermediate[idx]
                break
        for cidx in range(len(intermediate) - 1, -1, -1):
            call_msg = intermediate[cidx]
            if call_msg.role != Role.ASSISTANT:
                continue
            calls = [tc for tc in (call_msg.tool_calls or []) if tc.name == "skill_view"]
            if not calls:
                continue
            call = calls[-1]
            for ridx in range(cidx + 1, len(intermediate)):
                ret = intermediate[ridx]
                if ret.role == Role.TOOL and ret.tool_call_id == call.id:
                    pinned[cidx] = call_msg.model_copy(update={"tool_calls": [call], "content": call_msg.content or ""})
                    pinned[ridx] = ret
                    break
            if cidx in pinned:
                break
        return pinned

    @staticmethod
    def estimate_tokens(messages: List[ChatMessage]) -> int:
        """
        Rough heuristic: ~4 characters per token across content and tool call arguments.
        """
        total_chars = sum(len(m.content or "") for m in messages)
        for m in messages:
            if m.tool_calls:
                for tc in m.tool_calls:
                    total_chars += len(tc.name) + len(str(tc.arguments))
        return max(1, total_chars // 4)

    @classmethod
    def compact_with_stats(
        cls,
        messages: List[ChatMessage],
        model_name: str = "default",
        max_tokens: Optional[int] = None,
        keep_last_n_turns: int = 4,
        max_tool_chars: Optional[int] = None,
        preserve_root_intent: bool = True,
        safety_margin: float = 0.75,
        force: bool = False,
    ) -> Tuple[List[ChatMessage], CompactionMetrics]:
        """
        Compacts the message list if estimated tokens exceed the model token budget [REQ-COMPACT-001, REQ-COMPACT-003].
        When force=True, forces compaction of intermediate turns regardless of effective_max_tokens ceiling.
        """
        if not messages:
            return [], CompactionMetrics(
                original_tokens=0,
                compacted_tokens=0,
                turns_compacted=0,
                tools_truncated=0,
                compression_ratio=1.0,
                compaction_applied=False,
            )

        # Filter out UI-only proposal messages that cannot be processed by standard LLM APIs [CARD-358, REQ-SKIL-015]
        # CARD-482: chat notes (e.g. the can't-view-images notice) are UI-only too.
        messages = [m for m in messages if m.role not in (Role.SKILL_PROPOSAL, Role.NOTE)]
        if not messages:
            return [], CompactionMetrics(
                original_tokens=0,
                compacted_tokens=0,
                turns_compacted=0,
                tools_truncated=0,
                compression_ratio=1.0,
                compaction_applied=False,
            )

        original_tokens = cls.estimate_tokens(messages)


        # Determine effective budget ceiling
        if max_tokens is None:
            context_window = get_model_context_limit(model_name)
            effective_max_tokens = max(1000, int(context_window * safety_margin))
        else:
            context_window = None
            effective_max_tokens = max_tokens

        # Determine effective per-tool character limit [REQ-TOOL-BUDGET-003]
        if max_tool_chars is None:
            base_window = context_window or get_model_context_limit(model_name)
            resolved_ctx = max(base_window, effective_max_tokens)
            effective_tool_chars = resolve_max_tool_chars(resolved_ctx)
        else:
            effective_tool_chars = max(1000, int(max_tool_chars))

        # 1. Prune oversized tool outputs
        pruned_messages: List[ChatMessage] = []
        tools_truncated_count = 0

        for msg in messages:
            if msg.role == Role.TOOL and msg.content and len(msg.content) > effective_tool_chars:
                tools_truncated_count += 1
                head_chars = int(effective_tool_chars * 0.7)
                tail_chars = max(0, effective_tool_chars - head_chars)
                head = msg.content[:head_chars]
                tail = msg.content[-tail_chars:] if tail_chars > 0 else ""
                omitted = len(msg.content) - (head_chars + tail_chars)

                artifact_ref = ""
                try:
                    from pathlib import Path
                    art_dir = Path("scratch") / "tool_artifacts"
                    art_dir.mkdir(parents=True, exist_ok=True)
                    raw_id = msg.tool_call_id or "output"
                    cid = "".join(c if c.isalnum() or c in "-_" else "_" for c in raw_id)
                    art_file = art_dir / f"tool_{cid}.txt"
                    art_file.write_text(msg.content, encoding="utf-8")
                    artifact_ref = f"[Full output ({len(msg.content)} chars) saved to: {art_file.as_posix()}]\n"
                except Exception:
                    artifact_ref = ""

                truncated_content = (
                    f"{artifact_ref}{head}\n\n"
                    f"... [TRUNCATED: {omitted} characters omitted for context budget] ...\n\n"
                    f"{tail}"
                )
                pruned_messages.append(
                    ChatMessage(
                        role=msg.role,
                        content=truncated_content,
                        name=msg.name,
                        tool_call_id=msg.tool_call_id,
                    )
                )
            else:
                pruned_messages.append(msg)

        current_tokens = cls.estimate_tokens(pruned_messages)

        # If under budget and not forcing early compaction, return pruned messages
        if not force and current_tokens <= effective_max_tokens:
            return pruned_messages, CompactionMetrics(
                original_tokens=original_tokens,
                compacted_tokens=current_tokens,
                turns_compacted=0,
                tools_truncated=tools_truncated_count,
                compression_ratio=current_tokens / max(1, original_tokens),
                compaction_applied=tools_truncated_count > 0,
            )

        # 2. Extract System Prompt and Optional Root Intent [REQ-COMPACT-002]
        system_msg: Optional[ChatMessage] = None
        root_intent_msg: Optional[ChatMessage] = None
        start_idx = 0

        if pruned_messages and pruned_messages[0].role == Role.SYSTEM:
            system_msg = pruned_messages[0]
            start_idx = 1

        if preserve_root_intent and len(pruned_messages) > start_idx:
            first_user_candidate = pruned_messages[start_idx]
            if first_user_candidate.role == Role.USER:
                root_intent_msg = first_user_candidate
                start_idx += 1

        turns = pruned_messages[start_idx:]
        keep_msg_count = max(2, keep_last_n_turns * 2)

        if len(turns) <= keep_msg_count:
            return pruned_messages, CompactionMetrics(
                original_tokens=original_tokens,
                compacted_tokens=current_tokens,
                turns_compacted=0,
                tools_truncated=tools_truncated_count,
                compression_ratio=current_tokens / max(1, original_tokens),
                compaction_applied=tools_truncated_count > 0,
            )

        # 3. Partition into intermediate turns vs recent turns.
        # CARD-524: never open the recent window on a tool return whose call was compacted away.
        split = len(turns) - keep_msg_count
        while split > 0 and turns[split].role == Role.TOOL:
            split -= 1
        intermediate_turns = turns[:split]
        recent_turns = turns[split:]

        # CARD-524 keep-rule: the operator's latest message and the latest loaded skill_view
        # runbook stay verbatim even when a tool-heavy turn pushes them out of the recent window.
        pinned = cls._pinned_intermediate(intermediate_turns)

        # CARD-623: if every unpinned intermediate message is already a compaction summary, nothing to do.
        def _is_summary(m: ChatMessage) -> bool:
            return bool((m.content or "").lstrip().startswith(cls.SUMMARY_MARKER))

        unpinned = [m for idx, m in enumerate(intermediate_turns) if idx not in pinned]
        if unpinned and all(_is_summary(m) for m in unpinned):
            return pruned_messages, CompactionMetrics(
                original_tokens=original_tokens,
                compacted_tokens=current_tokens,
                turns_compacted=0,
                tools_truncated=tools_truncated_count,
                compression_ratio=current_tokens / max(1, original_tokens),
                compaction_applied=False,
            )

        # 4. Summarize unpinned runs of intermediate turns (newest lines win)
        compacted_prefix: List[ChatMessage] = []
        run: List[ChatMessage] = []
        summarized = 0

        def flush_run() -> None:
            nonlocal summarized
            if not run:
                return
            summary_lines: List[str] = []
            for m in run:
                role_label = m.role.value.capitalize()
                preview = (m.content or "")[:150].replace("\n", " ")
                summary_lines.append(f"- {role_label}: {preview}...")
            omitted = max(0, len(summary_lines) - cls.SUMMARY_LINES)
            head = f"... ({omitted} older messages omitted)\n" if omitted else ""
            summary_text = (
                "[Summary of earlier conversation:\n"
                + head
                + "\n".join(summary_lines[-cls.SUMMARY_LINES :])
                + "\n... (earlier turns compacted to preserve context budget)]"
            )
            compacted_prefix.append(ChatMessage(role=Role.ASSISTANT, content=summary_text))
            summarized += len(run)
            run.clear()

        for idx, m in enumerate(intermediate_turns):
            if idx in pinned:
                flush_run()
                compacted_prefix.append(pinned[idx])
            else:
                run.append(m)
        flush_run()

        # 5. Assemble compacted payload
        compacted: List[ChatMessage] = []
        if system_msg:
            compacted.append(system_msg)
        if root_intent_msg:
            compacted.append(root_intent_msg)
        compacted.extend(compacted_prefix)
        compacted.extend(recent_turns)

        compacted_tokens = cls.estimate_tokens(compacted)

        # CARD-623: the Compact button (force=True) only reports success when tokens actually dropped
        # (or tools were truncated). Auto over-budget compaction still applies a structural summary.
        # Re-compacting an already-summarized prefix that frees 0 tokens is "already compact".
        shrunk = compacted_tokens < original_tokens
        if force:
            applied = (summarized > 0 and shrunk) or tools_truncated_count > 0
        else:
            applied = summarized > 0 or tools_truncated_count > 0
        if not applied:
            return pruned_messages, CompactionMetrics(
                original_tokens=original_tokens,
                compacted_tokens=current_tokens,
                turns_compacted=0,
                tools_truncated=tools_truncated_count,
                compression_ratio=current_tokens / max(1, original_tokens),
                compaction_applied=False,
            )

        return compacted, CompactionMetrics(
            original_tokens=original_tokens,
            compacted_tokens=compacted_tokens,
            turns_compacted=summarized,
            tools_truncated=tools_truncated_count,
            compression_ratio=compacted_tokens / max(1, original_tokens),
            compaction_applied=True,
        )

    @classmethod
    def compact(
        cls,
        messages: List[ChatMessage],
        max_tokens: Optional[int] = None,
        model_name: str = "default",
        keep_last_n_turns: int = 4,
        max_tool_chars: Optional[int] = None,
        preserve_root_intent: bool = True,
    ) -> List[ChatMessage]:
        """
        Backwards-compatible convenience method returning compacted message list.
        """
        compacted, _ = cls.compact_with_stats(
            messages=messages,
            model_name=model_name,
            max_tokens=max_tokens,
            keep_last_n_turns=keep_last_n_turns,
            max_tool_chars=max_tool_chars,
            preserve_root_intent=preserve_root_intent,
        )
        return compacted
