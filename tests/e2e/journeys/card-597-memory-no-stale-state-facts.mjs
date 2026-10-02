/**
 * CARD-597 journey: Memory does not save short-lived state, drop newest-15 fallback.
 * Tutor due review prompt is run twice in one env across two chats.
 * Turn 1: checks the live due queue with tools (education_due_review_list / education_mastery_due).
 * Turn 2 (new chat in the same environment): checks live due queue with tools, does not answer from memory.
 */
import { waitFor } from './lib/runner.mjs';
import { getJson, openApp, openSessionByTitle, send, trackStreams, waitReplyIdle } from './lib/app.mjs';

const DUE_ASK = 'Start my flashcard due review for today: show me the first card that is due, or tell me if nothing is due.';
const BLOCKED_RE = /tool_policy_blocked|unknown tool|not an allowed tool|is not available/i;
const WANTED_TOOLS = ['education_due_review_list', 'education_mastery_due'];

async function newChat(request, base, agentId, title) {
  const res = await request.post(`${base}/api/sessions`, { data: { agent_id: agentId, title } });
  if (!res.ok()) throw new Error(`create session -> ${res.status()}`);
  return (await res.json()).id;
}

async function toolRows(request, base, sid) {
  const rows = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sid)}/messages`);
  return (Array.isArray(rows) ? rows : []).filter((m) => String((m && m.role) || '').toLowerCase() === 'tool');
}

export default {
  id: 'card-597-memory-no-stale-state-facts',
  card: 'CARD-597',
  title: 'Memory does not save short-lived state; Tutor checks live queue twice across sessions without answering from stale memory',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    const stamp = `${viewport.name} ${Date.now() % 100000}`;

    await j.step('Turn 1: Tutor due review checks live queue with tools', async () => {
      await openApp(page, base);
      await request.post(`${base}/api/settings/matrix`, {
        data: {
          default_context_window: 262144,
          model_context_windows: { 'nemotron-3.5-lightning': 262144, 'qwen3.8:latest': 262144 },
        },
      });
      await request.put(`${base}/api/settings/reply-limits`, {
        data: { max_tokens: 32768, max_seconds: 7200 },
      });

      const title = `QA 597 tutor-turn1 ${stamp}`;
      const sid = await newChat(request, base, 'tutor', title);
      await openSessionByTitle(page, title, { agentId: 'tutor' });
      const n = streams.count;
      await send(page, DUE_ASK);
      await waitFor(() => streams.count > n, { timeoutMs: 15000 });
      await waitReplyIdle(page, { timeoutMs: 400000 });

      const tools = await toolRows(request, base, sid);
      const names = tools.map((m) => String(m.name || '?'));
      j.note(`turn 1 tools: ${names.join(', ') || 'none'}`);
      const blocked = tools.filter((m) => BLOCKED_RE.test(String(m.content || '')));
      if (blocked.length) throw new Error(`Tutor tool was blocked: ${String(blocked[0].name)}`);
      if (!names.some((nm) => WANTED_TOOLS.includes(nm))) {
        throw new Error(`Turn 1: Tutor called none of ${WANTED_TOOLS.join(' / ')} (called: ${names.join(', ') || 'none'})`);
      }
    }, { timeoutMs: 430000 });

    // Wait 5 seconds to ensure post-turn background memory extraction has completed
    await page.waitForTimeout(5000);

    await j.step('Turn 2: In a new chat, Tutor again checks live queue with tools and does not answer from memory', async () => {
      const title = `QA 597 tutor-turn2 ${stamp}`;
      const sid = await newChat(request, base, 'tutor', title);
      await openApp(page, base);
      await openSessionByTitle(page, title, { agentId: 'tutor' });
      const n = streams.count;
      await send(page, DUE_ASK);
      await waitFor(() => streams.count > n, { timeoutMs: 15000 });
      await waitReplyIdle(page, { timeoutMs: 400000 });

      const tools = await toolRows(request, base, sid);
      const names = tools.map((m) => String(m.name || '?'));
      j.note(`turn 2 tools: ${names.join(', ') || 'none'}`);
      const blocked = tools.filter((m) => BLOCKED_RE.test(String(m.content || '')));
      if (blocked.length) throw new Error(`Tutor tool was blocked: ${String(blocked[0].name)}`);
      if (!names.some((nm) => WANTED_TOOLS.includes(nm))) {
        throw new Error(`Turn 2: Tutor answered from memory without calling due ledger tools (called: ${names.join(', ') || 'none'})`);
      }
    }, { timeoutMs: 430000 });
  },
};
