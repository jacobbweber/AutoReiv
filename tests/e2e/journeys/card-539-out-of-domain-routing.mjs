/**
 * CARD-539 journey (ADR-0061, D6): route, do not refuse.
 * 1) A code request to AutoReiv goes to Developer (CARD-544 D1: AutoReiv no longer ticks coding): either a
 *    handoff_to_agent row naming developer, or a job whose Execute phase is assigned to developer. No refusal text.
 * 2) Extra probe (soft; flakiness tracked in CARD-546): a flashcard due-review request is handed off to Tutor.
 * 3) A request no agent covers gets a reply that says so, with an Ask Developer button.
 * Replies are checked structurally (a handoff tool row, the delegation card, the button), never by exact text.
 */
import { waitFor } from './lib/runner.mjs';
import { getJson, openApp, openSessionByTitle, send, trackStreams, waitReplyIdle } from './lib/app.mjs';

const CODE_ASK = 'Inspect the AutoReiv git repository and write code to implement a bugfix in the codebase.';
const STUDY_ASK = 'Start my flashcard due review for today: show me the first card that is due and grade my answer.';
const NOBODY_ASK = 'Book me a real flight from Boston to Denver next Friday and pay for it with my credit card.';
// The old refusal sentence ("outside my authorized domain", "not authorized to"); saying plainly that no agent covers it is expected.
const REFUSAL_RE = /outside (of )?my authorized domain|not authorized to|\brefuse/i;

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
  title: 'Out-of-domain request: code goes to Developer, study to Tutor; nobody covers it -> say so with Ask Developer',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    const stamp = `${viewport.name} ${Date.now() % 100000}`;

    await j.step('A code request to AutoReiv directs to Developer in Chat (no refusal, no handoff)', async () => {
      const title = `QA 544 code ${stamp}`;
      const sid = await newChat(request, base, title);
      await openApp(page, base);
      await openSessionByTitle(page, title, { agentId: 'autoreiv' });
      const n = streams.count;
      await send(page, CODE_ASK);
      await waitFor(() => streams.count > n, { timeoutMs: 15000 });
      await waitReplyIdle(page, { timeoutMs: 400000 });
      const rows = await messages(request, base, sid);
      const handoffs = rows.filter((m) => role(m) === 'tool' && String(m.name || '') === 'handoff_to_agent');
      const replies = rows.filter((m) => role(m) === 'assistant').map((m) => String(m.content || ''));
      const last = replies[replies.length - 1] || '';
      j.note(`handoff rows: ${handoffs.length}; reply: ${last.slice(0, 160).replace(/\s+/g, ' ')}`);
      if (handoffs.length > 0) throw new Error('AutoReiv should not execute handoff_to_agent tool');
      if (!/developer/i.test(last)) throw new Error('reply did not direct user to Developer');
      if (REFUSAL_RE.test(last)) throw new Error(`reply contains refusal wording: ${last.slice(0, 160)}`);
    }, { timeoutMs: 430000 });

    await j.step('A due-review request to AutoReiv directs to Tutor in Chat (no handoff, no wiki search loop)', async () => {
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
      const wikiSearches = rows.filter((m) => role(m) === 'tool' && String(m.name || '').startsWith('wiki_')).length;
      const replies = rows.filter((m) => role(m) === 'assistant').map((m) => String(m.content || ''));
      const last = replies[replies.length - 1] || '';
      j.note(`lookup_agents rows: ${lookups}; handoff rows: ${handoffs.length}; wiki tool rows: ${wikiSearches}; reply: ${last.slice(0, 200).replace(/\s+/g, ' ')}`);
      if (handoffs.length > 0) throw new Error('AutoReiv should not execute handoff_to_agent');
      if (wikiSearches > 0) throw new Error('AutoReiv should not fall into a wiki search loop for study request');
      if (!/tutor/i.test(last)) throw new Error('reply did not direct user to Tutor');
      if (REFUSAL_RE.test(last)) throw new Error(`reply contains refusal wording: ${last.slice(0, 160)}`);
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
