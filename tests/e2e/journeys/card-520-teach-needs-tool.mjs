/**
 * CARD-532 journey for CARD-520: Teach on "weather in Boston" -> Needs a tool -> Ask Developer to build this tool
 * -> the new tool is granted to autoreiv -> AutoReiv answers the weather question with it.
 * Model replies are checked structurally (a card, a grant, a tool call), never by exact text.
 */
import { clickExpect, waitFor } from './lib/runner.mjs';
import { HITL_CARD, getJson, isStreaming, openApp, openSessionByTitle, send, trackStreams, waitReplyIdle } from './lib/app.mjs';

const QUESTION = 'What is the weather in Boston right now?';
const LESSON = 'You need a real weather tool to answer this. Do not guess the weather.';
const CONTINUE = 'Approved. Please continue and register the tool for autoreiv.';

async function grantedTools(request, base) {
  const a = await getJson(request, `${base}/api/agents/autoreiv`);
  return new Set([...(a.allowed_tool_names || []), ...(a.pack_tool_names || [])].map(String));
}

export default {
  id: 'card-520-teach-needs-tool',
  card: 'CARD-520',
  title: 'Teach -> Needs a tool -> Ask Developer -> tool granted to autoreiv -> AutoReiv answers',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const streams = trackStreams(page);
    const title = `QA 520 weather ${viewport.name} ${Date.now() % 100000}`;
    let sessionId = '';
    let before = new Set();
    let newTools = [];

    await j.step('Ask AutoReiv about the weather in Boston', async () => {
      before = await grantedTools(request, base);
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

    await j.step('The Developer builds the tool and grants it to autoreiv', async () => {
      let nudges = 0;
      let approvedSinceTurn = 0;
      const granted = await waitFor(async () => {
        const now = await grantedTools(request, base);
        const added = [...now].filter((t) => !before.has(t));
        if (added.length) return added;
        const approve = page.locator(`${HITL_CARD} [data-hitl-decision="APPROVED"]`).first();
        if (await approve.isVisible().catch(() => false)) {
          await approve.click();
          approvedSinceTurn += 1;
          j.note('approved a Developer approval card');
          await page.waitForTimeout(1500);
          return null;
        }
        if (!(await isStreaming(page))) {
          await page.waitForTimeout(3000);
          if (await isStreaming(page)) return null;
          if (await page.locator(`${HITL_CARD} [data-hitl-decision="APPROVED"]`).first().isVisible().catch(() => false)) return null;
          if (nudges < 3) {
            nudges += 1;
            j.note(`Developer stopped without a grant (approved ${approvedSinceTurn} card(s) this turn); sent "${CONTINUE}" (CARD-535 workaround, nudge ${nudges})`);
            approvedSinceTurn = 0;
            await send(page, CONTINUE);
            await page.waitForTimeout(3000);
          }
        }
        return null;
      }, { timeoutMs: 900000, intervalMs: 1500 });
      if (!granted) throw new Error('no new tool was granted to autoreiv within 15 minutes');
      newTools = granted;
      j.note(`granted to autoreiv: ${newTools.join(', ')}`);
      await waitReplyIdle(page, { timeoutMs: 300000 });
    }, { timeoutMs: 1300000 });

    await j.step('AutoReiv answers the weather question with the new tool', async () => {
      await openSessionByTitle(page, title, { agentId: 'autoreiv' });
      await send(page, QUESTION);
      await page.waitForTimeout(2000);
      await waitReplyIdle(page, { timeoutMs: 240000 });
      const msgs = await getJson(request, `${base}/api/sessions/${encodeURIComponent(sessionId)}/messages`);
      const used = (Array.isArray(msgs) ? msgs : []).filter((m) => String(m.role || '').toLowerCase() === 'tool'
        && newTools.some((t) => String(m.name || '') === t || String(m.content || '').includes(t)));
      if (!used.length) throw new Error(`AutoReiv did not call ${newTools.join(' / ')} for the question`);
      j.note(`tool rows for the new tool: ${used.length}; last: ${String(used[used.length - 1].content || '').slice(0, 160)}`);
    }, { timeoutMs: 260000, soft: true });
  },
};
