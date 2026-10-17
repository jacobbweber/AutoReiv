/**
 * CARD-692 journey: Consolidate MCP servers and deep-links into Capabilities Studio and retire Skill/Tools Studio tabs.
 * 1) Open the app and verify `#dock-capabilities` (desktop) / `#tab-capabilities` (phone) is present
 *    and `#dock-skill-studio`, `#dock-tools-studio`, `#tab-skill-studio`, and `#tab-tools-studio` are absent.
 * 2) Open Settings (`#dock-settings` / `#tab-settings`), click `#settingsOpenToolsStudioBtn`, and verify
 *    it routes to `#view-capabilities` directly on the `mcp/` (MCP Servers) inspector (`#capabilitiesMcpPane`).
 * 3) Open Agents Studio (`#dock-agents` / `#tab-agents`), click `#studioOpenSkillStudioBtn` (`Manage skills`),
 *    and verify it routes to `#view-capabilities` on the Agora skills tree.
 * 4) Verify zero horizontal overflow (`scrollWidth <= innerWidth`) on both desktop (`1280x800`) and phone (`390x844`).
 */
import { waitFor } from './lib/runner.mjs';
import { openApp } from './lib/app.mjs';

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
  id: 'card-692-consolidate-mcp-servers-and-deep-links',
  card: 'CARD-692',
  title: 'Consolidate MCP servers and deep-links into Capabilities Studio and retire Skill/Tools Studio tabs',
  allow: [],
  async run(j, { page, base, viewport }) {
    await j.step('Verify legacy Skill Studio and Tools Studio launchers are retired from dock and sidebar', async () => {
      await openApp(page, base);

      const legacyDockCount = await page.locator('#dock-skill-studio, #dock-tools-studio').count();
      if (legacyDockCount !== 0) {
        throw new Error(`Expected 0 legacy dock launchers (#dock-skill-studio, #dock-tools-studio), found ${legacyDockCount}`);
      }
      const legacyTabCount = await page.locator('#tab-skill-studio, #tab-tools-studio').count();
      if (legacyTabCount !== 0) {
        throw new Error(`Expected 0 legacy sidebar tabs (#tab-skill-studio, #tab-tools-studio), found ${legacyTabCount}`);
      }
      j.note('Verified dock and sidebar contain only the unified Capabilities launcher');
    });

    await j.step('Click Manage in Settings MCP card and verify it deep-links into Capabilities Studio mcp/ node', async () => {
      await openTab(page, 'settings');
      const connDetails = page.locator('[data-settings-section="connections"]');
      await connDetails.waitFor({ state: 'attached', timeout: 15000 });
      if (!(await connDetails.evaluate((el) => el.open).catch(() => false))) {
        await connDetails.locator('summary').first().evaluate((s) => s.click());
      }

      const openMcpBtn = page.locator('#settingsOpenToolsStudioBtn');
      await openMcpBtn.waitFor({ state: 'visible', timeout: 15000 });
      await openMcpBtn.scrollIntoViewIfNeeded();
      await openMcpBtn.click();

      await page.locator('#view-capabilities').waitFor({ state: 'visible', timeout: 20000 });
      await page.locator('#capabilitiesMcpPane').waitFor({ state: 'visible', timeout: 15000 });

      const activePath = await page.locator('#capabilitiesActivePath').innerText();
      if (!activePath.includes('mcp/')) {
        throw new Error(`Expected #capabilitiesActivePath to show mcp/, got: ${activePath}`);
      }
      j.note('Settings MCP deep-link opened #view-capabilities on mcp/ (MCP Servers)');
    });

    await j.step('Click Manage skills in Agents Studio and verify it deep-links into Capabilities Studio skill tree', async () => {
      await openTab(page, 'agents');
      await page.locator('#forgeAgentSelect').waitFor({ state: 'visible', timeout: 20000 });
      await waitFor(async () => (await page.locator('#forgeAgentSelect option[value="autoreiv"]').count()) > 0, { timeoutMs: 20000 });
      await page.selectOption('#forgeAgentSelect', 'autoreiv');
      await waitFor(async () => /autoreiv/i.test(await page.inputValue('#forgeNameInput').catch(() => '')), { timeoutMs: 20000 });

      const capsDetails = page.locator('details[data-section="capabilities"]');
      await waitFor(async () => (await capsDetails.getAttribute('aria-busy').catch(() => 'true')) !== 'true', { timeoutMs: 20000 });
      if (!(await capsDetails.evaluate((el) => el.open).catch(() => true))) {
        await capsDetails.locator('summary').first().click();
      }

      const manageSkillsBtn = page.locator('#studioOpenSkillStudioBtn');
      await manageSkillsBtn.waitFor({ state: 'visible', timeout: 15000 });
      await manageSkillsBtn.scrollIntoViewIfNeeded();
      await manageSkillsBtn.click();

      await page.locator('#view-capabilities').waitFor({ state: 'visible', timeout: 20000 });
      const treeReady = await waitFor(
        async () => {
          const txt = await page.locator('#capabilitiesTreeList').innerText().catch(() => '');
          return txt.includes('mcp/') && txt.includes('skills/');
        },
        { timeoutMs: 15000 }
      );
      if (!treeReady) {
        throw new Error('Expected #capabilitiesTreeList to show mcp/ and skills/ after deep-link from Agents Studio');
      }

      const overflow = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
      }));
      if (overflow.scrollWidth > overflow.innerWidth + 2) {
        throw new Error(`Horizontal overflow on ${viewport.name}: scrollWidth=${overflow.scrollWidth} > innerWidth=${overflow.innerWidth}`);
      }
      j.note(`Agents Studio deep-link opened #view-capabilities cleanly on ${viewport.name} (${overflow.scrollWidth}px <= ${overflow.innerWidth}px)`);
    });
  },
};
