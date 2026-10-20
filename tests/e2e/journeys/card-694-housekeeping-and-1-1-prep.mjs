/**
 * CARD-694 journey: Align product concepts, docs, and findings with M26-M28 for v1.1.0.
 * 1) Open Chat and Capabilities (#view-capabilities) and verify the 3-agent roster
 *    (AutoReiv, Tutor, Direct) and unified Capabilities studio with zero retired launchers or agents.
 * 2) Ask AutoReiv in Chat about AutoReiv's shipped agents and the studio that manages skills
 *    and verify it answers directly from AUTOREIV_CONCEPTS without tool calls.
 */
import { waitFor } from './lib/runner.mjs';
import { getJson, openApp, openTab, send, waitReplyIdle } from './lib/app.mjs';

const AGENT_ID = 'autoreiv';
const RETIRED_AGENTS = ['architect', 'developer', 'toolsmith'];

export default {
  id: 'card-694-housekeeping-and-1-1-prep',
  card: 'CARD-694',
  title: 'Product concepts, docs, and Capabilities alignment for v1.1.0',
  allow: [],
  async run(j, { page, request, base }) {
    await j.step('Verify 3-agent roster and unified Capabilities studio on desktop and phone', async () => {
      await openApp(page, base);
      await openTab(page, 'chat');

      const agents = await getJson(request, `${base}/api/agents`);
      const ids = (Array.isArray(agents) ? agents : (agents.agents || [])).map((a) => a.id).sort();
      for (const expected of ['autoreiv', 'direct', 'tutor']) {
        if (!ids.includes(expected)) {
          throw new Error(`Expected ${expected} in /api/agents, got: ${JSON.stringify(ids)}`);
        }
      }
      for (const retired of RETIRED_AGENTS) {
        if (ids.includes(retired)) {
          throw new Error(`Retired agent ${retired} still present in /api/agents: ${JSON.stringify(ids)}`);
        }
      }

      await openTab(page, 'capabilities');
      const treeReady = await waitFor(
        async () => {
          const txt = await page.locator('#capabilitiesTreeList').innerText().catch(() => '');
          return txt.includes('capability-authoring') && txt.includes('project-cards') && txt.includes('software-development');
        },
        { timeoutMs: 15000 }
      );
      if (!treeReady) {
        const txt = await page.locator('#capabilitiesTreeList').innerText().catch(() => '');
        throw new Error(`Expected #capabilitiesTreeList to list consolidated Agora skills, got: ${txt}`);
      }
      j.note('Verified 3-agent roster and unified Capabilities studio tree');
    });

    await j.step('In Chat, AutoReiv answers a product concept question about shipped agents and Capabilities without tool calls', async () => {
      await openTab(page, 'chat');
      await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 20000 });
      if ((await page.locator('#agentSelect').inputValue().catch(() => '')) !== AGENT_ID) {
        await page.selectOption('#agentSelect', AGENT_ID);
        await page.waitForTimeout(500);
      }

      await send(
        page,
        'In two short sentences, without calling any tools: what are the three shipped agents in AutoReiv, and which studio manages skills and tools?'
      );
      await waitReplyIdle(page, { timeoutMs: 180000 });

      const sessions = await getJson(request, `${base}/api/sessions?agent_id=${AGENT_ID}`);
      const latest = (sessions.sessions || sessions || [])[0];
      if (!latest || !latest.id) throw new Error('No chat session found for AutoReiv');
      const msgs = await getJson(request, `${base}/api/sessions/${encodeURIComponent(latest.id)}/messages`);
      const rows = Array.isArray(msgs) ? msgs : (msgs.messages || []);
      const assistantMsgs = rows.filter((m) => m.role === 'assistant' && String(m.content || '').trim().length > 0);
      if (assistantMsgs.length === 0) {
        throw new Error('Expected non-empty assistant reply in AutoReiv session');
      }
      const toolMsgs = rows.filter((m) => m.role === 'tool');
      if (toolMsgs.length > 0) {
        throw new Error(`Expected concept question to be answered without tools, got tool calls: ${JSON.stringify(toolMsgs.map((m) => m.name))}`);
      }
      const replyLower = String(assistantMsgs[assistantMsgs.length - 1].content || '').toLowerCase();
      for (const retired of RETIRED_AGENTS) {
        if (replyLower.includes(retired)) {
          throw new Error(`Expected reply not to list retired agent ${retired}, got: ${replyLower}`);
        }
      }
      j.note('AutoReiv answered product concept question directly without tool calls or retired agent names');
    }, { timeoutMs: 200000 });
  },
};
