/**
 * CARD-550 journey (D1, Jacob 2026-09-27): Developer ticks coding, so a code request that must read an AutoReiv
 * source file reaches Developer with the checkout repo_file_* tools allowed.
 * 1) Developer's allowed tools include repo_file_read / repo_file_list / repo_file_write / repo_file_patch.
 * 2) Asked in an AutoReiv chat, the request goes to Developer (a Developer job phase or a handoff row); the
 *    Developer phase's own chat lists repo_file_read and has no tool_policy_blocked row; no refusal wording.
 * Checks are structural (agent tool lists, phase assignment, tool rows), never exact model wording.
 */
import { waitFor } from './lib/runner.mjs';
import { HITL_CARD, getJson, openApp, openSessionByTitle, send, trackStreams, waitReplyIdle } from './lib/app.mjs';

const REPO_TOOLS = ['repo_file_read', 'repo_file_list', 'repo_file_write', 'repo_file_patch'];
const ASK = 'Read the AutoReiv source file src/application/agent_packs/allowed_tools.py and tell me in two sentences what resolve_allowed_tools returns.';
const REFUSAL_RE = /outside (of )?my (authorized )?domain|not authorized to|\brefuse/i;

const role = (m) => String((m && m.role) || '').toLowerCase();
const toolNames = (a) => new Set((a.allowed_tools || []).map((t) => String(typeof t === 'string' ? t : (t && t.name) || '')));

async function messages(request, base, sid) {
  const rows = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sid)}/messages`);
  return Array.isArray(rows) ? rows : [];
}

async function developerPhases(request, base, sid) {
  const jn = await getJson(request, `${base}/api/chat/sessions/${encodeURIComponent(sid)}/journey`).catch(() => ({}));
  const jobs = Array.isArray(jn.jobs) ? jn.jobs : [];
  return jobs.flatMap((job) => (Array.isArray(job.phases) ? job.phases : []))
    .filter((ph) => /developer/i.test(String(ph.assigned_agent_id || '')));
}

export default {
  id: 'card-550-checkout-code-to-developer',
  card: 'CARD-550',
  title: 'A code request that reads an AutoReiv source file reaches Developer with the repo_file_* tools allowed',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);

    await j.step("Developer's allowed tools include the checkout repo_file_* tools", async () => {
      const dev = await getJson(request, `${base}/api/agents/developer`);
      const names = toolNames(dev);
      const missing = REPO_TOOLS.filter((t) => !names.has(t));
      j.note(`developer skills: ${(dev.allowed_skill || []).join(', ')}; missing repo tools: ${missing.join(', ') || 'none'}`);
      if (!(dev.allowed_skill || []).includes('coding')) throw new Error('Developer does not tick coding');
      if (missing.length) throw new Error(`Developer lacks ${missing.join(', ')}`);
      const ar = await getJson(request, `${base}/api/agents/autoreiv`);
      if (REPO_TOOLS.some((t) => toolNames(ar).has(t))) throw new Error('AutoReiv still has repo_file_* tools (CARD-544)');
    }, { timeoutMs: 30000 });

    await j.step('A request to read an AutoReiv source file reaches Developer with repo_file_read allowed', async () => {
      const title = `QA 550 checkout ${viewport.name} ${Date.now() % 100000}`;
      const res = await request.post(`${base}/api/sessions`, { data: { agent_id: 'autoreiv', title } });
      if (!res.ok()) throw new Error(`create session -> ${res.status()}`);
      const sid = (await res.json()).id;
      await openApp(page, base);
      await openSessionByTitle(page, title, { agentId: 'autoreiv' });
      const n = streams.count;
      await send(page, ASK);
      await waitFor(() => streams.count > n, { timeoutMs: 15000 });
      await waitReplyIdle(page, { timeoutMs: 400000 });
      const rows = await messages(request, base, sid);
      const handoffs = rows.filter((m) => role(m) === 'tool' && String(m.name || '') === 'handoff_to_agent'
        && /developer/i.test(String(m.content || ''))).length;
      const phases = await developerPhases(request, base, sid);
      const last = rows.filter((m) => role(m) === 'assistant').map((m) => String(m.content || '')).filter(Boolean).pop() || '';
      j.note(`handoffs to developer ${handoffs}; developer phases: ${phases.map((p) => `${p.name}:${p.status}`).join(', ') || 'none'}; approval cards: ${await page.locator(HITL_CARD).count()}; reply: ${last.slice(0, 160).replace(/\s+/g, ' ')}`);
      if (REFUSAL_RE.test(last)) throw new Error(`reply contains refusal wording: ${last.slice(0, 160)}`);
      if (!handoffs && !phases.length) throw new Error('the request did not reach Developer (no handoff row, no developer phase)');
      for (const ph of phases) {
        const psid = `${sid}::phase::${ph.id}`;
        const ctx = await getJson(request, `${base}/api/sessions/${encodeURIComponent(psid)}/context`).catch(() => ({}));
        const listed = new Set((ctx.tools || []).map((t) => String(t.name)));
        const prow = await messages(request, base, psid);
        const blocked = prow.filter((m) => role(m) === 'tool' && /tool_policy_blocked/.test(String(m.content || '')));
        const reads = prow.filter((m) => role(m) === 'tool' && /^repo_file_/.test(String(m.name || '')));
        j.note(`phase ${ph.name}: session agent ${ctx.agent_id || '?'}; repo_file_read listed ${listed.has('repo_file_read')}; repo_file_* rows ${reads.length}${reads.length ? ` (first: ${String(reads[0].content || '').slice(0, 80).replace(/\s+/g, ' ')})` : ''}; policy-blocked ${blocked.length}`);
        if (ctx.agent_id && ctx.agent_id !== 'developer') throw new Error(`the Developer phase ran as ${ctx.agent_id}`);
        if (!listed.has('repo_file_read')) throw new Error('repo_file_read is not in the Developer phase tool list');
        if (blocked.length) throw new Error(`policy-blocked in the Developer phase: ${String(blocked[0].content).slice(0, 120)}`);
      }
    }, { timeoutMs: 430000 });
  },
};
