/**
 * CARD-567 journey: a runaway model reply stops at a reply limit with a clear message instead of hanging.
 * Runs on the throwaway QA data against the real reasoning model (Spark); the limits are changed through
 * PUT /api/settings/reply-limits in this throwaway environment only (no model server config is touched).
 * 1) max_tokens 200: a long step-by-step ask to Architect ends with "Stopped: ... reply limit of 200 tokens" (alert and saved
 *    chat row); the chat is idle and usable.
 * 2) Limits cleared: "Reply with only the word pong" answers normally in the same chat.
 * 3) max_seconds 5 (tokens default): a long ask stops with "Stopped: ... time limit of 5 s".
 * Checks are structural (saved rows, streaming state, timing), never exact model wording.
 */
import { waitFor } from './lib/runner.mjs';
import { getJson, isStreaming, openApp, openSessionByTitle, send, trackStreams, waitReplyIdle } from './lib/app.mjs';

const LONG_ASK = 'Think very carefully, step by step, and in full detail: design a complete relational schema for a library system '
  + '(members, books, copies, loans, holds, fines, branches, staff), with every table, column, type, index and constraint, then '
  + 'explain every design decision and all trade-offs. Do not use any tools.';

const role = (m) => String((m && m.role) || '').toLowerCase();

async function rowsOf(request, base, sid) {
  const rows = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sid)}/messages`).catch(() => []);
  return Array.isArray(rows) ? rows : [];
}

async function setLimits(request, base, data) {
  const res = await request.put(`${base}/api/settings/reply-limits`, { data });
  if (!res.ok()) throw new Error(`reply-limits -> ${res.status()} ${await res.text()}`);
  return res.json();
}

export default {
  id: 'card-567-reply-limits',
  card: 'CARD-567',
  title: 'A runaway reply stops at the token or time limit with a clear message; the chat stays usable',
  allow: [],
  allowConsole: [/reply limit|time limit|Reply failed/i],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    let sid = '';
    let title = '';

    const ask = async (text, timeoutMs) => {
      const from = (await rowsOf(request, base, sid)).length;
      const n = streams.count;
      const t0 = Date.now();
      await send(page, text);
      await waitFor(() => streams.count > n, { timeoutMs: 15000 });
      await waitFor(async () => !(await isStreaming(page)) && (await rowsOf(request, base, sid)).length > from + 1, { timeoutMs, intervalMs: 1000 });
      await waitReplyIdle(page, { timeoutMs: 60000 }).catch(() => {});
      const rows = (await rowsOf(request, base, sid)).slice(from);
      const last = [...rows].reverse().find((m) => role(m) === 'assistant' && String(m.content || '').trim());
      return { seconds: (Date.now() - t0) / 1000, last: String((last && last.content) || ''), streaming: await isStreaming(page) };
    };

    // The ERROR event shows a "Reply failed: ..." alert and toast (the user-visible message); reload so the step's
    // generic error-banner check sees the saved chat row instead.
    const reopen = async () => {
      await page.reload({ waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(2500);
      await openSessionByTitle(page, title, { agentId: 'architect' }).catch(() => {});
      await page.waitForTimeout(1500);
    };

    await j.step('An Architect chat on the throwaway data; reply-limits read from settings', async () => {
      const cur = await getJson(request, `${base}/api/settings/reply-limits`);
      j.note(`defaults ${JSON.stringify(cur)}`);
      if (!(cur.max_tokens > 0 && cur.max_seconds > 0)) throw new Error('reply-limits not readable');
      title = `QA 567 ${viewport.name} ${Date.now() % 100000}`;
      const made = await request.post(`${base}/api/sessions`, { data: { agent_id: 'architect', title } });
      if (!made.ok()) throw new Error(`create session -> ${made.status()}`);
      sid = (await made.json()).id;
      await openApp(page, base);
      try {
        await openSessionByTitle(page, title, { agentId: 'architect' });
      } catch (err) {
        const active = await page.evaluate(() => localStorage.getItem('autoreiv_active_session_id'));
        if (active !== sid) throw err;
        await page.locator('#toggleSidebarBtn').click();
      }
    }, { timeoutMs: 60000 });

    await j.step('max_tokens 200: a long ask stops with the reply-limit message and the chat is idle', async () => {
      j.note(`limits ${JSON.stringify(await setLimits(request, base, { max_tokens: 200 }))}`);
      const r = await ask(LONG_ASK, 600000);
      const alert = await page.locator('.chat-stream-error').last().innerText().catch(() => '');
      j.note(`seconds ${r.seconds.toFixed(1)}; streaming ${r.streaming}; saved: ${r.last.replace(/\s+/g, ' ').slice(0, 220)}`);
      j.note(`alert: ${alert.slice(0, 200)}`);
      if (!/reply limit of 200 tokens/.test(r.last)) throw new Error('no reply-limit message saved in the chat');
      if (r.streaming) throw new Error('chat still streaming');
      await j.screenshot('token-limit-alert');
      await reopen();
      if (!(await page.getByText(/reply limit of 200 tokens/).first().isVisible().catch(() => false))) throw new Error('saved message not shown after reload');
    }, { timeoutMs: 700000 });

    await j.step('Limits cleared: the next turn in the same chat answers normally', async () => {
      const lim = await setLimits(request, base, { max_tokens: null, max_seconds: null });
      const r = await ask('Reply with only the word pong.', 600000);
      j.note(`limits ${JSON.stringify(lim)}; seconds ${r.seconds.toFixed(1)}; saved: ${r.last.replace(/\s+/g, ' ').slice(0, 120)}`);
      if (!/pong/i.test(r.last) || /Stopped:/.test(r.last)) throw new Error('normal turn did not answer');
    }, { timeoutMs: 700000 });

    await j.step('max_seconds 5: a long ask stops with the time-limit message', async () => {
      j.note(`limits ${JSON.stringify(await setLimits(request, base, { max_seconds: 5 }))}`);
      const r = await ask(LONG_ASK, 300000);
      j.note(`seconds ${r.seconds.toFixed(1)}; streaming ${r.streaming}; saved: ${r.last.replace(/\s+/g, ' ').slice(0, 220)}`);
      await setLimits(request, base, { max_tokens: null, max_seconds: null });
      if (!/time limit of 5 s/.test(r.last)) throw new Error('no time-limit message saved in the chat');
      if (r.seconds > 60) throw new Error(`took ${r.seconds.toFixed(0)} s to stop`);
      await j.screenshot('time-limit-alert');
      await reopen();
      await page.getByText(/time limit of 5 s/).last().scrollIntoViewIfNeeded().catch(() => {});
      await j.screenshot('time-limit-saved');
    }, { timeoutMs: 400000 });
  },
};
