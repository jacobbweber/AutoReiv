/**
 * CARD-550 journey (D1, Jacob 2026-09-27): Developer ticks coding, so a code request that must read an AutoReiv
 * source file reaches Developer with the checkout repo_file_* tools allowed.
 * 1) Developer's allowed tools include repo_file_read / repo_file_list / repo_file_write / repo_file_patch.
 * 2) Asked in an AutoReiv chat, the job finishes end to end (CARD-554, CARD-553, CARD-548): Formulate plans (no
 *    'changed this step' failure), the journey presses Approve on each approval card, Developer's Execute phase runs
 *    with its own tools (no 'out of matched capability subset' skip), reads the file with repo_file_read, runs code
 *    with execute_code or cli_exec, and the job and the Execute phase end DONE. No refusal wording.
 * Checks are structural (agent tool lists, phase assignment, tool rows), never exact model wording.
 */
import { waitFor } from './lib/runner.mjs';
import { HITL_CARD, getJson, isStreaming, openApp, openSessionByTitle, send, sessionJobStatus, trackStreams, waitReplyIdle } from './lib/app.mjs';

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

    await j.step('A code request in an AutoReiv chat finishes: Formulate plans, Developer Execute runs after Approve, job DONE', async () => {
      const title = `QA 550 checkout ${viewport.name} ${Date.now() % 100000}`;
      const res = await request.post(`${base}/api/sessions`, { data: { agent_id: 'autoreiv', title } });
      if (!res.ok()) throw new Error(`create session -> ${res.status()}`);
      const sid = (await res.json()).id;
      await openApp(page, base);
      await openSessionByTitle(page, title, { agentId: 'autoreiv' });
      const n = streams.count;
      await send(page, ASK);
      await waitFor(() => streams.count > n, { timeoutMs: 15000 });
      // Press Approve on every approval card (Developer's execute_code / cli_exec) until the job ends [CARD-548].
      let approvals = 0;
      let status = '';
      await waitFor(async () => {
        const cards = page.locator(HITL_CARD);
        const count = await cards.count();
        for (let i = 0; i < count; i += 1) {
          const approve = cards.nth(i).locator('[data-hitl-decision="APPROVED"]').first();
          if (await approve.isVisible().catch(() => false)) {
            await approve.click();
            approvals += 1;
            await page.waitForTimeout(1500);
            return false;
          }
        }
        status = await sessionJobStatus(request, base, sid).catch(() => '');
        return ['done', 'failed', 'cancelled'].includes(status) && !(await isStreaming(page));
      }, { timeoutMs: 900000, intervalMs: 2000 });
      await waitReplyIdle(page, { timeoutMs: 60000 }).catch(() => {});

      const phasesAll = await jobPhases(request, base, sid);
      const listed = await getJson(request, `${base}/api/sessions`).catch(() => []);
      const inJob = (Array.isArray(listed) ? listed : []).filter((x) => String(x.id).startsWith(`${sid}::`));
      const devSessions = new Set(inJob.filter((x) => x.agent_id === 'developer').map((x) => String(x.id)));
      const rowsBy = {};
      for (const s2 of new Set([sid, ...inJob.map((x) => String(x.id))])) rowsBy[s2] = await messages(request, base, s2).catch(() => []);
      const allRows = Object.values(rowsBy).flat();
      const devRows = Object.entries(rowsBy).filter(([k]) => devSessions.has(k)).flatMap(([, v]) => v);
      const tool = (rows, re) => rows.filter((m) => role(m) === 'tool' && re.test(String(m.name || '')));
      const ok = (m) => !/tool_policy_blocked|"skipped":\s*true|^Tool Error|approval_required|"success":\s*false/i.test(String(m.content || ''));
      const repoOk = tool(devRows, /^repo_file_read$/).filter((m) => /"success":\s*true/.test(String(m.content || '')));
      const runOk = tool(devRows, /^(execute_code|cli_exec)$/).filter(ok);
      const subsetSkips = devRows.filter((m) => /out of matched capability subset/.test(String(m.content || ''))).length;
      const planningBlocks = allRows.filter((m) => /not used while planning/.test(String(m.content || ''))).length;
      const refused = allRows.some((m) => /changed this step while it was finishing/.test(String(m.content || '')));
      const execute = phasesAll.find((ph) => /developer/i.test(String(ph.assigned_agent_id || '')));
      const last = (rowsBy[sid] || []).filter((m) => role(m) === 'assistant').map((m) => String(m.content || '')).filter(Boolean).pop() || '';
      j.note(`job ${status}; phases: ${phasesAll.map((p) => `${p.name}(${p.assigned_agent_id}):${p.status}`).join(', ')}; approvals pressed ${approvals}; Developer sessions ${devSessions.size}; Developer tools used: ${[...new Set(tool(devRows, /./).map((m) => m.name))].join(', ') || 'none'}; repo_file_read ok ${repoOk.length}${repoOk.length ? ` (${String(repoOk[0].content).slice(0, 80).replace(/\s+/g, ' ')})` : ''}; execute_code/cli_exec ok ${runOk.length}; subset skips ${subsetSkips}; planning-phase blocks ${planningBlocks}; reply: ${last.slice(0, 160).replace(/\s+/g, ' ')}`);
      if (REFUSAL_RE.test(last)) throw new Error(`reply contains refusal wording: ${last.slice(0, 160)}`);
      if (refused) throw new Error('a phase failed with "another run of this job changed this step" (CARD-554)');
      if (!execute) throw new Error('no Execute phase assigned to Developer');
      if (subsetSkips) throw new Error(`Developer tools were skipped as out of the job's matched capability subset (${subsetSkips}, CARD-553)`);
      if (status !== 'done') throw new Error(`job ended ${status || 'unknown'}, not done`);
      if (String(execute.status) !== 'done') throw new Error(`Developer's ${execute.name} phase is ${execute.status}, not done`);
      if (!repoOk.length) throw new Error('Developer did not read the file with repo_file_read');
      if (!runOk.length) throw new Error('Developer did not run code (no successful execute_code or cli_exec row)');
    }, { timeoutMs: 960000 });
  },
};
