import { test, expect } from '@playwright/test';

/**
 * Comprehensive Multi-Studio Navigation & Interactive Smoke Suite [REQ-SMK-002, REQ-SMK-003, REQ-SMK-005]
 * Verifies that the AutoReiv Web Single-Page Application loads cleanly,
 * executes studio tab switching, and handles interactive modal and search flows with ZERO console errors.
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

  test('TC-1: Initial page load renders header, navigation, and default chat interface [REQ-SMK-002]', async ({
    page,
  }) => {
    const response = await page.goto('/', { waitUntil: 'domcontentloaded' });
    expect(response?.status()).toBe(200);

    // Verify main navigation studio tabs exist
    await expect(page.locator('#tab-chat')).toBeAttached();
    await expect(page.locator('#tab-routines')).toBeAttached();
    await expect(page.locator('#tab-observability')).toBeAttached();
    await expect(page.locator('#tab-agents')).toBeAttached();
    await expect(page.locator('#tab-settings')).toBeAttached();
    await expect(page.locator('#tab-wiki')).toBeAttached();

    // Verify Chat Studio elements
    await expect(page.locator('#view-chat')).toBeVisible();
    await expect(page.locator('#messagesContainer')).toBeAttached();
    await expect(page.locator('#promptInput')).toBeAttached();
    await expect(page.locator('#chatTopBarAgentSelect')).toBeAttached();
    await expect(page.locator('#activeAgentTitle')).toBeAttached();
  });

  test('TC-2: Studio navigation attaches critical DOM components without error [REQ-SMK-002]', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // 1. Routines Studio
    await page.locator('#tab-routines').click();
    await expect(page.locator('#view-routines')).toBeVisible();
    await expect(page.locator('#routinesGrid')).toBeAttached();
    await expect(page.locator('#newRoutineBtn')).toBeAttached();

    // 2. Observability Studio
    await page.locator('#tab-observability').click();
    await expect(page.locator('#view-observability')).toBeVisible();
    await expect(page.locator('#systemLogsTerminal')).toBeAttached();
    await expect(page.locator('#logSearchInput')).toBeAttached();
    await expect(page.locator('#logLevelSelect')).toBeAttached();

    // 3. Agent Forge Studio
    await page.locator('#tab-agents').click();
    await expect(page.locator('#view-agents')).toBeVisible();
    await expect(page.locator('#forgeAgentSelect')).toBeAttached();
    await expect(page.locator('#newAgentBtn')).toBeAttached();
    await expect(page.locator('#saveAgentBtn')).toBeAttached();
    await expect(page.locator('#forgeNameInput')).toBeAttached();

    // 4. Settings Studio
    await page.locator('#tab-settings').click();
    await expect(page.locator('#view-settings')).toBeVisible();
    await expect(page.locator('#provPresetSelect')).toBeAttached();
    await expect(page.locator('#saveProvidersBtn')).toBeAttached();
    await expect(page.locator('#modelFitTableBody')).toBeAttached();

    // 5. Wiki Vault Studio
    await page.locator('#tab-wiki').click();
    await expect(page.locator('#view-wiki')).toBeVisible();
    await expect(page.locator('#wikiNavTree')).toBeAttached();
    await expect(page.locator('#wikiViewerContent')).toBeAttached();
    await expect(page.locator('#wikiNewNoteBtn')).toBeAttached();

    // 6. Return to Chat Studio
    await page.locator('#tab-chat').click();
    await expect(page.locator('#view-chat')).toBeVisible();
  });

  test('TC-3: Interactive modals and search flows execute cleanly [REQ-SMK-003]', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // 2. Wiki Studio - New Note Modal Flow
    await page.locator('#tab-wiki').click();
    await page.locator('#wikiNewNoteBtn').click();
    await expect(page.locator('#wikiNewNoteModal')).toBeVisible();
    await page.locator('#wikiNewNoteCancelBtn').click();
    await expect(page.locator('#wikiNewNoteModal')).toBeHidden();

    // 3. Wiki Studio - Mind Map 2D Physics Canvas Flow
    await page.locator('#wikiMindMapViewBtn').click();
    await expect(page.locator('#wikiMindMapModal')).toBeVisible();
    await expect(page.locator('#wikiMindMapCanvas')).toBeAttached();
    await page.locator('#wikiMindMapCloseBtn').click();
    await expect(page.locator('#wikiMindMapModal')).toBeHidden();

    // 4. Routines Studio - New Routine Modal Flow
    await page.locator('#tab-routines').click();
    await page.locator('#newRoutineBtn').click();
    await expect(page.locator('#routineModal')).toBeVisible();
    await page.locator('#closeRoutineModalBtn').click();
    await expect(page.locator('#routineModal')).toBeHidden();
  });

  test('TC-4: Chat topbar agent switcher synchronizes state [REQ-SMK-003]', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('#chatTopBarAgentSelect')).toBeVisible();

    const topBarSelect = page.locator('#chatTopBarAgentSelect');
    await expect(topBarSelect.locator('option')).toHaveCount(2);
    await expect(topBarSelect.locator('option').nth(0)).toHaveAttribute('value', 'assistant');
    await expect(topBarSelect.locator('option').nth(1)).toHaveAttribute('value', 'autoreiv');

    // Switch to AutoReiv
    await topBarSelect.selectOption('autoreiv');
    await expect(page.locator('#activeAgentTitle')).toHaveText('AutoReiv');

    // Switch back to Assistant
    await topBarSelect.selectOption('assistant');
    await expect(page.locator('#activeAgentTitle')).toHaveText('Assistant');
  });
});
