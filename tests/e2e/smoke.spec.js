import { test, expect } from '@playwright/test';

/**
 * Comprehensive Multi-Studio Navigation & Interactive Smoke Suite [REQ-SMK-002, REQ-SMK-003, REQ-SMK-005]
 * Verifies that the AutoReiv Web Agent Desktop loads cleanly,
 * executes studio launching via dock, and handles interactive modal and search flows with ZERO console errors.
 */
test.describe('AutoReiv Web SPA Comprehensive Smoke Suite', () => {
  test.beforeEach(async ({ page }) => {
    page.context()._pageErrors = [];
    page.context()._consoleErrors = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        page.context()._consoleErrors.push(msg.text());
      }
    });

    page.on('pageerror', (exception) => {
      page.context()._pageErrors.push(exception.message);
    });
  });

  test.afterEach(async ({ page }) => {
    const pageErrors = page.context()._pageErrors || [];
    const consoleErrors = page.context()._consoleErrors || [];

    expect(pageErrors, `Uncaught page errors detected: ${pageErrors.join(' | ')}`).toEqual([]);
    expect(consoleErrors, `Console errors detected: ${consoleErrors.join(' | ')}`).toEqual([]);
  });

  test('TC-1: Initial page load renders desktop stage, dock launcher, and opens Chat window [REQ-SMK-002]', async ({
    page,
  }) => {
    const response = await page.goto('/', { waitUntil: 'domcontentloaded' });
    expect(response?.status()).toBe(200);

    // Verify Agent Desktop environment exists
    await expect(page.locator('#desktopStage')).toBeVisible();
    await expect(page.locator('#desktopDock')).toBeVisible();
    await expect(page.locator('#desktopWindowLayer')).toBeAttached();

    // Verify dock launchers exist
    await expect(page.locator('#dock-chat')).toBeVisible();
    await expect(page.locator('#dock-wiki')).toBeVisible();
    await expect(page.locator('#dock-projects')).toBeVisible();
    await expect(page.locator('#dock-agents')).toBeVisible();
    await expect(page.locator('#dock-factory')).toBeVisible();
    await expect(page.locator('#dock-routines')).toBeVisible();
    await expect(page.locator('#dock-observability')).toBeVisible();
    await expect(page.locator('#dock-settings')).toBeVisible();

    // Launch Chat Studio window from dock
    await page.locator('#dock-chat').click();
    await expect(page.locator('#desktopWin-chat')).toBeVisible();
    await expect(page.locator('#view-chat')).toBeVisible();
    await expect(page.locator('#messagesContainer')).toBeAttached();
    await expect(page.locator('#promptInput')).toBeAttached();
    await expect(page.locator('#chatTopBarAgentSelect')).toBeAttached();
    await expect(page.locator('#activeAgentTitle')).toBeAttached();
    await expect(page.locator('#artifactModal')).toBeAttached();
  });

  test('TC-2: Studio navigation via dock launches critical window components without error [REQ-SMK-002]', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // 1. Routines Studio
    await page.locator('#dock-routines').click();
    await expect(page.locator('#desktopWin-routines')).toBeVisible();
    await expect(page.locator('#view-routines')).toBeVisible();
    await expect(page.locator('#routinesGrid')).toBeAttached();
    await expect(page.locator('#newRoutineBtn')).toBeAttached();

    // 2. Observability Studio
    await page.locator('#dock-observability').click();
    await expect(page.locator('#desktopWin-observability')).toBeVisible();
    await expect(page.locator('#view-observability')).toBeVisible();
    await expect(page.locator('#systemLogsTerminal')).toBeAttached();
    await expect(page.locator('#logSearchInput')).toBeAttached();
    await expect(page.locator('#logLevelSelect')).toBeAttached();

    // 3. Agent Studio
    await page.locator('#dock-agents').click();
    await expect(page.locator('#desktopWin-agents')).toBeVisible();
    await expect(page.locator('#view-agents')).toBeVisible();
    await expect(page.locator('#forgeAgentSelect')).toBeAttached();
    await expect(page.locator('#newAgentBtn')).toBeAttached();
    await expect(page.locator('#saveAgentBtn')).toBeAttached();
    await expect(page.locator('#deleteAgentBtn')).toBeAttached();
    await expect(page.locator('#forgeNameInput')).toBeAttached();
    await expect(page.locator('#forgeProviderSelect')).toBeAttached();
    await expect(page.locator('#forgeAgentModelSelect')).toBeAttached();
    await expect(page.locator('#forgePurposeSelect')).toHaveCount(0);
    await expect(page.locator('#forgeModelSelect')).toHaveCount(0);
    await expect(page.locator('#tab-skills')).toHaveCount(0);
    await expect(page.locator('#studioRunbookBody')).toBeAttached();
    await expect(page.getByRole('heading', { name: 'Agent Studio' })).toBeAttached();

    // 4. Settings Studio
    await page.locator('#dock-settings').click();
    await expect(page.locator('#desktopWin-settings')).toBeVisible();
    await expect(page.locator('#view-settings')).toBeVisible();
    await expect(page.locator('#provPresetSelect')).toBeAttached();
    await expect(page.locator('#saveProvidersBtn')).toBeAttached();
    await expect(page.locator('#saveMatrixBtn')).toHaveCount(0);
    await expect(page.locator('#matrixGeneral')).toHaveCount(0);
    await expect(page.locator('#addMcpServerBtn')).toBeAttached();
    await expect(page.locator('#addMcpEnvRowBtn')).toBeAttached();
    await expect(page.locator('#testMcpServerBtn')).toBeAttached();
    await expect(page.locator('#mcpServerList')).toBeAttached();

    // 5. Wiki Vault Studio
    await page.locator('#dock-wiki').click();
    await expect(page.locator('#desktopWin-wiki')).toBeVisible();
    await expect(page.locator('#view-wiki')).toBeVisible();
    await expect(page.locator('#wikiNavTree')).toBeAttached();
    await expect(page.locator('#wikiViewerContent')).toBeAttached();
    await expect(page.locator('#wikiNewNoteBtn')).toBeAttached();

    // 6. Return to Chat Studio
    await page.locator('#dock-chat').click();
    await expect(page.locator('#desktopWin-chat')).toBeVisible();
    await expect(page.locator('#view-chat')).toBeVisible();
  });

  test('TC-3: Interactive modals and search flows execute cleanly [REQ-SMK-003]', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // 1. Wiki Studio - New Note Modal Flow
    await page.locator('#dock-wiki').click();
    await expect(page.locator('#desktopWin-wiki')).toBeVisible();
    await page.locator('#wikiNewNoteBtn').click();
    await expect(page.locator('#wikiNewNoteModal')).toBeVisible();
    await page.locator('#wikiNewNoteCancelBtn').click();
    await expect(page.locator('#wikiNewNoteModal')).toBeHidden();

    // 2. Wiki Studio - Mind Map 2D Physics Canvas Flow
    await page.locator('#wikiMindMapViewBtn').click();
    await expect(page.locator('#wikiMindMapModal')).toBeVisible();
    await expect(page.locator('#wikiMindMapCanvas')).toBeAttached();
    await page.locator('#wikiMindMapCloseBtn').click();
    await expect(page.locator('#wikiMindMapModal')).toBeHidden();

    // 3. Routines Studio - New Routine Modal Flow
    await page.locator('#dock-routines').click();
    await expect(page.locator('#desktopWin-routines')).toBeVisible();
    await page.locator('#newRoutineBtn').click();
    await expect(page.locator('#routineModal')).toBeVisible();
    await page.locator('#closeRoutineModalBtn').click();
    await expect(page.locator('#routineModal')).toBeHidden();
  });

  test('TC-4: Chat topbar agent switcher synchronizes state [REQ-SMK-003]', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // Open Chat window from dock
    await page.locator('#dock-chat').click();
    await expect(page.locator('#desktopWin-chat')).toBeVisible();
    await expect(page.locator('#chatTopBarAgentSelect')).toBeVisible();

    const topBarSelect = page.locator('#chatTopBarAgentSelect');
    await expect(topBarSelect.locator('option[value="assistant"]')).toHaveCount(1);
    await expect(topBarSelect.locator('option[value="autoreiv"]')).toHaveCount(1);

    // Switch to AutoReiv
    await topBarSelect.selectOption('autoreiv');
    await expect(page.locator('#activeAgentTitle')).toHaveText('AutoReiv');

    // Switch back to Assistant
    await topBarSelect.selectOption('assistant');
    await expect(page.locator('#activeAgentTitle')).toHaveText('Assistant');
  });
});
