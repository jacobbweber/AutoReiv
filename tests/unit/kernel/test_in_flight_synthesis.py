"""
CARD-165: Turn-time Missing Capability Detection, In-flight JIT Tool Synthesis, and Turn Resumption.
[REQ-FACT-024, REQ-FACT-025, REQ-FACT-026, REQ-FACT-027]
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.orchestration.capability_detector import CapabilityDetector, CapabilityGapDetection
from src.application.orchestration.jit_synthesizer import JitToolSynthesizer, SynthesizeResult
from src.domain.gateway.models import ChatMessage, CompletionResponse, Role, ToolCall
from src.domain.kernel.models import AgentProfile, KernelEventType
from src.domain.orchestration.factory_packets import EvalPacket


class TestCapabilityDetector:
    def test_detects_missing_tool_phrases(self):
        user_prompt = "Please create a VM named ubuntu-box in Hyper-V"
        assistant_resp = "I don't have the tools to create a Hyper-V VM directly."

        detection = CapabilityDetector.detect(user_prompt=user_prompt, assistant_response=assistant_resp)
        assert detection is not None
        assert detection.detected is True
        assert "vm" in detection.missing_capability.lower() or "hyper-v" in detection.missing_capability.lower()
        assert len(detection.suggested_tool_name) > 0

    def test_ignores_ordinary_turn(self):
        user_prompt = "What is the capital of France?"
        assistant_resp = "The capital of France is Paris."

        detection = CapabilityDetector.detect(user_prompt=user_prompt, assistant_response=assistant_resp)
        assert detection is None or detection.detected is False


class TestJitToolSynthesizer:
    @pytest.mark.asyncio
    async def test_successful_synthesis_bypasses_hitl_when_all_4_stages_pass(self, tmp_path):
        agent = AgentProfile(
            id="test-agent",
            name="Test Agent",
            description="Test description",
            system_prompt="You are a test agent.",
            allow_autonomous_training=True,
            max_training_retries=2,
            allowed_tool_names=[],
        )
        gap = CapabilityGapDetection(
            detected=True,
            missing_capability="create a hyper-v vm",
            suggested_tool_name="manage_hyperv_vm",
            user_prompt="Create a VM",
            context_summary="User requested VM creation",
        )

        mock_battery = MagicMock()
        mock_battery.run_battery = AsyncMock(return_value=EvalPacket(
            passed=True,
            stage_1_functional=True,
            stage_2_safety=True,
            stage_3_idempotency=True,
            stage_4_critic=True,
            checks_executed=["stage_1_functional", "stage_2_safety", "stage_3_idempotency", "stage_4_critic"],
        ))

        mock_tool_registry = MagicMock()
        mock_state_store = MagicMock()

        synthesizer = JitToolSynthesizer(
            data_dir=str(tmp_path),
            battery_service=mock_battery,
        )

        progress_events = []
        result = await synthesizer.synthesize_and_deploy(
            agent=agent,
            gap=gap,
            tool_registry=mock_tool_registry,
            state_store=mock_state_store,
            on_progress=lambda stage, detail: progress_events.append((stage, detail)),
        )

        assert result.success is True
        assert result.tool_name == "manage_hyperv_vm"
        assert "manage_hyperv_vm" in agent.allowed_tool_names
        assert mock_tool_registry.register_tool.called
        assert any(stage == "deploying" for stage, _ in progress_events)

    @pytest.mark.asyncio
    async def test_fails_when_sandbox_battery_fails_bounded_by_max_retries(self, tmp_path):
        agent = AgentProfile(
            id="test-agent",
            name="Test Agent",
            description="Test description",
            system_prompt="You are a test agent.",
            allow_autonomous_training=True,
            max_training_retries=2,
            allowed_tool_names=[],
        )
        gap = CapabilityGapDetection(
            detected=True,
            missing_capability="untrusted action",
            suggested_tool_name="run_untrusted",
            user_prompt="Do something dangerous",
            context_summary="",
        )

        mock_battery = MagicMock()
        mock_battery.run_battery = AsyncMock(return_value=EvalPacket(
            passed=False,
            stage_1_functional=True,
            stage_2_safety=False,
            stage_3_idempotency=False,
            stage_4_critic=False,
            critic_notes="Safety violation",
        ))

        synthesizer = JitToolSynthesizer(
            data_dir=str(tmp_path),
            battery_service=mock_battery,
        )

        progress_events = []
        result = await synthesizer.synthesize_and_deploy(
            agent=agent,
            gap=gap,
            tool_registry=MagicMock(),
            state_store=MagicMock(),
            on_progress=lambda stage, detail: progress_events.append((stage, detail)),
        )

        assert result.success is False
        assert mock_battery.run_battery.call_count == 2
        assert "run_untrusted" not in agent.allowed_tool_names


class TestAgentKernelAutonomousTurn:
    @pytest.mark.asyncio
    async def test_agent_kernel_resumes_turn_after_in_flight_synthesis(self, tmp_path):
        from src.application.kernel.agent_kernel import AgentKernel
        from src.application.kernel.tool_registry import ScopedToolRegistry

        agent = AgentProfile(
            id="vm-agent",
            name="VM Agent",
            description="VM description",
            system_prompt="You are a VM agent.",
            allow_autonomous_training=True,
            max_training_retries=2,
            allowed_tool_names=[],
        )

        mock_gateway = MagicMock()
        # First call says "I don't have the tools to create a VM"
        # Second call (after resumption) calls the newly synthesized tool
        msg1 = ChatMessage(role=Role.ASSISTANT, content="I don't have the tools to create a VM directly.")
        msg2 = ChatMessage(role=Role.ASSISTANT, content="VM created successfully!", tool_calls=[
            ToolCall(id="tc-1", name="manage_vm", arguments={"action": "create", "name": "web-box"})
        ])

        mock_gateway.complete = AsyncMock(side_effect=[
            CompletionResponse(model="test-model", message=msg1),
            CompletionResponse(model="test-model", message=msg2),
            CompletionResponse(model="test-model", message=ChatMessage(role=Role.ASSISTANT, content="Done.")),
        ])

        mock_store = MagicMock()
        mock_store.get_messages.return_value = []
        mock_telemetry = MagicMock()
        tool_registry = ScopedToolRegistry()

        kernel = AgentKernel(
            gateway=mock_gateway,
            tool_registry=tool_registry,
            state_store=mock_store,
            telemetry=mock_telemetry,
            data_dir=str(tmp_path),
        )

        # Mock battery service so synthesis passes cleanly
        with patch.object(
            JitToolSynthesizer,
            "synthesize_and_deploy",
            new_callable=AsyncMock,
        ) as mock_synth:
            mock_synth.return_value = SynthesizeResult(
                success=True,
                tool_name="manage_vm",
                eval_packet=EvalPacket(passed=True),
            )
            # Add dummy handler to registry so tool execution succeeds
            tool_registry.register_tool("manage_vm", "VM tool", {}, lambda **kw: {"success": True})
            agent.allowed_tool_names.append("manage_vm")

            resp = await kernel.run_turn(
                agent=agent,
                session_id="test-session",
                user_content="Create a VM named web-box",
            )

            assert mock_synth.called
            assert resp.content == "Done."

    @pytest.mark.asyncio
    async def test_agent_kernel_logs_gap_when_auto_train_disabled(self, tmp_path):
        from src.application.kernel.agent_kernel import AgentKernel
        from src.application.kernel.tool_registry import ScopedToolRegistry

        agent = AgentProfile(
            id="vm-agent",
            name="VM Agent",
            description="VM description",
            system_prompt="You are a VM agent.",
            allow_autonomous_training=False,
            allowed_tool_names=[],
        )

        mock_gateway = MagicMock()
        msg = ChatMessage(role=Role.ASSISTANT, content="I don't have the tools to create a VM.")
        mock_gateway.complete = AsyncMock(return_value=CompletionResponse(model="test-model", message=msg))

        mock_store = MagicMock()
        mock_store.get_messages.return_value = []
        mock_telemetry = MagicMock()
        tool_registry = ScopedToolRegistry()

        kernel = AgentKernel(
            gateway=mock_gateway,
            tool_registry=tool_registry,
            state_store=mock_store,
            telemetry=mock_telemetry,
            data_dir=str(tmp_path),
        )

        mock_create_gap = MagicMock()
        kernel.capability_gap_repo.create_gap = mock_create_gap

        resp = await kernel.run_turn(
            agent=agent,
            session_id="test-session",
            user_content="Create a VM",
        )

        assert resp.content == "I don't have the tools to create a VM."
        assert mock_create_gap.called

    @pytest.mark.asyncio
    async def test_stream_turn_emits_auto_train_progress_and_resumes(self, tmp_path):
        from src.application.kernel.agent_kernel import AgentKernel
        from src.application.kernel.tool_registry import ScopedToolRegistry
        from src.domain.gateway.models import StreamChunk

        agent = AgentProfile(
            id="vm-agent",
            name="VM Agent",
            description="VM description",
            system_prompt="You are a VM agent.",
            allow_autonomous_training=True,
            max_training_retries=2,
            allowed_tool_names=[],
        )

        mock_gateway = MagicMock()

        async def stream_side_effect(req, **kw):
            # First stream yields text missing tool
            # Second stream (after resumption) yields tool call
            if not getattr(stream_side_effect, "called_once", False):
                stream_side_effect.called_once = True
                yield StreamChunk(content="I don't have the tools to create a VM.")
            else:
                yield StreamChunk(
                    tool_calls=[ToolCall(id="tc-stream", name="manage_vm", arguments={"action": "create"})]
                )

        mock_gateway.stream = stream_side_effect

        mock_store = MagicMock()
        mock_store.get_messages.return_value = []
        mock_telemetry = MagicMock()
        tool_registry = ScopedToolRegistry()

        kernel = AgentKernel(
            gateway=mock_gateway,
            tool_registry=tool_registry,
            state_store=mock_store,
            telemetry=mock_telemetry,
            data_dir=str(tmp_path),
        )

        # Mock synthesis
        with patch.object(
            JitToolSynthesizer,
            "synthesize_and_deploy",
            new_callable=AsyncMock,
        ) as mock_synth:
            async def _fake_synth(agent, gap, tool_registry, state_store, on_progress=None):
                if on_progress:
                    await on_progress("synthesizing", "Drafting...")
                    await on_progress("deploying", "Deploying...")
                agent.allowed_tool_names.append("manage_vm")
                tool_registry.register_tool("manage_vm", "VM tool", {}, lambda **kw: {"success": True})
                return SynthesizeResult(success=True, tool_name="manage_vm", eval_packet=EvalPacket(passed=True))

            mock_synth.side_effect = _fake_synth

            events = []
            async for ev in kernel.stream_turn(
                agent=agent,
                session_id="test-session",
                user_content="Create a VM",
            ):
                events.append(ev)

            progress_events = [e for e in events if e.event_type == KernelEventType.AUTO_TRAIN_PROGRESS]
            assert len(progress_events) >= 2
            stages = [e.auto_train["stage"] for e in progress_events]
            assert "synthesizing" in stages
            assert "deploying" in stages
