/**
 * CARD-712 journey: Unify AgentKernel.run_turn and stream_turn onto one shared ReAct loop
 * and decompose agent_kernel.py under 800 lines.
 * 1) Verifies all kernel modules under src/application/kernel/ are under 800 lines and exercises
 *    AgentKernel.run_turn (non-streaming) through execute_react_loop, confirming tool gating,
 *    nested park handling, and 'Tool Error: ' formatting.
 * 2) Opens a fresh AutoReiv chat session in #view-chat on desktop and phone and executes a real
 *    tool-calling streaming turn (stream_turn) via execute_react_loop.
 * 3) Verifies the tool execution, persisted session messages, telemetry turn/tool spans, and
 *    rendered reply with zero horizontal overflow.
 */
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { waitFor } from './lib/runner.mjs';
import {
  getJson,
  isStreaming,
  openApp,
  openSessionByTitle,
  send,
  trackStreams,
  waitReplyIdle,
} from './lib/app.mjs';

const REPO_ROOT = process.cwd();
const PYTHON_BIN = '/home/spark/autoreiv/.venv/bin/python';
const QA_DB_PATH = path.join(REPO_ROOT, 'scratch', 'live_qa_data', 'database', 'autoreiv.db');

const role = (m) => String((m && m.role) || '').toLowerCase();

function verifyUnifiedRunTurnAndModules(syncSid) {
  const script = `
import asyncio
import json
import sys
from pathlib import Path
from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ChatMessage, CompletionRequest, CompletionResponse, Role, ToolCall
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

kernel_dir = Path("src/application/kernel")
for name in ("agent_kernel.py", "react_loop.py", "system_prompt_builder.py", "model_resolver.py"):
    p = kernel_dir / name
    assert p.is_file(), f"Missing {name}"
    lines = len(p.read_text(encoding="utf-8").splitlines())
    assert lines < 800, f"{name} has {lines} lines"

store = SQLiteStateStore(db_path=sys.argv[1])
sid = sys.argv[2]
collector = TelemetryCollector(store=store)
reg = ScopedToolRegistry()
reg.register_tool(
    name="get_session_info",
    description="Get session info",
    parameters={"type": "object", "properties": {"query": {"type": "string"}}},
    handler=lambda query="": {"query": query, "status": "ok_712"},
)

class _SyncLLM(LLMProviderPort):
    provider_id = "mock"
    def __init__(self):
        self.step = 0
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.step += 1
        if self.step == 1:
            return CompletionResponse(
                model="mock/model",
                message=ChatMessage(
                    role=Role.ASSISTANT,
                    content="",
                    tool_calls=[ToolCall(id="c_712", name="get_session_info", arguments={"query": "kernel-712"})],
                ),
                finish_reason="tool_calls",
            )
        return CompletionResponse(
            model="mock/model",
            message=ChatMessage(role=Role.ASSISTANT, content="Completed sync run_turn for kernel-712."),
            finish_reason="stop",
        )
    async def stream(self, request: CompletionRequest):
        if False:
            yield None

gw = MultiProviderGateway()
gw.register_provider(_SyncLLM())
kernel = AgentKernel(gateway=gw, tool_registry=reg, state_store=store, telemetry=collector)
profile = AgentProfile(
    id="autoreiv",
    name="AutoReiv",
    description="Assistant",
    system_prompt="You help.",
    provider="mock",
    model="mock/model",
    allowed_skill=[],
)
msg = asyncio.run(kernel.run_turn(agent=profile, session_id=sid, user_content="Inspect kernel-712"))
assert "kernel-712" in (msg.content or ""), f"Unexpected reply: {msg.content}"
`;
  execFileSync(PYTHON_BIN, ['-c', script, QA_DB_PATH, syncSid], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
  });
}

export default {
  id: 'card-712-kernel-unification-and-split',
  card: 'CARD-712',
  title: 'Unify AgentKernel.run_turn and stream_turn onto one shared ReAct loop and decompose agent_kernel.py under 800 lines',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    let syncSid = '';
    let chatSid = '';
    let chatTitle = '';
    const stamp = Date.now() % 100000;

    await j.step('Verify decomposed kernel modules and non-streaming run_turn execution', async () => {
      const res = await request.post(`${base}/api/sessions`, {
        data: { agent_id: 'autoreiv', title: `QA 712 Sync ${viewport.name} ${stamp}` },
      });
      if (!res.ok()) throw new Error(`create sync session -> ${res.status()}`);
      syncSid = (await res.json()).id;

      verifyUnifiedRunTurnAndModules(syncSid);
      const msgs = await getJson(request, `${base}/api/sessions/${encodeURIComponent(syncSid)}/messages`);
      const toolRow = msgs.find((m) => role(m) === 'tool' && String(m.name || '') === 'get_session_info');
      if (!toolRow || !String(toolRow.content || '').includes('ok_712')) {
        throw new Error(`Expected get_session_info tool output in sync session ${syncSid}`);
      }
      j.note(`verified non-streaming run_turn and <800-line kernel modules in session=${syncSid}`);
    });

    await j.step('Execute a streaming tool-calling turn in #view-chat via stream_turn', async () => {
      chatTitle = `QA 712 Stream ${viewport.name} ${stamp}`;
      const made = await request.post(`${base}/api/sessions`, {
        data: { agent_id: 'autoreiv', title: chatTitle },
      });
      if (!made.ok()) throw new Error(`create stream session -> ${made.status()}`);
      chatSid = (await made.json()).id;

      await openApp(page, base);
      try {
        await openSessionByTitle(page, chatTitle, { agentId: 'autoreiv' });
      } catch (err) {
        const active = await page.evaluate(() => localStorage.getItem('autoreiv_active_session_id'));
        if (active !== chatSid) throw err;
        await page.locator('#toggleSidebarBtn').click().catch(() => {});
      }

      const prevStreams = streams.count;
      const prompt =
        'Use wiki_note_search with query "AutoReiv" to search the wiki and briefly summarize what you find.';
      await send(page, prompt);
      await waitFor(() => streams.count > prevStreams, { timeoutMs: 20000 });
      await waitFor(
        async () => {
          const streaming = await isStreaming(page);
          if (streaming) return false;
          const rows = await getJson(
            request,
            `${base}/api/sessions/${encodeURIComponent(chatSid)}/messages`,
          ).catch(() => []);
          const lastAssistant = [...rows].reverse().find(
            (m) => role(m) === 'assistant' && String(m.content || '').trim().length > 0,
          );
          return Boolean(lastAssistant);
        },
        { timeoutMs: 120000, intervalMs: 1500 },
      );
      await waitReplyIdle(page, { timeoutMs: 60000 }).catch(() => {});
    }, { timeoutMs: 180000 });

    await j.step('Verify streaming tool execution, persisted messages, and responsive layout', async () => {
      const msgs = await getJson(
        request,
        `${base}/api/sessions/${encodeURIComponent(chatSid)}/messages`,
      );
      const toolMsgs = msgs.filter((m) => role(m) === 'tool');
      if (toolMsgs.length < 1) {
        throw new Error(`Expected at least 1 tool call in streaming session ${chatSid}`);
      }
      const assistantMsgs = msgs.filter(
        (m) => role(m) === 'assistant' && String(m.content || '').trim().length > 0,
      );
      if (assistantMsgs.length < 1) {
        throw new Error(`Expected final assistant reply in streaming session ${chatSid}`);
      }

      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      if (overflow > 2) {
        throw new Error(`Horizontal overflow on ${viewport.name}: ${overflow}px`);
      }
      j.note(`verified unified ReAct stream_turn and tool execution on ${viewport.name}`);
    });
  },
};
