"""
Agent Kernel ReAct Loop & Event Streamer [REQ-KERNEL-003, REQ-KERNEL-006].
"""

import json
import logging
import time
from typing import AsyncIterator, List, Optional

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.kernel.context_compactor import ContextCompactor
from src.application.kernel.cycle_detector import CycleDetector
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    Role,
    ToolCall,
)
from src.domain.kernel.models import (
    AgentProfile,
    KernelEvent,
    KernelEventType,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

logger = logging.getLogger(__name__)


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
    ):
        self.gateway = gateway
        self.tool_registry = tool_registry
        self.state_store = state_store
        self.telemetry = telemetry

    def _resolve_model(self, agent: AgentProfile) -> str:
        if agent.model and agent.model != "default":
            return agent.model
        if self.gateway.default_provider_id:
            return f"{self.gateway.default_provider_id}/default"
        return "default"

    async def run_turn(
        self,
        agent: AgentProfile,
        session_id: str,
        user_content: Optional[str] = None,
    ) -> ChatMessage:
        """
        Execute a full synchronous/batched ReAct agent turn with tool execution.
        """
        if user_content:
            user_msg = ChatMessage(role=Role.USER, content=user_content)
            self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=user_msg)

        history = self.state_store.get_messages(session_id=session_id)
        system_msg = ChatMessage(role=Role.SYSTEM, content=agent.get_effective_system_prompt())
        allowed_tools = self.tool_registry.get_tools_for_agent(agent)
        model_name = self._resolve_model(agent)

        cycle_detector = CycleDetector(max_repeats=3)

        for turn_idx in range(agent.max_turns):
            turn_start = time.perf_counter()
            compacted_messages = ContextCompactor.compact([system_msg] + history, max_tokens=4000, keep_last_n_turns=4)
            req = CompletionRequest(
                model=model_name,
                messages=compacted_messages,
                tools=allowed_tools or None,
            )

            try:
                resp = await self.gateway.complete(req)
                turn_dur_ms = (time.perf_counter() - turn_start) * 1000

                prompt_tokens = resp.usage.get("prompt_tokens", 0) if resp.usage else 0
                comp_tokens = resp.usage.get("completion_tokens", 0) if resp.usage else 0

                self.telemetry.record_turn_span(
                    agent_id=agent.id,
                    session_id=session_id,
                    model=resp.model,
                    duration_ms=turn_dur_ms,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=comp_tokens,
                    success=True,
                )
            except Exception as e:
                turn_dur_ms = (time.perf_counter() - turn_start) * 1000
                self.telemetry.record_turn_span(
                    agent_id=agent.id,
                    session_id=session_id,
                    model=model_name,
                    duration_ms=turn_dur_ms,
                    success=False,
                    error_message=str(e),
                )
                raise

            assistant_msg = resp.message

            # If no tool calls, turn is complete
            if not assistant_msg.tool_calls:
                self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=assistant_msg)
                return assistant_msg

            # Cycle detection
            if cycle_detector.record_and_check(assistant_msg.tool_calls):
                cycle_msg = ChatMessage(
                    role=Role.ASSISTANT,
                    content="Execution terminated: Detected repetitive cycle calling tools.",
                )
                self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=cycle_msg)
                return cycle_msg

            # Handle tool calls
            self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=assistant_msg)
            history.append(assistant_msg)

            for tc in assistant_msg.tool_calls:
                # Execute tool via ScopedToolRegistry
                tool_res = await self.tool_registry.execute(tc, agent)
                self.telemetry.record_tool_span(
                    agent_id=agent.id,
                    session_id=session_id,
                    tool_name=tc.name,
                    duration_ms=tool_res.duration_ms,
                    success=tool_res.success,
                    error_message=tool_res.error,
                )

                if tool_res.success:
                    tool_content = json.dumps(tool_res.output) if isinstance(tool_res.output, (dict, list)) else str(tool_res.output)
                else:
                    tool_content = tool_res.error or "Tool execution error"

                tool_msg = ChatMessage(
                    role=Role.TOOL,
                    content=tool_content,
                    name=tc.name,
                    tool_call_id=tc.id,
                )
                self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=tool_msg)
                history.append(tool_msg)

        limit_msg = ChatMessage(
            role=Role.ASSISTANT,
            content=f"Execution terminated: Max turn budget of {agent.max_turns} reached.",
        )
        self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=limit_msg)
        return limit_msg

    async def stream_turn(
        self,
        agent: AgentProfile,
        session_id: str,
        user_content: Optional[str] = None,
    ) -> AsyncIterator[KernelEvent]:
        """
        Execute an asynchronous streaming agent turn with live token and tool lifecycle events.
        """
        if user_content:
            user_msg = ChatMessage(role=Role.USER, content=user_content)
            self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=user_msg)

        history = self.state_store.get_messages(session_id=session_id)
        system_msg = ChatMessage(role=Role.SYSTEM, content=agent.get_effective_system_prompt())
        allowed_tools = self.tool_registry.get_tools_for_agent(agent)
        model_name = self._resolve_model(agent)
        cycle_detector = CycleDetector(max_repeats=3)

        for turn_idx in range(agent.max_turns):
            compacted_messages = ContextCompactor.compact([system_msg] + history, max_tokens=4000, keep_last_n_turns=4)
            req = CompletionRequest(
                model=model_name,
                messages=compacted_messages,
                tools=allowed_tools or None,
                stream=True,
            )

            accumulated_content = []
            accumulated_reasoning = []
            collected_tool_calls: List[ToolCall] = []

            async for chunk in self.gateway.stream(req, demux_reasoning=True):
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

            full_content = "".join(accumulated_content)

            # If no tool calls returned, stream is complete
            if not collected_tool_calls:
                assistant_msg = ChatMessage(role=Role.ASSISTANT, content=full_content)
                self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=assistant_msg)
                yield KernelEvent(event_type=KernelEventType.TURN_END, content=full_content, is_finished=True)
                return

            # Cycle detection
            if cycle_detector.record_and_check(collected_tool_calls):
                cycle_msg = ChatMessage(
                    role=Role.ASSISTANT,
                    content="Execution terminated: Detected repetitive cycle calling tools.",
                )
                self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=cycle_msg)
                yield KernelEvent(event_type=KernelEventType.TURN_END, content=cycle_msg.content, is_finished=True)
                return

            # Save assistant message with tool calls
            assistant_msg = ChatMessage(
                role=Role.ASSISTANT,
                content=full_content,
                tool_calls=collected_tool_calls,
            )
            self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=assistant_msg)
            history.append(assistant_msg)

            # Execute tool calls
            for tc in collected_tool_calls:
                yield KernelEvent(
                    event_type=KernelEventType.TOOL_START,
                    tool_call={"id": tc.id, "name": tc.name, "arguments": tc.arguments},
                )

                tool_res = await self.tool_registry.execute(tc, agent)
                self.telemetry.record_tool_span(
                    agent_id=agent.id,
                    session_id=session_id,
                    tool_name=tc.name,
                    duration_ms=tool_res.duration_ms,
                    success=tool_res.success,
                    error_message=tool_res.error,
                )

                yield KernelEvent(
                    event_type=KernelEventType.TOOL_END,
                    tool_result=tool_res,
                )

                if tool_res.success:
                    tool_content = json.dumps(tool_res.output) if isinstance(tool_res.output, (dict, list)) else str(tool_res.output)
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

        # If turn limit reached
        limit_msg = ChatMessage(
            role=Role.ASSISTANT,
            content=f"Execution terminated: Max turn budget of {agent.max_turns} reached.",
        )
        self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=limit_msg)
        yield KernelEvent(
            event_type=KernelEventType.TURN_END,
            content=limit_msg.content,
            is_finished=True,
        )
