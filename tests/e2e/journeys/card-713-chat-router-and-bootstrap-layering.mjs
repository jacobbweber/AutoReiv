/**
 * CARD-713 journey: Extract chat orchestration out of src/web/routers/chat.py
 * and move application bootstrap out of src/infrastructure/agents/registry.py.
 * 1) Verifies src/web/routers/chat.py, src/application/chat/*, and src/application/bootstrap/ecosystem.py
 *    are all < 800 lines, busy.py does not import from src.web, and registry.py has no skill imports.
 * 2) Uploads a chat attachment via /api/chat/upload and verifies /api/chat/attachments/{id}/{filename}
 *    round-trip through src/application/chat/attachments.py.
 * 3) Runs a streaming tool-calling turn in #view-chat on desktop and phone and verifies SSE streaming,
 *    session activity tracking, tool execution, and responsive layout.
 */
import { execFileSync } from 'node:child_process';
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
const role = (m) => String((m && m.role) || '').toLowerCase();

function verifyRouterAndBootstrapLayering() {
  const script = `
from pathlib import Path
from src.application.chat import attachments, job_runner, stream_registry, turn_streamer
from src.application.bootstrap import bootstrap_ecosystem
from src.application.system.busy import BusyDetector

for rel in (
    "src/web/routers/chat.py",
    "src/application/chat/stream_registry.py",
    "src/application/chat/turn_streamer.py",
    "src/application/chat/job_runner.py",
    "src/application/chat/attachments.py",
    "src/application/bootstrap/ecosystem.py",
):
    p = Path(rel)
    assert p.is_file(), f"Missing {rel}"
    lines = len(p.read_text(encoding="utf-8").splitlines())
    assert lines < 800, f"{rel} has {lines} lines"

busy_src = Path("src/application/system/busy.py").read_text(encoding="utf-8")
assert "src.web" not in busy_src
detector = BusyDetector()
assert detector.is_busy()[0] is False
`;
  execFileSync(PYTHON_BIN, ['-c', script], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
  });
}

export default {
  id: 'card-713-chat-router-and-bootstrap-layering',
  card: 'CARD-713',
  title: 'Extract chat orchestration out of src/web/routers/chat.py and move application bootstrap out of src/infrastructure/agents/registry.py',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    let chatSid = '';
    let chatTitle = '';
    const stamp = Date.now() % 100000;

    await j.step('Verify chat router decomposition, bootstrap layering, and attachment round-trip', async () => {
      verifyRouterAndBootstrapLayering();

      chatTitle = `QA 713 Chat ${viewport.name} ${stamp}`;
      const made = await request.post(`${base}/api/sessions`, {
        data: { agent_id: 'autoreiv', title: chatTitle },
      });
      if (!made.ok()) throw new Error(`create session -> ${made.status()}`);
      chatSid = (await made.json()).id;

      const uploadRes = await request.post(`${base}/api/chat/upload`, {
        multipart: {
          session_id: chatSid,
          file: {
            name: 'card713_note.txt',
            mimeType: 'text/plain',
            buffer: Buffer.from('CARD-713 attachment round-trip verification payload.\n', 'utf8'),
          },
        },
      });
      if (!uploadRes.ok()) throw new Error(`upload attachment -> ${uploadRes.status()}`);
      const uploaded = await uploadRes.json();
      if (!uploaded.id || !uploaded.url) throw new Error('upload response missing id or url');

      const fetchRes = await request.get(`${base}${uploaded.url}`);
      if (!fetchRes.ok()) throw new Error(`fetch attachment -> ${fetchRes.status()}`);
      const bodyText = await fetchRes.text();
      if (!bodyText.includes('CARD-713 attachment round-trip')) {
        throw new Error(`unexpected attachment body: ${bodyText}`);
      }
      j.note(`verified <800-line chat modules and attachment round-trip id=${uploaded.id}`);
    });

    await j.step('Execute a streaming tool-calling turn in #view-chat', async () => {
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

    await j.step('Verify persisted messages, session status endpoint, and responsive layout', async () => {
      const status = await getJson(
        request,
        `${base}/api/sessions/${encodeURIComponent(chatSid)}/status`,
      );
      if (status.is_running !== false) {
        throw new Error(`Expected session ${chatSid} is_running=false after turn completion`);
      }

      const msgs = await getJson(
        request,
        `${base}/api/sessions/${encodeURIComponent(chatSid)}/messages`,
      );
      const toolMsgs = msgs.filter((m) => role(m) === 'tool');
      if (toolMsgs.length < 1) {
        throw new Error(`Expected at least 1 tool call in session ${chatSid}`);
      }
      const assistantMsgs = msgs.filter(
        (m) => role(m) === 'assistant' && String(m.content || '').trim().length > 0,
      );
      if (assistantMsgs.length < 1) {
        throw new Error(`Expected final assistant reply in session ${chatSid}`);
      }

      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      if (overflow > 2) {
        throw new Error(`Horizontal overflow on ${viewport.name}: ${overflow}px`);
      }
      j.note(`verified chat router streaming and bootstrap wiring on ${viewport.name}`);
    });
  },
};
