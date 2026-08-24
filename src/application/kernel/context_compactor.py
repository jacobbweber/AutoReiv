"""
Context Window Compactor [REQ-MEMORY-001, REQ-MEMORY-002].
Implements sliding-window truncation, large tool output pruning, and intermediate turn summarization.
"""

from typing import List, Optional

from src.domain.gateway.models import ChatMessage, Role


class ContextCompactor:
    """
    Manages conversational working memory to prevent context overflow.
    Preserves system instructions, condenses intermediate turns, and keeps recent turns verbatim.
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
    def compact(
        cls,
        messages: List[ChatMessage],
        max_tokens: int = 4000,
        keep_last_n_turns: int = 4,
        max_tool_chars: int = 8000,
    ) -> List[ChatMessage]:
        """
        Compacts the message list if estimated tokens exceed max_tokens.
        """
        if not messages:
            return []

        # 1. Prune individual tool outputs that exceed max_tool_chars
        pruned_messages: List[ChatMessage] = []
        for msg in messages:
            if msg.role == Role.TOOL and msg.content and len(msg.content) > max_tool_chars:
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

        # 2. Check if total estimated tokens are within budget
        current_tokens = cls.estimate_tokens(pruned_messages)
        if current_tokens <= max_tokens:
            return pruned_messages

        # 3. Identify System Message vs Conversation Turns
        system_msg: Optional[ChatMessage] = None
        start_idx = 0
        if pruned_messages and pruned_messages[0].role == Role.SYSTEM:
            system_msg = pruned_messages[0]
            start_idx = 1

        turns = pruned_messages[start_idx:]
        # Each turn is roughly 2 messages (user + assistant/tool)
        keep_msg_count = max(2, keep_last_n_turns * 2)

        if len(turns) <= keep_msg_count:
            return pruned_messages

        # 4. Partition into intermediate turns vs recent turns
        intermediate_turns = turns[:-keep_msg_count]
        recent_turns = turns[-keep_msg_count:]

        # 5. Condense intermediate turns into an informative summary checkpoint
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

        # 6. Assemble compacted output: System + Summary + Recent Turns
        compacted: List[ChatMessage] = []
        if system_msg:
            compacted.append(system_msg)
        compacted.append(summary_msg)
        compacted.extend(recent_turns)

        return compacted
