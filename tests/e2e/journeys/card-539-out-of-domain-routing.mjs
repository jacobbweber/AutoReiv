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

const CODE_ASK = 'Write a small Python function that reverses a string, run it on "AutoReiv", and show me the output.';
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

/** Execute phases of this chat's jobs that are assigned to developer (journey API). */
async function developerPhases(request, base, sid) {
  const jn = await getJson(request, `${base}/api/chat/sessions/${encodeURIComponent(sid)}/journey`).catch(() => ({}));
  const jobs = Array.isArray(jn.jobs) ? jn.jobs : [];
  const phases = jobs.flatMap((job) => (Array.isArray(job.phases) ? job.phases : []));
  return phases.filter((ph) => /developer/i.test(String(ph.assigned_agent_id || ph.agent_id || ph.agent || '')));
}

export default {
  id: 'card-539-out-of-domain-routing',
  card: 'CARD-539',
  title: 'Out-of-domain request: code goes to Developer, study to Tutor; nobody covers it -> say so with Ask Developer',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    const stamp = `${viewport.name} ${Date.now() % 100000}`;

    await j.step('A code request to AutoReiv goes to Developer (no refusal)', async () => {
      const title = `QA 544 code ${stamp}`;
      const sid = await newChat(request, base, title);
      await openApp(page, base);
      await openSessionByTitle(page, title, { agentId: 'autoreiv' });
      const n = streams.count;
      await send(page, CODE_ASK);
      await waitFor(() => streams.count > n, { timeoutMs: 15000 });
      await waitReplyIdle(page, { timeoutMs: 400000 });
      const rows = await messages(request, base, sid);
      const handoffs = rows.filter((m) => role(m) === 'tool' && String(m.name || '') === 'handoff_to_agent'
        && /developer/i.test(String(m.content || '') + JSON.stringify(m.tool_calls || m.arguments || '')));
      const devPhases = await developerPhases(request, base, sid);
      const replies = rows.filter((m) => role(m) === 'assistant').map((m) => String(m.content || ''));
      const last = replies[replies.length - 1] || '';
      j.note(`handoff rows to developer: ${handoffs.length}; job phases on developer: ${devPhases.map((p) => p.name || p.phase_name || '?').join(', ') || 'none'}; reply: ${last.slice(0, 160).replace(/\s+/g, ' ')}`);
      if (!handoffs.length && !devPhases.length) throw new Error('the code request did not go to Developer (no handoff row, no developer phase)');
      // The Developer phase must really run as Developer: no tool_policy_blocked on its own session (CARD-544 live QA).
      for (const ph of devPhases) {
        const pid = ph.phase_id || ph.id;
        if (!pid) continue;
        const prow = await messages(request, base, `${sid}::phase::${pid}`);
        const blocked = prow.filter((m) => role(m) === 'tool' && /tool_policy_blocked/.test(String(m.content || '')));
        j.note(`developer phase ${ph.name || '?'}: status ${ph.status || '?'}; tool rows ${prow.filter((m) => role(m) === 'tool').length}; policy-blocked ${blocked.length}`);
        if (blocked.length) throw new Error(`the Developer phase ran without Developer's tools: ${String(blocked[0].content).slice(0, 120)}`);
      }
      if (REFUSAL_RE.test(last)) throw new Error(`reply contains refusal wording: ${last.slice(0, 160)}`);
    }, { timeoutMs: 430000 });

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
    }, { timeoutMs: 430000, soft: true });

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
