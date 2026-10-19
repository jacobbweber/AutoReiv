/**
 * CARD-725 journey:
 * 1) Verifies GET /api/agents exposes only the 3-agent roster (autoreiv, tutor, direct), POST /api/agents rejects agent-builder (422), and GET /api/capabilities/tree includes capability-authoring with propose_skill, commit_skill, and write_skill_file.
 * 2) Opens Agent Studio and Capabilities Studio to verify capability-authoring is ticked on AutoReiv and rendered in the Capabilities tree.
 */
import { clickExpect, waitFor } from './lib/runner.mjs';
import { getJson, openApp } from './lib/app.mjs';

export default {
  id: 'card-725-modernize-capability-authoring-contracts',
  card: 'CARD-725',
  title: '3-agent roster, retired agent rejection, and AutoReiv capability-authoring contract',
  allow: [],
  async run(j, { page, request, base }) {
    await j.step('API roster exposes only autoreiv/tutor/direct, rejects agent-builder, and lists capability-authoring in /api/capabilities/tree', async () => {
      const agents = await getJson(request, `${base}/api/agents`);
      const ids = (Array.isArray(agents) ? agents : []).map((a) => a.id).sort();
      for (const retired of ['agent-builder', 'developer', 'toolsmith', 'architect']) {
        if (ids.includes(retired)) {
          throw new Error(`Retired agent '${retired}' present in /api/agents: ${ids.join(', ')}`);
        }
      }
      for (const expected of ['autoreiv', 'direct', 'tutor']) {
        if (!ids.includes(expected)) {
          throw new Error(`Expected agent '${expected}' missing from /api/agents: ${ids.join(', ')}`);
        }
      }

      const rejectRes = await request.post(`${base}/api/agents`, {
        data: {
          id: 'agent-builder',
          name: 'Agent Builder',
          description: 'retired',
          system_prompt: 'retired',
        },
      });
      if (rejectRes.status() !== 422) {
        throw new Error(`Expected 422 rejecting agent-builder creation, got ${rejectRes.status()}`);
      }

      const tree = await getJson(request, `${base}/api/capabilities/tree`);
      const capSkill = (tree.skills || []).find((s) => s.id === 'capability-authoring');
      if (!capSkill) {
        throw new Error('capability-authoring missing from /api/capabilities/tree');
      }
      const declared = new Set(capSkill.declared_tools || []);
      for (const tool of ['propose_skill', 'commit_skill', 'write_skill_file']) {
        if (!declared.has(tool)) {
          throw new Error(`Expected ${tool} in capability-authoring declared_tools`);
        }
      }

      await openApp(page, base);
    }, { timeoutMs: 30000 });

    await j.step('Agent Studio shows capability-authoring ticked on AutoReiv and Capabilities Studio renders its folder', async () => {
      await clickExpect(
        page.locator('#dock-agents'),
        () => page.locator('#forgeAgentSelect').isVisible(),
        { label: 'Agents dock', what: 'Agent Studio', timeoutMs: 10000 }
      );
      await page.selectOption('#forgeAgentSelect', 'autoreiv');

      const capsDetails = page.locator('details[data-section="capabilities"]');
      if (!(await capsDetails.evaluate((el) => el.open).catch(() => true))) {
        await capsDetails.locator('summary').first().click();
      }

      const pill = page.locator('.forge-skill-pill[data-skill-id="capability-authoring"]').first();
      const ticked = await waitFor(
        async () => (await pill.getAttribute('aria-pressed').catch(() => null)) === 'true',
        { timeoutMs: 10000 }
      );
      if (!ticked) {
        throw new Error('Expected capability-authoring skill pill to be ticked on autoreiv in Agent Studio');
      }
      await pill.scrollIntoViewIfNeeded().catch(() => {});

      await clickExpect(
        page.locator('#dock-capabilities'),
        () => page.locator('#view-capabilities').isVisible(),
        { label: 'Capabilities dock', what: 'Capabilities Studio', timeoutMs: 10000 }
      );
      const treeHasCap = await waitFor(
        async () => {
          const text = await page.locator('#view-capabilities').innerText().catch(() => '');
          return text.includes('Capability Authoring') || text.includes('capability-authoring');
        },
        { timeoutMs: 10000 }
      );
      if (!treeHasCap) {
        throw new Error('Expected Capability Authoring to appear in Capabilities Studio');
      }
    }, { timeoutMs: 35000 });
  },
};
