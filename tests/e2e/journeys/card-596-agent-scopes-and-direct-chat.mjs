/**
 * CARD-596 journey: Agent scopes and direct chat.
 * 1) A study request to AutoReiv directs the user to open Tutor in Chat (no handoff, no wiki search loop).
 * 2) The same study request to Tutor starts the study review.
 * 3) A code request to AutoReiv directs the user to open Developer in Chat (no handoff).
 * 4) A request nobody covers offers Ask Developer.
 */
import { waitFor } from './lib/runner.mjs';
import { getJson, openApp, openSessionByTitle, send, trackStreams, waitReplyIdle } from './lib/app.mjs';

const STUDY_ASK = 'Start my flashcard due review for today: show me the first card that is due and grade my answer.';
const CODE_ASK = 'Inspect the AutoReiv git repository and write code to implement a bugfix in the codebase.';
const NOBODY_ASK = 'Book me a real flight from Boston to Denver next Friday and pay for it with my credit card.';
const REFUSAL_RE = /outside (of )?my authorized domain|not authorized to|\brefuse/i;

async function newChat(request, base, agentId, title) {
  const res = await request.post(`${base}/api/sessions`, { data: { agent_id: agentId, title } });
  if (!res.ok()) throw new Error(`create session -> ${res.status()}`);
  return (await res.json()).id;
}

async function messages(request, base, sid) {
  const rows = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sid)}/messages`);
  return Array.isArray(rows) ? rows : [];
}

const role = (m) => String((m && m.role) || '').toLowerCase();

export default {
  id: 'card-596-agent-scopes-and-direct-chat',
  card: 'CARD-596',
  title: 'Agent scopes and direct chat: AutoReiv directs to Tutor/Developer; Tutor handles study directly',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    const stamp = `${viewport.name} ${Date.now() % 100000}`;

    await j.step('Study request to AutoReiv: directs to Tutor in Chat with no handoff or search loop', async () => {
      const title = `QA 596 study-auto ${stamp}`;
      const sid = await newChat(request, base, 'autoreiv', title);
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
      j.note(`handoffs: ${handoffs.length}; lookups: ${lookups}; wiki tools: ${wikiSearches}; reply: ${last.slice(0, 160).replace(/\s+/g, ' ')}`);
      if (handoffs.length > 0) throw new Error('AutoReiv executed handoff_to_agent tool');
      if (wikiSearches > 0) throw new Error('AutoReiv executed wiki searches instead of directing to Tutor');
      if (!/tutor/i.test(last)) throw new Error('reply did not name Tutor');
      if (REFUSAL_RE.test(last)) throw new Error(`reply contains refusal wording: ${last.slice(0, 160)}`);
    }, { timeoutMs: 430000 });

    await j.step('Study request to Tutor: Tutor executes study turn directly', async () => {
      const title = `QA 596 study-tutor ${stamp}`;
      const sid = await newChat(request, base, 'tutor', title);
      await openApp(page, base);
      await openSessionByTitle(page, title, { agentId: 'tutor' });
      const n = streams.count;
      await send(page, STUDY_ASK);
      await waitFor(() => streams.count > n, { timeoutMs: 15000 });
      await waitReplyIdle(page, { timeoutMs: 400000 });
      const rows = await messages(request, base, sid);
      const replies = rows.filter((m) => role(m) === 'assistant').map((m) => String(m.content || ''));
      const last = replies[replies.length - 1] || '';
      j.note(`tutor reply: ${last.slice(0, 160).replace(/\s+/g, ' ')}`);
      if (REFUSAL_RE.test(last)) throw new Error(`Tutor refused: ${last.slice(0, 160)}`);
      if (!last.trim()) throw new Error('Tutor produced empty reply');
    }, { timeoutMs: 430000 });

    await j.step('Code request to AutoReiv: directs to Developer in Chat with no handoff', async () => {
      const title = `QA 596 code-auto ${stamp}`;
      const sid = await newChat(request, base, 'autoreiv', title);
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
      j.note(`handoffs: ${handoffs.length}; reply: ${last.slice(0, 160).replace(/\s+/g, ' ')}`);
      if (handoffs.length > 0) throw new Error('AutoReiv executed handoff_to_agent tool');
      if (!/developer/i.test(last)) throw new Error('reply did not name Developer');
    }, { timeoutMs: 430000 });

    await j.step('Request nobody covers: says so and offers Ask Developer button', async () => {
      const title = `QA 596 nobody ${stamp}`;
      const sid = await newChat(request, base, 'autoreiv', title);
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
      const btn = page.locator('.msg-ask-developer-btn').last();
      const shown = await waitFor(() => btn.isVisible().catch(() => false), { timeoutMs: 10000 });
      if (!shown) throw new Error('no Ask Developer button on the reply');
      await btn.scrollIntoViewIfNeeded();
    }, { timeoutMs: 330000 });
  },
};
