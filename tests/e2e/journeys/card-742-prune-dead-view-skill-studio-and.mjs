/**
 * CARD-742: Prune dead #view-skill-studio and #view-tools-studio DOM and JS remnants.
 *
 * Verifies on both desktop and phone:
 * 1) #view-skill-studio, #view-tools-studio, #skillStudio, and #toolsStudio are completely
 *    absent from the DOM (0 nodes), while #view-capabilities is the single Capabilities view.
 * 2) Opening Capabilities Studio displays the Agora skill tree and file inspector cleanly
 *    with zero horizontal overflow.
 * 3) Selecting mcp/ (MCP Servers) opens #capabilitiesMcpPane and populates #capabilitiesMcpAgentSelect
 *    under Agent scope with zero horizontal overflow.
 */
import { waitFor } from './lib/runner.mjs';
import { openApp } from './lib/app.mjs';

async function openCapabilities(page) {
  if (await page.locator('#view-capabilities').isVisible().catch(() => false)) {
    return;
  }
  const dockBtn = page.locator('#dock-capabilities');
  if (await dockBtn.isVisible().catch(() => false)) {
    await dockBtn.click();
  } else {
    const mobileMenu = page.locator('#mobileMenuBtn');
    if (await mobileMenu.isVisible().catch(() => false)) {
      await mobileMenu.click();
    }
    await page.locator('#tab-capabilities').click();
  }
  await page.locator('#view-capabilities').waitFor({ state: 'visible', timeout: 15000 });
}

export default {
  id: 'card-742-prune-dead-view-skill-studio-and',
  card: 'CARD-742',
  title: 'Prune dead #view-skill-studio and #view-tools-studio DOM and JS remnants',
  async run(j, { page, base, viewport }) {
    await j.step('1. Verify dead #view-skill-studio and #view-tools-studio DOM sections are absent', async () => {
      await openApp(page, base);
      const counts = await page.evaluate(() => ({
        skillView: document.querySelectorAll('#view-skill-studio, #skillStudio').length,
        toolsView: document.querySelectorAll('#view-tools-studio, #toolsStudio').length,
        capView: document.querySelectorAll('#view-capabilities').length,
      }));
      if (counts.skillView !== 0) {
        throw new Error(`Expected 0 #view-skill-studio/#skillStudio nodes, found ${counts.skillView}`);
      }
      if (counts.toolsView !== 0) {
        throw new Error(`Expected 0 #view-tools-studio/#toolsStudio nodes, found ${counts.toolsView}`);
      }
      if (counts.capView !== 1) {
        throw new Error(`Expected 1 #view-capabilities node, found ${counts.capView}`);
      }
      j.note(`Verified 0 legacy Skill/Tools Studio DOM nodes and 1 #view-capabilities node on ${viewport.name}`);
    });

    await j.step('2. Open Capabilities Studio and verify Agora skill tree and New Skill bar', async () => {
      await openCapabilities(page);
      await waitFor(
        async () => {
          const text = await page.locator('#capabilitiesTreeList').innerText().catch(() => '');
          return text.includes('mcp/') && text.includes('SKILL.md');
        },
        { timeoutMs: 15000, label: 'Capabilities tree populated with skills and mcp/' },
      );

      await page.locator('#capabilitiesNewSkillBtn').click();
      await page.locator('#capabilitiesCreateBar').waitFor({ state: 'visible', timeout: 5000 });
      await page.locator('#capabilitiesCreateCancelBtn').click();
      await page.locator('#capabilitiesCreateBar').waitFor({ state: 'hidden', timeout: 5000 });

      const overflow = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
      }));
      if (overflow.scrollWidth > overflow.innerWidth + 1) {
        throw new Error(
          `Horizontal overflow in #view-capabilities on ${viewport.name}: ${overflow.scrollWidth} > ${overflow.innerWidth}`,
        );
      }
      j.note(`Capabilities Studio tree and create bar verified on ${viewport.name} (${overflow.scrollWidth}px <= ${overflow.innerWidth}px)`);
    });

    await j.step('3. Select mcp/ (MCP Servers) in Capabilities Studio and verify MCP inspector pane', async () => {
      const mcpNode = page.locator('[data-action="select-mcp-node"]').first();
      await mcpNode.click();
      await page.locator('#capabilitiesMcpPane').waitFor({ state: 'visible', timeout: 10000 });

      await page.locator('#capabilitiesMcpScopeSelect').selectOption('agent');
      await page.locator('#capabilitiesMcpAgentField').waitFor({ state: 'visible', timeout: 5000 });

      const agentOptionsCount = await page.locator('#capabilitiesMcpAgentSelect option').count();
      if (agentOptionsCount < 2) {
        throw new Error(`Expected #capabilitiesMcpAgentSelect to list agents, found ${agentOptionsCount} options`);
      }

      await page.locator('#capabilitiesMcpScopeSelect').selectOption('platform');

      const overflow = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
      }));
      if (overflow.scrollWidth > overflow.innerWidth + 1) {
        throw new Error(
          `Horizontal overflow in #capabilitiesMcpPane on ${viewport.name}: ${overflow.scrollWidth} > ${overflow.innerWidth}`,
        );
      }
      j.note(`Verified #capabilitiesMcpPane (${agentOptionsCount} agent options) on ${viewport.name}`);
    });
  },
};
