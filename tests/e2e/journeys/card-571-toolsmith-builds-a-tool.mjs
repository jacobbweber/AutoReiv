/**
 * CARD-571 journey: Ask Developer -> Toolsmith builds a small tool -> saved disabled -> Jacob enables it in
 * Tools Studio, which also accepts the attach proposal -> the target agent has the tool.
 * 1) A capability gap for Tutor (API), then Agents studio > Tutor > gap backlog > Ask Developer opens a Toolsmith chat.
 * 2) Toolsmith saves a runtime tool (the journey approves only register_native_tool cards, never an attach card).
 *    The tool is disabled, has a pending attach for tutor, and Tutor does not have it yet.
 * 3) Accepting the attach before enabling is refused (409, Gap 1).
 * 4) Tools Studio shows the tool with Enable (and a warning if it reaches the network/files/programs); Show code works.
 * 5) Enable: the tool is enabled, the attach is accepted, and Tutor's allowed tools include it.
 */
import { waitFor } from './lib/runner.mjs';
import { HITL_CARD, getJson, isStreaming, openApp, trackStreams, waitReplyIdle } from './lib/app.mjs';

const GAP = {
  user_prompt: 'How many words are in this sentence: "the quick brown fox jumps over the lazy dog"? Count them exactly with a tool.',
  identified_capability: 'count the words in a piece of text and return the number',
  suggested_tool_name: 'count_words_571',
};

async function runtimeTools(request, base) {
  const body = await getJson(request, `${base}/api/tools/native`).catch(() => ({}));
  return Array.isArray(body.tools) ? body.tools : [];
}

async function tutorTools(request, base) {
  const body = await getJson(request, `${base}/api/agents/tutor`).catch(() => ({}));
  const agent = body.agent || body;
  return new Set(Array.isArray(agent.allowed_tools) ? agent.allowed_tools : []);
}

export default {
  id: 'card-571-toolsmith-builds-a-tool',
  card: 'CARD-571',
  title: 'Ask Developer -> Toolsmith saves a disabled tool -> Jacob enables it (accepts the attach) -> Tutor has it',
  allow: ['/api/approvals/'],
  allowConsole: ['409', 'Conflict'],
  async run(j, { page, request, base }) {
    const streams = trackStreams(page);
    let tool = null;

    await j.step('Ask Developer on a Tutor gap opens a Toolsmith chat', async () => {
      const res = await request.post(`${base}/api/agents/tutor/gaps`, { data: GAP });
      if (!res.ok()) throw new Error(`create gap -> ${res.status()}`);
      await openApp(page, base);
      await page.locator('#dock-agents').click();
      await page.locator('#forgeAgentSelect').selectOption('tutor');
      const btn = page.locator('.btn-gap-ask-developer').first();
      if (!(await btn.isVisible().catch(() => false))) {
        const header = page.locator('#agentTrainingBacklogCard > summary');
        await header.scrollIntoViewIfNeeded().catch(() => {});
        await header.click();
      }
      await btn.scrollIntoViewIfNeeded().catch(() => {});
      const shown = await waitFor(() => btn.isVisible().catch(() => false), { timeoutMs: 15000 });
      if (!shown) throw new Error('no Ask Developer button in the Tutor gap backlog');
      const n = streams.count;
      await btn.click();
      const started = await waitFor(() => streams.count > n, { timeoutMs: 20000 });
      if (!started) throw new Error('Ask Developer did not start a chat reply');
      const agent = await page.locator('#agentSelect').inputValue().catch(() => '');
      j.note(`active agent after Ask Developer: ${agent}`);
      if (agent !== 'toolsmith') throw new Error(`the chat opened on ${agent || '?'}, not toolsmith`);
    }, { timeoutMs: 60000 });

    await j.step('Toolsmith saves the tool disabled with a pending attach for Tutor', async () => {
      const approved = [];
      await waitFor(async () => {
        const cards = page.locator(HITL_CARD);
        const count = await cards.count();
        for (let i = 0; i < count; i += 1) {
          const text = (await cards.nth(i).innerText().catch(() => '')).replace(/\s+/g, ' ');
          const approve = cards.nth(i).locator('[data-hitl-decision="APPROVED"]').first();
          if (/register_native_tool/.test(text) && await approve.isVisible().catch(() => false)) {
            await approve.click();
            approved.push(text.slice(0, 80));
            await page.waitForTimeout(1500);
            return false;
          }
        }
        if (await isStreaming(page)) return false;
        const rows = await runtimeTools(request, base);
        return rows.some((r) => (r.pending_attach || []).some((p) => p.agent_id === 'tutor'));
      }, { timeoutMs: 900000, intervalMs: 3000 }).catch(() => {});
      await waitReplyIdle(page, { timeoutMs: 120000 }).catch(() => {});
      j.note(`approved save calls: ${approved.length}`);
      const rows = await runtimeTools(request, base);
      tool = rows.find((r) => (r.pending_attach || []).some((p) => p.agent_id === 'tutor')) || rows[0] || null;
      if (!tool) throw new Error('Toolsmith did not save a runtime tool');
      j.note(`tool ${tool.name}: approval ${tool.approval}; check ${tool.check && tool.check.status}; access [${(tool.access || []).join(', ')}]; pending attach ${JSON.stringify(tool.pending_attach)}`);
      if (tool.approval !== 'disabled') throw new Error(`a freshly saved tool must be disabled, got ${tool.approval}`);
      if (!(tool.pending_attach || []).some((p) => p.agent_id === 'tutor')) throw new Error('no pending attach proposal for tutor');
      if ((await tutorTools(request, base)).has(tool.name)) throw new Error('Tutor has the tool before Jacob enabled it');
    }, { timeoutMs: 960000 });

    await j.step('Accepting the attach before enabling is refused (Gap 1)', async () => {
      const pid = tool.pending_attach.find((p) => p.agent_id === 'tutor').approval_id;
      const res = await request.post(`${base}/api/approvals/${encodeURIComponent(pid)}/decision`, { data: { decision: 'APPROVED' } });
      j.note(`accept before enable -> ${res.status()}`);
      if (res.status() !== 409) throw new Error(`expected 409, got ${res.status()}`);
    });

    await j.step('Tools Studio shows the tool with Enable, its code and any access warning', async () => {
      await page.locator('#dock-tools-studio').click();
      const row = page.locator(`[data-testid="runtime-tool-${tool.name}"]`);
      const shown = await waitFor(() => row.isVisible().catch(() => false), { timeoutMs: 20000 });
      if (!shown) throw new Error('the runtime tool is not listed in Tools Studio');
      await page.locator(`[data-testid="runtime-tool-show-code-${tool.name}"]`).click();
      const code = page.locator(`[data-testid="runtime-tool-code-${tool.name}"]`);
      await waitFor(async () => /def run/.test(await code.innerText().catch(() => '')), { timeoutMs: 10000 });
      const warn = await page.locator(`[data-testid="runtime-tool-access-${tool.name}"]`).isVisible().catch(() => false);
      const attach = await page.locator(`[data-testid="runtime-tool-attach-${tool.name}"]`).innerText().catch(() => '');
      j.note(`warning shown: ${warn} (access: ${(tool.access || []).join(', ') || 'none'}); attach note: ${attach}`);
      if ((tool.access || []).length && !warn) throw new Error('the tool reaches the network/files/programs but no warning is shown');
      if (!/tutor/.test(attach)) throw new Error('the panel does not say enabling also gives it to tutor');
      await row.scrollIntoViewIfNeeded();
    });

    await j.step('Enable accepts the attach: the tool is enabled and Tutor has it', async () => {
      await page.locator(`[data-testid="runtime-tool-enable-${tool.name}"]`).click();
      const ok = await waitFor(async () => (await tutorTools(request, base)).has(tool.name), { timeoutMs: 20000 });
      const after = (await runtimeTools(request, base)).find((r) => r.name === tool.name) || {};
      j.note(`after enable: approval ${after.approval}; pending attach ${JSON.stringify(after.pending_attach)}; tutor has tool: ${ok}`);
      if (after.approval !== 'enabled') throw new Error('the tool is not enabled');
      if (!ok) throw new Error('Tutor does not have the tool after enabling');
      if ((after.pending_attach || []).length) throw new Error('the attach proposal is still pending');
      await page.locator(`[data-testid="runtime-tool-${tool.name}"]`).scrollIntoViewIfNeeded();
    }, { timeoutMs: 40000 });
  },
};
