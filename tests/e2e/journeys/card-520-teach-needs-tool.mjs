/**
 * CARD-532 journey for CARD-520, updated for CARD-539 (ADR-0061 rule 8): Teach on "weather in Boston" -> Needs a tool
 * -> Ask Developer to build this tool -> the Developer registers it with target_agent_id -> a pending
 * "attach tool to skill" proposal (no silent grant) -> Jacob accepts it in Agent Studio -> the skill is ticked
 * -> AutoReiv answers the weather question with the new tool.
 * Model replies are checked structurally (a card, a proposal, a tick, a tool call), never by exact text.
 */
import { clickExpect, waitFor } from './lib/runner.mjs';
import { HITL_CARD, getJson, isStreaming, openApp, openSessionByTitle, send, trackStreams, waitReplyIdle } from './lib/app.mjs';

const QUESTION = 'What is the weather in Boston right now?';
const LESSON = 'You need a real weather tool to answer this. Do not guess the weather.';
const ATTACH = 'attach_tool_to_skill';

async function grantedTools(request, base) {
  const a = await getJson(request, `${base}/api/agents/autoreiv`);
  return new Set((a.allowed_tools || []).map((t) => String(t && t.name ? t.name : t)));
}

async function attachProposals(request, base) {
  const rows = await getJson(request, `${base}/api/approvals/pending?agent_id=autoreiv`);
  return (Array.isArray(rows) ? rows : []).filter((r) => r && r.tool_name === ATTACH);
}

export default {
  id: 'card-520-teach-needs-tool',
  card: 'CARD-520',
  title: 'Teach -> Needs a tool -> Ask Developer -> attach proposal accepted in Agent Studio -> AutoReiv answers',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    const title = `QA 520 weather ${viewport.name} ${Date.now() % 100000}`;
    let sessionId = '';
    let newTools = [];
    let beforeProposals = new Set();
    let proposal = null;

    await j.step('Ask AutoReiv about the weather in Boston', async () => {
      beforeProposals = new Set((await attachProposals(request, base)).map((r) => String(r.id)));
      const res = await request.post(`${base}/api/sessions`, { data: { agent_id: 'autoreiv', title } });
      if (!res.ok()) throw new Error(`create session -> ${res.status()}`);
      sessionId = (await res.json()).id;
      await openApp(page, base);
      await openSessionByTitle(page, title, { agentId: 'autoreiv' });
      await send(page, QUESTION);
      await waitFor(() => streams.count >= 1, { timeoutMs: 15000 });
      await waitReplyIdle(page, { timeoutMs: 240000 });
    }, { timeoutMs: 260000 });

    await j.step('Teach on that reply shows a Needs a tool card with Ask Developer', async () => {
      const teach = page.locator('.msg-teach-agent-btn').last();
      await clickExpect(teach, () => page.locator('#teachAgentModal').isVisible(), { label: 'Teach', what: 'the Teach dialog', timeoutMs: 10000 });
      await page.locator('#teachAgentGuidanceInput').fill(LESSON);
      const ask = page.locator('.skill-proposal-card .btn-escalate-developer').last();
      await clickExpect(page.locator('#submitTeachAgentBtn'), () => ask.isVisible(), { label: 'Teach submit', what: 'a Needs a tool card with Ask Developer', timeoutMs: 300000 });
      await ask.scrollIntoViewIfNeeded();
    }, { timeoutMs: 320000 });

    await j.step('Ask Developer opens a Developer chat that starts replying', async () => {
      const n = streams.count;
      await clickExpect(page.locator('.skill-proposal-card .btn-escalate-developer').last(), () => streams.count > n,
        { label: 'Ask Developer to build this tool', what: 'a Developer reply (POST /api/chat/stream)', timeoutMs: 30000 });
    }, { timeoutMs: 40000 });

    await j.step('The Developer builds the tool and proposes attaching it to an autoreiv skill (no silent grant)', async () => {
      let stoppedChecks = 0;
      const found = await waitFor(async () => {
        const pending = await attachProposals(request, base);
        const fresh = pending.filter((r) => !beforeProposals.has(String(r.id)));
        if (fresh.length) return fresh[fresh.length - 1];
        const attachIds = new Set(pending.map((r) => String(r.id)));
        const cards = page.locator(HITL_CARD);
        const n = await cards.count();
        for (let i = 0; i < n; i += 1) {
          const card = cards.nth(i);
          if (attachIds.has(String(await card.getAttribute('data-approval-id')))) continue;
          const approve = card.locator('[data-hitl-decision="APPROVED"]').first();
          if (await approve.isVisible().catch(() => false)) {
            await approve.click();
            stoppedChecks = 0;
            j.note('approved a Developer approval card');
            await page.waitForTimeout(1500);
            return null;
          }
        }
        // No nudging (CARD-535 is a known bug): if the Developer goes idle with nothing to approve, stop here.
        stoppedChecks = (await isStreaming(page)) ? 0 : stoppedChecks + 1;
        if (stoppedChecks >= 10) return { stopped: true }; // ~15 s idle
        return null;
      }, { timeoutMs: 900000, intervalMs: 1500 });
      if (!found) throw new Error('no attach-tool-to-skill proposal for autoreiv within 15 minutes');
      if (found.stopped) throw new Error('the Developer stopped without proposing attach_tool_to_skill');
      proposal = found;
      const a = proposal.arguments || {};
      newTools = [String(a.tool)];
      j.note(`proposal ${proposal.id}: attach ${a.tool} to ${a.new_skill ? 'new ' : ''}skill ${a.skill_id}`);
      const now = await grantedTools(request, base);
      if (now.has(String(a.tool))) throw new Error(`${a.tool} is already usable by autoreiv before acceptance (silent grant)`);
      await waitReplyIdle(page, { timeoutMs: 300000 });
      const inTray = page.locator(`${HITL_CARD}[data-approval-id="${proposal.id}"]`);
      j.note(`proposal card visible in the Developer chat tray: ${await inTray.isVisible().catch(() => false)}`);
    }, { timeoutMs: 1300000, knownBug: 'CARD-535' });

    await j.step('Accept the proposal in Agent Studio; the skill shows ticked', async () => {
      const a = proposal.arguments || {};
      if (!(await page.locator('#forgeAgentSelect').isVisible().catch(() => false))) await page.locator('#dock-agents').click();
      await page.locator('#forgeAgentSelect').waitFor({ state: 'visible', timeout: 15000 });
      await page.selectOption('#forgeAgentSelect', 'autoreiv');
      const accept = page.locator(`#forgePendingProposals [data-attach-decision="APPROVED"][data-id="${proposal.id}"]`);
      await accept.waitFor({ state: 'visible', timeout: 20000 });
      await page.waitForTimeout(800); // the pending list can re-render once after the agent loads
      await accept.scrollIntoViewIfNeeded().catch(() => {});
      await clickExpect(accept, async () => (await grantedTools(request, base)).has(String(a.tool)),
        { label: 'Accept', what: `${a.tool} usable by autoreiv`, timeoutMs: 20000 });
      const agent = await getJson(request, `${base}/api/agents/autoreiv`);
      if (!(agent.allowed_skill || []).includes(a.skill_id)) throw new Error(`skill ${a.skill_id} not ticked on autoreiv`);
      const caps = page.locator('details[data-section="capabilities"]');
      if (!(await caps.evaluate((el) => el.open).catch(() => true))) await caps.locator('summary').first().click();
      const pill = page.locator(`.forge-skill-pill[data-skill-id="${a.skill_id}"]`).first();
      const ok = await waitFor(async () => (await pill.getAttribute('aria-pressed').catch(() => null)) === 'true', { timeoutMs: 15000 });
      if (!ok) throw new Error(`Agent Studio does not show ${a.skill_id} ticked`);
      await page.waitForTimeout(800); // the Studio re-renders after accepting
      await pill.scrollIntoViewIfNeeded().catch(() => {});
      j.note(`accepted; ${a.skill_id} ticked in Agent Studio`);
    }, { timeoutMs: 90000 });

    // On desktop the Agent Studio window sits over the chat (and is restored after a reload); minimize it.
    async function minimizeStudio() {
      const studio = page.locator('#forgeAgentSelect');
      if (!(await studio.isVisible().catch(() => false))) return;
      await page.locator('#dock-agents').click(); // the dock button toggles an open window to minimized
      const hidden = await waitFor(async () => !(await studio.isVisible().catch(() => false)), { timeoutMs: 5000 });
      if (!hidden) await page.locator('.desktop-window:has(#forgeAgentSelect) .desktop-win-min').first().click({ timeout: 5000 }).catch(() => {});
    }

    async function askAndCheck(sid, label) {
      await send(page, QUESTION);
      await page.waitForTimeout(2000);
      await waitReplyIdle(page, { timeoutMs: 240000 });
      const msgs = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sid)}/messages`);
      const used = (Array.isArray(msgs) ? msgs : []).filter((m) => String(m.role || '').toLowerCase() === 'tool'
        && newTools.some((t) => String(m.name || '') === t || String(m.content || '').includes(t)));
      if (!used.length) throw new Error(`AutoReiv did not call ${newTools.join(' / ')} for the question (${label})`);
      j.note(`${label}: tool rows for the new tool: ${used.length}; last: ${String(used[used.length - 1].content || '').slice(0, 160)}`);
    }

    await j.step('AutoReiv answers the weather question with the new tool (same chat)', async () => {
      await minimizeStudio();
      await openSessionByTitle(page, title, { agentId: 'autoreiv' });
      await askAndCheck(sessionId, 'same chat');
    }, { timeoutMs: 260000, soft: true, card: 'CARD-543' });

    await j.step('A new AutoReiv chat answers the weather question with the new tool', async () => {
      const t2 = `${title} new`;
      const res = await request.post(`${base}/api/sessions`, { data: { agent_id: 'autoreiv', title: t2 } });
      if (!res.ok()) throw new Error(`create session -> ${res.status()}`);
      const sid2 = (await res.json()).id;
      await openApp(page, base); // reload so the drawer lists the chat created through the API
      await minimizeStudio();
      await openSessionByTitle(page, t2, { agentId: 'autoreiv' });
      await askAndCheck(sid2, 'new chat');
    }, { timeoutMs: 260000, soft: true, card: 'CARD-543' });
  },
};
