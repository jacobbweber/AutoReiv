/**
 * CARD-550 journey (D1, Jacob 2026-09-27): Developer ticks coding, so a code request that must read an AutoReiv
 * source file reaches Developer with the checkout repo_file_* tools allowed.
 * 1) Developer's allowed tools include repo_file_read / repo_file_list / repo_file_write / repo_file_patch.
 * 2) Asked in an AutoReiv chat, the request goes to Developer (a handoff row in the chat or a phase chat, or a Developer
 *    job phase), and Developer gets a working repo_file_* tool (a successful repo_file_* row, or repo_file_read in
 *    the Developer phase's tool list). No refusal wording.
 * Checks are structural (agent tool lists, phase assignment, tool rows), never exact model wording.
 */
import { waitFor } from './lib/runner.mjs';
import { HITL_CARD, getJson, openApp, openSessionByTitle, send, trackStreams, waitReplyIdle } from './lib/app.mjs';

const REPO_TOOLS = ['repo_file_read', 'repo_file_list', 'repo_file_write', 'repo_file_patch'];
// Reading alone is platform-wide (read_document_file, CARD-539 D3), so the ask also needs code run: that is code work.
const ASK = 'In the AutoReiv checkout, read src/application/agent_packs/allowed_tools.py with the repository tools, then write and run a small Python snippet that counts the top-level def statements in it, and show me the count.';
const REFUSAL_RE = /outside (of )?my (authorized )?domain|not authorized to|\brefuse/i;

const role = (m) => String((m && m.role) || '').toLowerCase();
const toolNames = (a) => new Set((a.allowed_tools || []).map((t) => String(typeof t === 'string' ? t : (t && t.name) || '')));

async function messages(request, base, sid) {
  const rows = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sid)}/messages`);
  return Array.isArray(rows) ? rows : [];
}

async function jobPhases(request, base, sid) {
  const jn = await getJson(request, `${base}/api/chat/sessions/${encodeURIComponent(sid)}/journey`).catch(() => ({}));
  const jobs = Array.isArray(jn.jobs) ? jn.jobs : [];
  return jobs.flatMap((job) => (Array.isArray(job.phases) ? job.phases : []));
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
      // The request can reach Developer three ways: a handoff from the chat, a handoff from inside a job phase, or a
      // job whose Execute phase is Developer's. Look in the chat and in every phase chat of its jobs.
      const phasesAll = await jobPhases(request, base, sid);
      const sessions = [sid, ...phasesAll.map((ph) => `${sid}::phase::${ph.id}`)];
      const rowsBy = {};
      for (const s2 of sessions) rowsBy[s2] = await messages(request, base, s2).catch(() => []);
      const allRows = Object.values(rowsBy).flat();
      const handoffs = allRows.filter((m) => role(m) === 'tool' && String(m.name || '') === 'handoff_to_agent'
        && /developer/i.test(String(m.content || ''))).length;
      const devPhases = phasesAll.filter((ph) => /developer/i.test(String(ph.assigned_agent_id || '')));
      // AutoReiv no longer ticks coding (CARD-544), so only Developer can get a successful repo_file_* result.
      const repoOk = allRows.filter((m) => role(m) === 'tool' && /^repo_file_/.test(String(m.name || ''))
        && /"success":\s*true/.test(String(m.content || '')));
      const blocked = allRows.filter((m) => role(m) === 'tool' && /^repo_file_/.test(String(m.name || ''))
        && /tool_policy_blocked/.test(String(m.content || ''))).length;
      const last = (rowsBy[sid] || []).filter((m) => role(m) === 'assistant').map((m) => String(m.content || '')).filter(Boolean).pop() || '';
      let listedInDevPhase = false;
      for (const ph of devPhases) {
        const ctx = await getJson(request, `${base}/api/sessions/${encodeURIComponent(`${sid}::phase::${ph.id}`)}/context`).catch(() => ({}));
        if ((ctx.tools || []).some((t) => String(t.name) === 'repo_file_read') && ctx.agent_id === 'developer') listedInDevPhase = true;
      }
      j.note(`handoffs to developer ${handoffs}; developer phases: ${devPhases.map((p) => `${p.name}:${p.status}`).join(', ') || 'none'}; successful repo_file_* rows ${repoOk.length}${repoOk.length ? ` (${String(repoOk[0].content).slice(0, 90).replace(/\s+/g, ' ')})` : ''}; repo_file_read in a Developer phase tool list ${listedInDevPhase}; AutoReiv repo_file_* policy blocks ${blocked} (expected, CARD-544); approval cards: ${await page.locator(HITL_CARD).count()}; reply: ${last.slice(0, 140).replace(/\s+/g, ' ')}`);
      if (REFUSAL_RE.test(last)) throw new Error(`reply contains refusal wording: ${last.slice(0, 160)}`);
      if (!handoffs && !devPhases.length) throw new Error('the request did not reach Developer (no handoff row, no developer phase)');
      if (!repoOk.length && !listedInDevPhase) throw new Error('Developer did not get a working repo_file_* tool (no successful repo_file_* row, not in a Developer phase tool list)');
    }, { timeoutMs: 430000 });
  },
};
