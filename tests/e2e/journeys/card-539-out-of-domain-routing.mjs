/**
 * CARD-539 journey (ADR-0061, D6): route, do not refuse.
 * 1) A flashcard due-review request to AutoReiv (due-review is ticked for Tutor, not AutoReiv) is handed off, with no refusal text.
 *    (AutoReiv ticks `coding`, so a code request is in its domain and is not a routing probe.)
 * 2) A request no agent covers gets a reply that says so, with an Ask Developer button.
 * Replies are checked structurally (a handoff tool row, the delegation card, the button), never by exact text.
 */
import { waitFor } from './lib/runner.mjs';
import { getJson, openApp, openSessionByTitle, send, trackStreams, waitReplyIdle } from './lib/app.mjs';

const STUDY_ASK = 'Start my flashcard due review for today: show me the first card that is due and grade my answer.';
const NOBODY_ASK = 'Book me a real flight from Boston to Denver next Friday and pay for it with my credit card.';
const REFUSAL_RE = /outside (of )?my (authorized )?domain|not authorized to|refuse/i;

async function newChat(request, base, title) {
  const res = await request.post(`${base}/api/sessions`, { data: { agent_id: 'autoreiv', title } });
  if (!res.ok()) throw new Error(`create session -> ${res.status()}`);
  return (await res.json()).id;
}

async function messages(request, base, sid) {
  const rows = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sid)}/messages`);
  return Array.isArray(rows) ? rows : [];
}

const role = (m) => String((m && m.role) || '').toLowerCase();

export default {
  id: 'card-539-out-of-domain-routing',
  card: 'CARD-539',
  title: 'Out-of-domain request: hand off to Tutor; nobody covers it -> say so with Ask Developer',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    const stamp = `${viewport.name} ${Date.now() % 100000}`;

    await j.step('A due-review request to AutoReiv is handed off to Tutor (no refusal)', async () => {
      const title = `QA 539 study ${stamp}`;
      const sid = await newChat(request, base, title);
      await openApp(page, base);
      await openSessionByTitle(page, title, { agentId: 'autoreiv' });
      const n = streams.count;
      await send(page, STUDY_ASK);
      await waitFor(() => streams.count > n, { timeoutMs: 15000 });
      await waitReplyIdle(page, { timeoutMs: 400000 });
      const rows = await messages(request, base, sid);
      const handoffs = rows.filter((m) => role(m) === 'tool' && String(m.name || '') === 'handoff_to_agent');
      const lookups = rows.filter((m) => role(m) === 'tool' && String(m.name || '') === 'lookup_agents').length;
      const replies = rows.filter((m) => role(m) === 'assistant').map((m) => String(m.content || ''));
      const last = replies[replies.length - 1] || '';
      j.note(`lookup_agents rows: ${lookups}; handoff rows: ${handoffs.length}; reply: ${last.slice(0, 200).replace(/\s+/g, ' ')}`);
      if (!handoffs.length) throw new Error('AutoReiv did not hand off the due-review request (no handoff_to_agent tool row)');
      const toTutor = handoffs.some((m) => /tutor/i.test(String(m.content || '')) || /tutor/i.test(JSON.stringify(m.tool_calls || m.arguments || '')));
      j.note(`handoff mentions tutor: ${toTutor}`);
      if (REFUSAL_RE.test(last)) throw new Error(`reply contains refusal wording: ${last.slice(0, 160)}`);
      const card = page.locator('text=Delegation to').last();
      j.note(`delegation card visible: ${await card.isVisible().catch(() => false)}`);
      await card.scrollIntoViewIfNeeded().catch(() => {});
    }, { timeoutMs: 430000 });

    await j.step('A request no agent covers: the reply says so and offers an Ask Developer button', async () => {
      const title = `QA 539 nobody ${stamp}`;
      const sid = await newChat(request, base, title);
      await openApp(page, base);
      await openSessionByTitle(page, title, { agentId: 'autoreiv' });
      const n = streams.count;
      await send(page, NOBODY_ASK);
      await waitFor(() => streams.count > n, { timeoutMs: 15000 });
      await waitReplyIdle(page, { timeoutMs: 300000 });
      const rows = await messages(request, base, sid);
      const replies = rows.filter((m) => role(m) === 'assistant').map((m) => String(m.content || ''));
      const last = replies[replies.length - 1] || '';
      j.note(`reply: ${last.slice(0, 240).replace(/\s+/g, ' ')}`);
      if (REFUSAL_RE.test(last)) throw new Error(`reply contains refusal wording: ${last.slice(0, 160)}`);
      const btn = page.locator('.msg-ask-developer-btn').last();
      const shown = await waitFor(() => btn.isVisible().catch(() => false), { timeoutMs: 10000 });
      if (!shown) throw new Error('no Ask Developer button on the reply');
      await btn.scrollIntoViewIfNeeded();
    }, { timeoutMs: 330000 });
  },
};
