/**
 * CARD-702 journey: Provenance-badged search_past_chats across hot and cold sessions.
 * 1) Seeds an earlier active session ([Recent]) and an earlier compacted session ([Archived] via
 *    archive_links) in SQLite, both recording Project Hyperion decisions.
 * 2) Opens a new AutoReiv chat session and asks AutoReiv to use search_past_chats to recall
 *    what was decided for Project Hyperion across recent and archived chats.
 * 3) Verifies search_past_chats is called (at most 2 times per turn), returns [Recent] and [Archived]
 *    badges with local calendar dates and the deterministic stop trailer, excludes the current session,
 *    and AutoReiv answers with the recalled facts on desktop and phone.
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

function seedPastSessions(hotSid, coldSid) {
  const script = `
import sys
from src.domain.gateway.models import ChatMessage, Role
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

repo = SQLiteStateStore(db_path=sys.argv[1])
hot_sid = sys.argv[2]
cold_sid = sys.argv[3]

# 1. Hot session ([Recent])
repo.save_message(
    hot_sid,
    "autoreiv",
    ChatMessage(
        role=Role.USER,
        content="We decided Project Hyperion gateway listens on port 9481 with primary token HPR-9481-ALPHA.",
    ),
)
repo.save_message(
    hot_sid,
    "autoreiv",
    ChatMessage(
        role=Role.ASSISTANT,
        content="Recorded: Project Hyperion gateway uses port 9481 and primary token HPR-9481-ALPHA.",
    ),
)

# 2. Compacted session ([Archived] via archive_links)
repo.save_message(
    cold_sid,
    "autoreiv",
    ChatMessage(
        role=Role.USER,
        content="Project Hyperion archived cold vault key is BRL-8877-COLD on backup port 8877.",
    ),
)
repo.save_message(
    cold_sid,
    "autoreiv",
    ChatMessage(
        role=Role.ASSISTANT,
        content="Acknowledged: Project Hyperion cold vault key BRL-8877-COLD is stored.",
    ),
)
keep_msg = ChatMessage(
    role=Role.USER,
    content=" Wrapping up the migration checklist.",
)
repo.save_message(cold_sid, "autoreiv", keep_msg)
summary_msg = ChatMessage(
    role=Role.USER,
    content="[Summary of earlier conversation:\\n## Decisions\\n- Cold vault migration completed.]",
)
repo.replace_session_messages(cold_sid, "autoreiv", [summary_msg, keep_msg])
`;
  execFileSync(PYTHON_BIN, ['-c', script, QA_DB_PATH, hotSid, coldSid], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
  });
}

export default {
  id: 'card-702-provenance-badged-search-past-chats',
  card: 'CARD-702',
  title: 'Provenance-badged search_past_chats recalls [Recent] and [Archived] past chats with dates and per-turn budget',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    let hotSid = '';
    let coldSid = '';
    let recallSid = '';
    let recallTitle = '';

    await j.step('Seed an active [Recent] session and a compacted [Archived] session in SQLite', async () => {
      const stamp = Date.now() % 100000;
      const hotRes = await request.post(`${base}/api/sessions`, {
        data: { agent_id: 'autoreiv', title: `QA 702 Hyperion Recent ${viewport.name} ${stamp}` },
      });
      if (!hotRes.ok()) throw new Error(`create hot session -> ${hotRes.status()}`);
      hotSid = (await hotRes.json()).id;

      const coldRes = await request.post(`${base}/api/sessions`, {
        data: { agent_id: 'autoreiv', title: `QA 702 Hyperion Archive ${viewport.name} ${stamp}` },
      });
      if (!coldRes.ok()) throw new Error(`create cold session -> ${coldRes.status()}`);
      coldSid = (await coldRes.json()).id;

      seedPastSessions(hotSid, coldSid);

      const uncompactedCold = await getJson(
        request,
        `${base}/api/sessions/${encodeURIComponent(coldSid)}/messages`,
      );
      if (uncompactedCold.some((m) => String(m.content || '').includes('BRL-8877-COLD'))) {
        throw new Error('Expected BRL-8877-COLD message to be compacted out of active messages');
      }
      const allCold = await getJson(
        request,
        `${base}/api/sessions/${encodeURIComponent(coldSid)}/messages?include_archived=true`,
      );
      if (!allCold.some((m) => m.archived && String(m.content || '').includes('BRL-8877-COLD'))) {
        throw new Error('Expected BRL-8877-COLD message to be preserved as archived=true via archive_links');
      }
      j.note(`seeded hot=${hotSid} and compacted cold=${coldSid}`);
    });

    await j.step('Open a fresh AutoReiv session and ask to recall Project Hyperion via search_past_chats', async () => {
      recallTitle = `QA 702 Recall ${viewport.name} ${Date.now() % 100000}`;
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
        'Use search_past_chats with query "Project Hyperion" to look up our earlier chats and tell me the gateway port, primary token, and archived cold vault key, including the [Recent] and [Archived] provenance badges and session date.';
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

    await j.step('Verify search_past_chats tool output badges, date, self-exclusion, per-turn cap, and reply', async () => {
      const msgs = await getJson(
        request,
        `${base}/api/sessions/${encodeURIComponent(recallSid)}/messages`,
      );
      const toolMsgs = msgs.filter(
        (m) => role(m) === 'tool' && String(m.name || '') === 'search_past_chats',
      );
      if (toolMsgs.length < 1) {
        throw new Error(`Expected search_past_chats tool execution in session ${recallSid}`);
      }
      if (toolMsgs.length > 2) {
        throw new Error(`Expected search_past_chats per-turn budget <= 2, got ${toolMsgs.length}`);
      }

      const combinedToolOutput = toolMsgs.map((m) => String(m.content || '')).join('\n');
      for (const expected of ['[Recent]', '[Archived]', '9481', 'HPR-9481-ALPHA', 'BRL-8877-COLD', 'Answer now from what you have']) {
        if (!combinedToolOutput.includes(expected)) {
          throw new Error(`search_past_chats output missing ${expected}: ${combinedToolOutput.slice(0, 600)}`);
        }
      }
      if (!/\b202\d-\d{2}-\d{2}\b/.test(combinedToolOutput)) {
        throw new Error(`search_past_chats output missing ISO local date: ${combinedToolOutput.slice(0, 500)}`);
      }
      // Negative assertion: active session must never appear as a search hit
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
      if (!finalReply.includes('9481') || !finalReply.includes('BRL-8877-COLD')) {
        throw new Error(`Assistant reply did not include recalled facts (9481 & BRL-8877-COLD): ${finalReply.slice(0, 400)}`);
      }

      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      if (overflow > 2) {
        throw new Error(`Horizontal overflow on ${viewport.name}: ${overflow}px`);
      }
      j.note(`verified ${toolMsgs.length} search_past_chats call(s), [Recent] + [Archived] hits, and assistant recall on ${viewport.name}`);
    });
  },
};
