/**
 * CARD-537 journey (D1, Jacob 2026-09-26): an accepted skill tool widens AutoReiv's domain.
 * 1) Before: a high-tide question is outside AutoReiv's skills; the reply routes or says so (no refusal wording).
 * 2) A native tool (qa537_harbor_tide, fixed answer 14:05) is registered for autoreiv: a pending attach proposal,
 *    and the chat's tool list does not show it yet.
 * 3) Jacob accepts the proposal in Agent Studio; the skill shows ticked.
 * 4) Same chat: AutoReiv calls the tool and the reply gives 14:05 (no refusal). The chat tool list shows it.
 * 5) New chat: the same.
 * Checks are structural (tool rows, the tool's fixed value, the proposal, the tick), never exact model wording.
 */
import { clickExpect, waitFor } from './lib/runner.mjs';
import { HITL_CARD, getJson, openApp, openSessionByTitle, send, trackStreams, waitReplyIdle } from './lib/app.mjs';

const TOOL = 'qa537_harbor_tide';
const QUESTION = 'What time is high tide at Boston harbor today?';
const TIDE_RE = /\b(14:05|2:05)\b/;
const REFUSAL_RE = /outside (of )?my (authorized )?domain|not authorized to|\brefuse/i;
const CODE = "def run(port='', **kw):\n    return {'port': port or 'Boston', 'high_tide': '14:05', 'source': 'qa537 fixed table'}\n";

const role = (m) => String((m && m.role) || '').toLowerCase();

async function messages(request, base, sid) {
  const rows = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sid)}/messages`);
  return Array.isArray(rows) ? rows : [];
}

async function chatTools(request, base, sid) {
  const ctx = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sid)}/context`);
  return new Set((ctx.tools || []).map((t) => String(t.name)));
}

async function newChat(request, base, title) {
  const res = await request.post(`${base}/api/sessions`, { data: { agent_id: 'autoreiv', title } });
  if (!res.ok()) throw new Error(`create session -> ${res.status()}`);
  return (await res.json()).id;
}

export default {
  id: 'card-537-accepted-skill-widens-domain',
  card: 'CARD-537',
  title: 'An accepted skill tool widens the domain: AutoReiv uses it in the same chat and a new chat, never refuses',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    const title = `QA 537 tide ${viewport.name} ${Date.now() % 100000}`;
    let sid = '';
    let proposal = null;

    async function ask(label) {
      const n = streams.count;
      await send(page, QUESTION);
      await waitFor(() => streams.count > n, { timeoutMs: 15000 });
      await waitReplyIdle(page, { timeoutMs: 240000 });
      // The tool is registered read-only and without HITL; if a card still appears, approve it (noted, CARD-545).
      for (let i = 0; i < 2; i += 1) {
        const approve = page.locator(`${HITL_CARD} [data-hitl-decision="APPROVED"]`).first();
        if (!(await approve.isVisible().catch(() => false))) break;
        j.note(`${label}: approved a tool card (CARD-545: per-call approval)`);
        await approve.click();
        await page.waitForTimeout(2000);
        await waitReplyIdle(page, { timeoutMs: 240000 });
      }
    }

    async function checkAnswer(chatId, label) {
      const rows = await messages(request, base, chatId);
      const used = rows.filter((m) => role(m) === 'tool' && String(m.name || '') === TOOL);
      const replies = rows.filter((m) => role(m) === 'assistant').map((m) => String(m.content || '')).filter(Boolean);
      const last = replies[replies.length - 1] || '';
      const tools = await chatTools(request, base, chatId);
      j.note(`${label}: ${TOOL} rows ${used.length}; last result: ${String((used[used.length - 1] || {}).content || '').slice(0, 120)}; in chat tool list: ${tools.has(TOOL)}; reply: ${last.slice(0, 160).replace(/\s+/g, ' ')}`);
      if (!tools.has(TOOL)) throw new Error(`${TOOL} is not in the chat's tool list (${label})`);
      if (!used.length) throw new Error(`AutoReiv did not call ${TOOL} (${label})`);
      if (/Tool Error/i.test(String(used[used.length - 1].content || ''))) throw new Error(`${TOOL} returned an error (${label})`);
      if (REFUSAL_RE.test(last)) throw new Error(`reply contains refusal wording (${label}): ${last.slice(0, 160)}`);
      if (!TIDE_RE.test(last)) throw new Error(`the reply does not give the tool's answer 14:05 (${label})`);
    }

    await j.step('Before: the tide question is routed or declined plainly, never refused', async () => {
      sid = await newChat(request, base, title);
      await openApp(page, base);
      await openSessionByTitle(page, title, { agentId: 'autoreiv' });
      await ask('before');
      const rows = await messages(request, base, sid);
      const last = rows.filter((m) => role(m) === 'assistant').map((m) => String(m.content || '')).filter(Boolean).pop() || '';
      const handoffs = rows.filter((m) => role(m) === 'tool' && String(m.name || '') === 'handoff_to_agent').length;
      const button = await page.locator('.msg-ask-developer-btn').last().isVisible().catch(() => false);
      j.note(`before: handoffs ${handoffs}; Ask Developer button ${button}; reply: ${last.slice(0, 160).replace(/\s+/g, ' ')}`);
      if (REFUSAL_RE.test(last)) throw new Error(`reply contains refusal wording: ${last.slice(0, 160)}`);
      if (rows.some((m) => role(m) === 'tool' && String(m.name || '') === TOOL)) throw new Error(`${TOOL} was called before it existed`);
    }, { timeoutMs: 300000 });

    await j.step('Register the tool for autoreiv: a pending attach proposal, not yet in the domain', async () => {
      const res = await request.post(`${base}/api/tools/native`, { data: {
        name: TOOL, description: "Returns today's high tide time for a harbor port (for example Boston).",
        code: CODE, parameters: { type: 'object', properties: { port: { type: 'string' } } },
        requires_hitl: false, risk_level: 'low', target_agent_id: 'autoreiv', sample_arguments: { port: 'Boston' },
      } });
      if (!res.ok()) throw new Error(`register -> ${res.status()} ${await res.text()}`);
      const pending = await getJson(request, `${base}/api/approvals/pending?agent_id=autoreiv`);
      proposal = (Array.isArray(pending) ? pending : []).find((r) => r && r.tool_name === 'attach_tool_to_skill'
        && String((r.arguments || {}).tool) === TOOL) || null;
      if (!proposal) throw new Error('no pending attach proposal for the tool');
      if ((await chatTools(request, base, sid)).has(TOOL)) throw new Error(`${TOOL} is usable before acceptance`);
      j.note(`proposal ${proposal.id}: attach ${TOOL} to ${(proposal.arguments || {}).skill_id}`);
    }, { timeoutMs: 60000 });

    await j.step('Accept the proposal in Agent Studio; the skill shows ticked', async () => {
      const a = proposal.arguments || {};
      if (!(await page.locator('#forgeAgentSelect').isVisible().catch(() => false))) await page.locator('#dock-agents').click();
      await page.locator('#forgeAgentSelect').waitFor({ state: 'visible', timeout: 15000 });
      await page.selectOption('#forgeAgentSelect', 'autoreiv');
      const accept = page.locator(`#forgePendingProposals [data-attach-decision="APPROVED"][data-id="${proposal.id}"]`);
      await accept.waitFor({ state: 'visible', timeout: 20000 });
      await page.waitForTimeout(800);
      await accept.scrollIntoViewIfNeeded().catch(() => {});
      await clickExpect(accept, async () => (await chatTools(request, base, sid)).has(TOOL),
        { label: 'Accept', what: `${TOOL} in the chat tool list`, timeoutMs: 20000 });
      const agent = await getJson(request, `${base}/api/agents/autoreiv`);
      if (!(agent.allowed_skill || []).includes(a.skill_id)) throw new Error(`skill ${a.skill_id} not ticked on autoreiv`);
      const caps = page.locator('details[data-section="capabilities"]');
      if (!(await caps.evaluate((el) => el.open).catch(() => true))) await caps.locator('summary').first().click();
      const pill = page.locator(`.forge-skill-pill[data-skill-id="${a.skill_id}"]`).first();
      const ok = await waitFor(async () => (await pill.getAttribute('aria-pressed').catch(() => null)) === 'true', { timeoutMs: 15000 });
      if (!ok) throw new Error(`Agent Studio does not show ${a.skill_id} ticked`);
      await page.waitForTimeout(800);
      await pill.scrollIntoViewIfNeeded().catch(() => {});
      j.note(`accepted; ${a.skill_id} ticked in Agent Studio`);
    }, { timeoutMs: 90000 });

    async function minimizeStudio() {
      const studio = page.locator('#forgeAgentSelect');
      if (!(await studio.isVisible().catch(() => false))) return;
      await page.locator('#dock-agents').click();
      const hidden = await waitFor(async () => !(await studio.isVisible().catch(() => false)), { timeoutMs: 5000 });
      if (!hidden) await page.locator('.desktop-window:has(#forgeAgentSelect) .desktop-win-min').first().click({ timeout: 5000 }).catch(() => {});
    }

    await j.step('Same chat: AutoReiv answers with the accepted tool (14:05), no refusal', async () => {
      await minimizeStudio();
      await openSessionByTitle(page, title, { agentId: 'autoreiv' });
      await ask('same chat');
      await checkAnswer(sid, 'same chat');
    }, { timeoutMs: 520000 });

    await j.step('New chat: AutoReiv answers with the accepted tool (14:05), no refusal', async () => {
      const t2 = `${title} new`;
      const sid2 = await newChat(request, base, t2);
      await openApp(page, base);
      await minimizeStudio();
      await openSessionByTitle(page, t2, { agentId: 'autoreiv' });
      await ask('new chat');
      await checkAnswer(sid2, 'new chat');
    }, { timeoutMs: 520000 });
  },
};
