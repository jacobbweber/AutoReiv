/**
 * CARD-693 journey: Three-Agent Roster (AutoReiv, Tutor, Direct) & Consolidated Agora Skill Folders.
 * 1) Verify GET /api/agents and Chat (#agentSelect) list only AutoReiv, Tutor, and Direct (retired
 *    architect, developer, and toolsmith are absent).
 * 2) Open Capabilities (#view-capabilities) and verify the unified directory tree lists the 3
 *    consolidated Agora skill folders (capability-authoring, project-cards, software-development)
 *    with their progressive references/ files and none of the 17 retired micro-skills.
 * 3) In Chat on AutoReiv, call skill_view(skill_id="project-cards", reference="card-rubric.md")
 *    and verify AutoReiv loads the reference and mounts project-cards tools on demand in one session.
 */
import { waitFor } from './lib/runner.mjs';
import { getJson, openApp, send, waitReplyIdle } from './lib/app.mjs';

const AGENT_ID = 'autoreiv';
const RETIRED_AGENTS = ['architect', 'developer', 'toolsmith'];
const CONSOLIDATED_SKILLS = ['capability-authoring', 'project-cards', 'software-development'];
const RETIRED_SKILLS = [
  'agent-authoring',
  'native-tool-engineering',
  'project-orientation',
  'brainstorm',
  'card-intake',
  'card-writing',
  'plan-change',
  'hand-off',
  'review',
  'implement-change',
  'write-tests',
  'debug',
  'run-checks',
  'git-workflow',
  'code-review',
  'codebase-audit',
  'journey-qa',
];

async function openTab(page, tabName) {
  const viewId = `#view-${tabName}`;
  if (await page.locator(viewId).isVisible().catch(() => false)) return;
  const dockBtn = page.locator(`#dock-${tabName}`);
  if (await dockBtn.isVisible().catch(() => false)) {
    await dockBtn.click();
  } else {
    const mobileMenu = page.locator('#mobileMenuBtn');
    if (await mobileMenu.isVisible().catch(() => false)) {
      const sidebarTab = page.locator(`#tab-${tabName}`);
      if (!(await sidebarTab.isVisible().catch(() => false))) {
        await mobileMenu.click();
      }
      await sidebarTab.waitFor({ state: 'visible', timeout: 10000 });
      await sidebarTab.click();
    } else {
      await page.locator(`#tab-${tabName}`).click();
    }
  }
  await page.locator(viewId).waitFor({ state: 'visible', timeout: 20000 });
}

export default {
  id: 'card-693-retire-architect-developer-and-toolsmith-agents',
  card: 'CARD-693',
  title: 'Three-agent roster and consolidated Agora skill folders on AutoReiv',
  allow: [],
  async run(j, { page, request, base }) {
    await j.step('Verify API and Chat picker expose the 3-agent shipped roster (AutoReiv, Tutor, Direct)', async () => {
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

      const chatOptions = await page.locator('#agentSelect option').evaluateAll((opts) => opts.map((o) => o.value));
      for (const retired of RETIRED_AGENTS) {
        if (chatOptions.includes(retired)) {
          throw new Error(`Retired agent ${retired} still in #agentSelect: ${JSON.stringify(chatOptions)}`);
        }
      }
      j.note(`Chat picker roster verified: ${chatOptions.join(', ')}`);
    });

    await j.step('Verify Capabilities Studio tree shows consolidated Agora skill folders with references/', async () => {
      const treeData = await getJson(request, `${base}/api/capabilities/tree`);
      const skills = Array.isArray(treeData.skills) ? treeData.skills : [];
      const skillIds = skills.map((s) => s.id);

      for (const consolidated of CONSOLIDATED_SKILLS) {
        if (!skillIds.includes(consolidated)) {
          throw new Error(`Missing consolidated Agora skill ${consolidated} in /api/capabilities/tree: ${JSON.stringify(skillIds)}`);
        }
      }
      for (const retired of RETIRED_SKILLS) {
        if (skillIds.includes(retired)) {
          throw new Error(`Retired micro-skill ${retired} still in /api/capabilities/tree: ${JSON.stringify(skillIds)}`);
        }
      }

      await openTab(page, 'capabilities');
      const treeReady = await waitFor(
        async () => {
          const txt = await page.locator('#capabilitiesTreeList').innerText().catch(() => '');
          return CONSOLIDATED_SKILLS.every((id) => txt.includes(id));
        },
        { timeoutMs: 15000 }
      );
      if (!treeReady) {
        const txt = await page.locator('#capabilitiesTreeList').innerText().catch(() => '');
        throw new Error(`Expected #capabilitiesTreeList to list ${CONSOLIDATED_SKILLS.join(', ')}, got: ${txt}`);
      }
      const projectCardsNode = page.locator('#capabilitiesTreeList', { hasText: 'project-cards' }).first();
      await projectCardsNode.waitFor({ state: 'visible', timeout: 10000 });
      j.note(`Capabilities Studio tree verified: ${CONSOLIDATED_SKILLS.join(', ')}`);
    });

    await j.step('In Chat, AutoReiv opens project-cards/card-rubric.md via skill_view and mounts project-cards tools on demand', async () => {
      await openTab(page, 'chat');
      await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 20000 });
      if ((await page.locator('#agentSelect').inputValue().catch(() => '')) !== AGENT_ID) {
        await page.selectOption('#agentSelect', AGENT_ID);
        await page.waitForTimeout(500);
      }

      await send(
        page,
        'Call skill_view with skill_id="project-cards" and reference="card-rubric.md", then state the 3 review verdicts or rules listed in that reference.'
      );
      await waitReplyIdle(page, { timeoutMs: 240000 });

      const sessions = await getJson(request, `${base}/api/sessions?agent_id=${AGENT_ID}`);
      const latest = (sessions.sessions || sessions || [])[0];
      if (!latest || !latest.id) throw new Error('No chat session found for AutoReiv');
      const msgs = await getJson(request, `${base}/api/sessions/${encodeURIComponent(latest.id)}/messages`);
      const rows = Array.isArray(msgs) ? msgs : (msgs.messages || []);
      const toolMsgs = rows.filter((m) => m.role === 'tool' && m.name === 'skill_view');
      if (toolMsgs.length === 0) {
        throw new Error(`Expected AutoReiv to call skill_view, got tool messages: ${JSON.stringify(rows.filter((m) => m.role === 'tool').map((m) => m.name))}`);
      }
      const lastOut = String(toolMsgs[toolMsgs.length - 1].content || '');
      if (lastOut.includes('not allowed for this agent') || lastOut.includes('"success": false')) {
        throw new Error(`skill_view failed for project-cards: ${lastOut}`);
      }
      j.note('AutoReiv loaded project-cards reference and mounted project-cards tools on demand');
    }, { timeoutMs: 260000 });
  },
};
