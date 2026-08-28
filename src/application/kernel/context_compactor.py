"""
Context Window Compactor [REQ-MEMORY-001, REQ-MEMORY-002, REQ-COMPACT-001 - REQ-COMPACT-004].
Implements sliding-window truncation, large tool output pruning, root intent preservation,
and model-aware dynamic token budget management.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from src.domain.gateway.models import ChatMessage, Role


@dataclass
class CompactionMetrics:
    original_tokens: int
    compacted_tokens: int
    turns_compacted: int
    tools_truncated: int
    compression_ratio: float
    compaction_applied: bool


def get_model_context_limit(
    model_name: str,
    default_override: Optional[int] = None,
    model_overrides: Optional[dict] = None,
) -> int:
    """
    Returns context limit in tokens [REQ-COMPACT-001].
    Settings overrides win, then explicit size tags, then family guesses.
    """
    raw = (model_name or "").strip()
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
    if default_override:
        try:
            parsed = int(default_override)
        except (TypeError, ValueError):
            parsed = 0
        if parsed > 0:
            return parsed
    if not name or name == "default":
        return 8192

    if "1m" in name or "gemini-1.5" in name or "gemini-2.0" in name:
        return 1000000
    if "256k" in name or "262k" in name or "262144" in name:
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
    if "4k" in name:
        return 4096

    # Default conservative baseline for local 8k models (e.g. llama3.2, phi4, gemma2)
    return 8192


class ContextCompactor:
    """
    Manages conversational working memory to prevent context overflow.
    Preserves system instructions, root intent, condenses intermediate turns,
    and keeps recent turns verbatim.
    """

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
        max_tool_chars: int = 8000,
        preserve_root_intent: bool = True,
        safety_margin: float = 0.75,
    ) -> Tuple[List[ChatMessage], CompactionMetrics]:
        """
        Compacts the message list if estimated tokens exceed the model token budget [REQ-COMPACT-001, REQ-COMPACT-003].
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

        original_tokens = cls.estimate_tokens(messages)

        # Determine effective budget ceiling
        if max_tokens is None:
            context_window = get_model_context_limit(model_name)
            effective_max_tokens = max(1000, int(context_window * safety_margin))
        else:
            effective_max_tokens = max_tokens

        # 1. Prune oversized tool outputs
        pruned_messages: List[ChatMessage] = []
        tools_truncated_count = 0

        for msg in messages:
            if msg.role == Role.TOOL and msg.content and len(msg.content) > max_tool_chars:
                tools_truncated_count += 1
                truncated_content = (
                    msg.content[:max_tool_chars]
                    + f"\n\n... [TRUNCATED: {len(msg.content) - max_tool_chars} characters omitted for context budget] ..."
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

        # If under budget, return pruned messages
        if current_tokens <= effective_max_tokens:
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

        # 3. Partition into intermediate turns vs recent turns
        intermediate_turns = turns[:-keep_msg_count]
        recent_turns = turns[-keep_msg_count:]

        # 4. Summarize intermediate turns
        summary_lines: List[str] = []
        for m in intermediate_turns:
            role_label = m.role.value.capitalize()
            preview = (m.content or "")[:150].replace("\n", " ")
            summary_lines.append(f"- {role_label}: {preview}...")

        summary_text = (
            "[Summary of earlier conversation:\n"
            + "\n".join(summary_lines[:8])
            + "\n... (earlier turns compacted to preserve context budget)]"
        )
        summary_msg = ChatMessage(role=Role.ASSISTANT, content=summary_text)

        # 5. Assemble compacted payload
        compacted: List[ChatMessage] = []
        if system_msg:
            compacted.append(system_msg)
        if root_intent_msg:
            compacted.append(root_intent_msg)
        compacted.append(summary_msg)
        compacted.extend(recent_turns)

        compacted_tokens = cls.estimate_tokens(compacted)

        return compacted, CompactionMetrics(
            original_tokens=original_tokens,
            compacted_tokens=compacted_tokens,
            turns_compacted=len(intermediate_turns),
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
        max_tool_chars: int = 8000,
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
