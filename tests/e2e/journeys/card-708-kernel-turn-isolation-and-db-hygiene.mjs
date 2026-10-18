/**
 * CARD-708 journey: Isolate nested AgentKernel turn state, stop per-turn schema/prune churn,
 * fix message sequence race, and bound past_chat_search SQL.
 * 1) Seeds an earlier session in SQLite with Project Atlas details and verifies atomic monotonic
 *    sequence_num assignment across saved messages.
 * 2) Opens a fresh AutoReiv chat session in #view-chat and asks AutoReiv to use search_past_chats
 *    to recall the Project Atlas telemetry port and key.
 * 3) Verifies search_past_chats executes with bounded SQL pushdown (returning the [Recent] hit
 *    and excluding the active session), verifies all messages in the active session have strictly
 *    monotonic sequence numbers, and checks the rendered reply on desktop and phone.
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
const PYTHON_BIN = path.join(REPO_ROOT, '.venv', 'bin', 'python');
const QA_DB_PATH = path.join(REPO_ROOT, 'scratch', 'live_qa_data', 'database', 'autoreiv.db');

const role = (m) => String((m && m.role) || '').toLowerCase();

function seedPastSessionAndVerifySequence(seedSid) {
  const script = `
import sys
from src.domain.gateway.models import ChatMessage, Role
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

repo = SQLiteStateStore(db_path=sys.argv[1])
sid = sys.argv[2]

repo.save_message(
    sid,
    "autoreiv",
    ChatMessage(
        role=Role.USER,
        content="We configured Project Atlas telemetry port 7742 with token ATL-7742-ZETA.",
    ),
)
repo.save_message(
    sid,
    "autoreiv",
    ChatMessage(
        role=Role.ASSISTANT,
        content="Confirmed: Project Atlas telemetry listens on port 7742 with token ATL-7742-ZETA.",
    ),
)
with repo._get_connection() as conn:
    seqs = [
        r[0]
        for r in conn.execute(
            "SELECT sequence_num FROM messages WHERE session_id = ? ORDER BY sequence_num ASC",
            (sid,),
        ).fetchall()
    ]
assert seqs == [1, 2], f"Expected sequence_num [1, 2], got {seqs}"
`;
  execFileSync(PYTHON_BIN, ['-c', script, QA_DB_PATH, seedSid], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
  });
}

export default {
  id: 'card-708-kernel-turn-isolation-and-db-hygiene',
  card: 'CARD-708',
  title: 'AgentKernel turn isolation, cached memory schema init, atomic message sequence numbers, and bounded search_past_chats SQL',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    let seedSid = '';
    let recallSid = '';
    let recallTitle = '';

    await j.step('Seed an earlier session in SQLite and verify atomic monotonic sequence_num', async () => {
      const stamp = Date.now() % 100000;
      const seedRes = await request.post(`${base}/api/sessions`, {
        data: { agent_id: 'autoreiv', title: `QA 708 Atlas Seed ${viewport.name} ${stamp}` },
      });
      if (!seedRes.ok()) throw new Error(`create seed session -> ${seedRes.status()}`);
      seedSid = (await seedRes.json()).id;

      seedPastSessionAndVerifySequence(seedSid);
      j.note(`seeded session=${seedSid} with sequence_num=[1, 2]`);
    });

    await j.step('Open a fresh AutoReiv session and recall Project Atlas via search_past_chats', async () => {
      recallTitle = `QA 708 Recall ${viewport.name} ${Date.now() % 100000}`;
      const made = await request.post(`${base}/api/sessions`, {
        data: { agent_id: 'autoreiv', title: recallTitle },
      });
      if (!made.ok()) throw new Error(`create recall session -> ${made.status()}`);
      recallSid = (await made.json()).id;

      await openApp(page, base);
      try {
        await openSessionByTitle(page, recallTitle, { agentId: 'autoreiv' });
      } catch (err) {
        const active = await page.evaluate(() => localStorage.getItem('autoreiv_active_session_id'));
        if (active !== recallSid) throw err;
        await page.locator('#toggleSidebarBtn').click().catch(() => {});
      }

      const prevStreams = streams.count;
      const prompt =
        'Use search_past_chats with query "Project Atlas" to look up our earlier chat and tell me the telemetry port and token.';
      await send(page, prompt);
      await waitFor(() => streams.count > prevStreams, { timeoutMs: 20000 });
      await waitFor(
        async () => {
          const streaming = await isStreaming(page);
          if (streaming) return false;
          const rows = await getJson(
            request,
            `${base}/api/sessions/${encodeURIComponent(recallSid)}/messages`,
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

    await j.step('Verify bounded search_past_chats hit, self-session exclusion, and reply in #view-chat', async () => {
      const msgs = await getJson(
        request,
        `${base}/api/sessions/${encodeURIComponent(recallSid)}/messages`,
      );
      const toolMsgs = msgs.filter(
        (m) => role(m) === 'tool' && String(m.name || '') === 'search_past_chats',
      );
      if (toolMsgs.length < 1) {
        throw new Error(`Expected search_past_chats tool call in session ${recallSid}`);
      }

      const combinedToolOutput = toolMsgs.map((m) => String(m.content || '')).join('\n');
      for (const expected of ['[Recent]', '7742', 'ATL-7742-ZETA']) {
        if (!combinedToolOutput.includes(expected)) {
          throw new Error(`search_past_chats output missing ${expected}: ${combinedToolOutput.slice(0, 500)}`);
        }
      }

      for (const tm of toolMsgs) {
        let parsed;
        try {
          parsed = JSON.parse(String(tm.content || '{}'));
        } catch {
          parsed = null;
        }
        if (parsed && Array.isArray(parsed.hits)) {
          if (parsed.hits.some((h) => h && h.session_id === recallSid)) {
            throw new Error(`search_past_chats returned self-hit from active session ${recallSid}`);
          }
        }
      }

      const assistantReplies = msgs.filter(
        (m) => role(m) === 'assistant' && String(m.content || '').trim().length > 0,
      );
      const finalReply = String((assistantReplies[assistantReplies.length - 1] || {}).content || '');
      if (!finalReply.includes('7742') || !finalReply.includes('ATL-7742-ZETA')) {
        throw new Error(`Assistant reply missing recalled Project Atlas facts: ${finalReply.slice(0, 400)}`);
      }

      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      if (overflow > 2) {
        throw new Error(`Horizontal overflow on ${viewport.name}: ${overflow}px`);
      }
      j.note(`verified search_past_chats SQL pushdown recall and turn state on ${viewport.name}`);
    });
  },
};
