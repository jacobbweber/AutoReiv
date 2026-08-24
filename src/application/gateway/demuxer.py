"""
Reasoning Tag Demuxer for splitting <think> tags from output streams [REQ-GW-006].
"""

from typing import AsyncIterator

from src.domain.gateway.models import StreamChunk


class ReasoningDemuxer:
    """
    Streaming filter that demuxes <think>...</think> reasoning traces from LLM outputs.
    Emits StreamChunk instances with separated `reasoning_content` and `content`.
    """

    THINK_OPEN = "<think>"
    THINK_CLOSE = "</think>"

    def __init__(self):
        self._inside_think = False
        self._buffer = ""

    def process_text(self, text: str) -> tuple[str, str]:
        """
        Process a slice of incoming text.
        Returns a tuple: (user_facing_content, reasoning_content).
        """
        if not text:
            return "", ""

        combined = self._buffer + text
        self._buffer = ""
        user_parts: list[str] = []
        reasoning_parts: list[str] = []

        i = 0
        n = len(combined)

        while i < n:
            if not self._inside_think:
                # Check for possible start of <think>
                open_idx = combined.find("<", i)
                if open_idx == -1:
                    user_parts.append(combined[i:])
                    break
                else:
                    # Flush text before '<'
                    if open_idx > i:
                        user_parts.append(combined[i:open_idx])
                        i = open_idx

                    # Check if remaining text could be a prefix of THINK_OPEN
                    remaining = combined[i:]
                    if self.THINK_OPEN.startswith(remaining):
                        # Potential partial tag, buffer it
                        self._buffer = remaining
                        break
                    elif remaining.startswith(self.THINK_OPEN):
                        self._inside_think = True
                        i += len(self.THINK_OPEN)
                    else:
                        # False alarm ('<' wasn't start of <think>)
                        user_parts.append(combined[i])
                        i += 1
            else:
                # Inside think mode, look for </think>
                close_idx = combined.find("<", i)
                if close_idx == -1:
                    reasoning_parts.append(combined[i:])
                    break
                else:
                    if close_idx > i:
                        reasoning_parts.append(combined[i:close_idx])
                        i = close_idx

                    remaining = combined[i:]
                    if self.THINK_CLOSE.startswith(remaining):
                        # Potential partial close tag, buffer it
                        self._buffer = remaining
                        break
                    elif remaining.startswith(self.THINK_CLOSE):
                        self._inside_think = False
                        i += len(self.THINK_CLOSE)
                    else:
                        reasoning_parts.append(combined[i])
                        i += 1

        return "".join(user_parts), "".join(reasoning_parts)

    def flush(self) -> tuple[str, str]:
        """Flush any remaining buffer at end of stream."""
        if not self._buffer:
            return "", ""
        buf = self._buffer
        self._buffer = ""
        if self._inside_think:
            return "", buf
        return buf, ""

    async def demux_stream(self, stream: AsyncIterator[StreamChunk]) -> AsyncIterator[StreamChunk]:
        """
        Wrap an incoming StreamChunk async generator and demux reasoning tokens.
        """
        async for chunk in stream:
            if chunk.content:
                user_text, reasoning_text = self.process_text(chunk.content)
                yield StreamChunk(
                    content=user_text,
                    reasoning_content=reasoning_text,
                    tool_calls=chunk.tool_calls,
                    finish_reason=chunk.finish_reason,
                    is_finished=chunk.is_finished,
                )
            elif chunk.is_finished:
                # Flush buffer before emitting finished chunk
                user_flush, reasoning_flush = self.flush()
                if user_flush or reasoning_flush:
                    yield StreamChunk(
                        content=user_flush,
                        reasoning_content=reasoning_flush,
                        tool_calls=None,
                        finish_reason=None,
                        is_finished=False,
                    )
                yield chunk
            else:
                yield chunk
