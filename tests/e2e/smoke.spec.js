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

  test('TC-5: Sessions window cleanup, studio scrolling, and window corner resize [CARD-207]', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // 1. Sessions Window: opens from dock, redundant headers and studio grid hidden, sessionList attached
    await page.locator('#dock-sessions').click();
    await page.waitForTimeout(200);
    await expect(page.locator('#desktopWin-sessions')).toBeVisible();
    await expect(page.locator('#sidebar')).toBeVisible();
    await expect(page.locator('#sidebarDrawerHeader')).toBeHidden();
    await expect(page.locator('#sidebarNav')).toBeHidden();
    await expect(page.locator('#sessionList')).toBeAttached();

    const winBox = await page.locator('#desktopWin-sessions').boundingBox();
    const sideBox = await page.locator('#sidebar').boundingBox();
    expect(winBox).toBeTruthy();
    expect(sideBox).toBeTruthy();
    if (winBox && sideBox) {
      // Sidebar should sit directly inside the window body beneath titlebar
      expect(Math.abs(sideBox.x - winBox.x)).toBeLessThan(5);
      expect(sideBox.y).toBeGreaterThanOrEqual(winBox.y);
    }

    // Drag Sessions window by titlebar and verify sidebar moves synchronously
    const titleHandle = page.locator('#desktopWin-sessions .desktop-win-titlebar');
    const titleBox = await titleHandle.boundingBox();
    expect(titleBox).toBeTruthy();
    if (titleBox && winBox && sideBox) {
      await page.mouse.move(titleBox.x + titleBox.width / 2, titleBox.y + titleBox.height / 2);
      await page.mouse.down();
      await page.mouse.move(titleBox.x + titleBox.width / 2 + 80, titleBox.y + titleBox.height / 2 + 60, { steps: 5 });
      await page.mouse.up();
      await page.waitForTimeout(200);

      const movedWinBox = await page.locator('#desktopWin-sessions').boundingBox();
      const movedSideBox = await page.locator('#sidebar').boundingBox();
      expect(movedWinBox).toBeTruthy();
      expect(movedSideBox).toBeTruthy();
      if (movedWinBox && movedSideBox) {
        expect(movedWinBox.x).toBeGreaterThan(winBox.x + 40);
        expect(movedSideBox.x).toBeGreaterThan(sideBox.x + 40);
        expect(Math.abs(movedSideBox.x - movedWinBox.x)).toBeLessThan(5);
      }
    }

    // 2. Settings Studio: opens from dock, content is vertically scrollable (overflow-y: auto)
    await page.locator('#dock-settings').click();
    await expect(page.locator('#desktopWin-settings')).toBeVisible();
    await expect(page.locator('#view-settings')).toBeVisible();
    const settingsOverflow = await page.locator('#view-settings').evaluate((el) => {
      const style = window.getComputedStyle(el);
      return style.overflowY;
    });
    expect(settingsOverflow).toBe('auto');

    // 3. Routines & Observability: overflow-y: auto verified
    await page.locator('#dock-routines').click();
    const routinesOverflow = await page.locator('#view-routines').evaluate((el) => window.getComputedStyle(el).overflowY);
    expect(routinesOverflow).toBe('auto');

    // 4. Corner resize: bottom-right handle exists, is attached and resizes window
    const chatWin = page.locator('#desktopWin-chat');
    await page.locator('#dock-chat').click();
    await expect(chatWin).toBeVisible();

    const resizeHandle = chatWin.locator('.desktop-win-resize-se');
    await expect(resizeHandle).toBeAttached();

    const initialBox = await chatWin.boundingBox();
    expect(initialBox).toBeTruthy();

    if (initialBox) {
      const handleBox = await resizeHandle.boundingBox();
      expect(handleBox).toBeTruthy();
      if (handleBox) {
        const hx = handleBox.x + handleBox.width / 2;
        const hy = handleBox.y + handleBox.height / 2;

        // Verify handle receives pointer events
        const topElement = await page.evaluate(({ x, y }) => {
          const el = document.elementFromPoint(x, y);
          return el?.classList?.contains('desktop-win-resize-se') || false;
        }, { x: hx, y: hy });
        expect(topElement).toBe(true);

        // Drag handle outwards by 64px width and 64px height (grid aligned)
        await page.mouse.move(hx, hy);
        await page.mouse.down();
        await page.mouse.move(hx + 64, hy + 64, { steps: 5 });
        await page.mouse.up();

        const resizedBox = await chatWin.boundingBox();
        expect(resizedBox).toBeTruthy();
        if (resizedBox) {
          expect(resizedBox.width).toBeGreaterThan(initialBox.width);
          expect(resizedBox.height).toBeGreaterThan(initialBox.height);
        }
      }
    }
  });

  test('TC-6: Settings Studio theme customizer applies presets and slider palettes [CARD-208]', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // Open Settings Studio from dock
    await page.locator('#dock-settings').click();
    await expect(page.locator('#desktopWin-settings')).toBeVisible();
    await expect(page.locator('#settingsThemeCard')).toBeVisible();

    // 1. Verify preset buttons exist
    const presetsList = page.locator('#themePresetsList');
    await expect(presetsList.locator('[data-theme-preset="autoreiv-indigo"]')).toBeVisible();
    await expect(presetsList.locator('[data-theme-preset="orbital-mono"]')).toBeVisible();
    await expect(presetsList.locator('[data-theme-preset="obsidian-slate"]')).toBeVisible();
    await expect(presetsList.locator('[data-theme-preset="amber-phosphor"]')).toBeVisible();
    await expect(presetsList.locator('[data-theme-preset="emerald-matrix"]')).toBeVisible();

    // 2. Select Orbital Monochrome preset
    await presetsList.locator('[data-theme-preset="orbital-mono"]').click();

    let rootBg = await page.evaluate(() => {
      return document.documentElement.style.getPropertyValue('--theme-bg-base');
    });
    expect(rootBg).toBe('#000000');

    // 3. Select Emerald Matrix preset
    await presetsList.locator('[data-theme-preset="emerald-matrix"]').click();
    let rootBrand = await page.evaluate(() => {
      return document.documentElement.style.getPropertyValue('--theme-brand');
    });
    expect(rootBrand).toBe('#10b981');

    // 4. Adjust Hue slider to 38 (Amber)
    const hueSlider = page.locator('#themeHueSlider');
    await hueSlider.fill('38');
    await hueSlider.dispatchEvent('input');

    const hueValText = await page.locator('#themeHueVal').innerText();
    expect(hueValText).toBe('38°');

    // 5. Save custom theme
    await page.locator('#saveThemeBtn').click();
    await expect(page.locator('#themeSaveStatus')).toBeVisible();

    // 6. Reload and verify persistence from localStorage
    await page.reload({ waitUntil: 'domcontentloaded' });
    const persistedHue = await page.evaluate(() => {
      const raw = localStorage.getItem('autoreiv.theme.v1');
      return raw ? JSON.parse(raw).hue : null;
    });
    expect(persistedHue).toBe(38);

    // 7. Reset to default
    await page.locator('#dock-settings').click();
    await page.locator('#resetThemeBtn').click();
    const resetBrand = await page.evaluate(() => {
      return document.documentElement.style.getPropertyValue('--theme-brand');
    });
    expect(resetBrand).toBe('#6366f1');
  });

  test('TC-7: Deep Desktop & Studio Theme Skinning transforms wallpaper, studio cards, and buttons [CARD-209]', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // Open Settings and select Amber Phosphor
    await page.locator('#dock-settings').click();
    await expect(page.locator('#desktopWin-settings')).toBeVisible();

    const presetsList = page.locator('#themePresetsList');
    await presetsList.locator('[data-theme-preset="amber-phosphor"]').click();

    // Verify root tokens
    const tokens = await page.evaluate(() => {
      const s = document.documentElement.style;
      return {
        brand: s.getPropertyValue('--theme-brand'),
        bgBase: s.getPropertyValue('--theme-bg-base'),
        bgSurface: s.getPropertyValue('--theme-bg-surface'),
      };
    });
    expect(tokens.brand).toBe('#f59e0b');
    expect(tokens.bgBase).toBe('#0a0804');
    expect(tokens.bgSurface).toBe('#18120a');

    // Open Observability and verify card background surface
    await page.locator('#dock-observability').click();
    await expect(page.locator('#desktopWin-observability')).toBeVisible();

    const cardBg = await page.locator('#view-observability .bg-slate-900').first().evaluate((el) => {
      return window.getComputedStyle(el).backgroundColor;
    });
    // #18120a -> rgb(24, 18, 10)
    expect(cardBg).toBe('rgb(24, 18, 10)');

    // Verify primary button background turns to amber (#f59e0b -> rgb(245, 158, 11))
    const updateBtnBg = await page.locator('#checkForUpdatesBtn').evaluate((el) => {
      return window.getComputedStyle(el).backgroundColor;
    });
    expect(updateBtnBg).toBe('rgb(245, 158, 11)');

    // Verify window icon color turns to amber
    const iconColor = await page.locator('#desktopWin-settings .desktop-win-icon').evaluate((el) => {
      return window.getComputedStyle(el).color;
    });
    expect(iconColor).toBe('rgb(245, 158, 11)');

    // Switch to Emerald Matrix and verify button background turns to matrix green (#10b981 -> rgb(16, 185, 129))
    await page.locator('#dock-settings').click();
    const emeraldPreset = presetsList.locator('[data-theme-preset="emerald-matrix"]');
    await emeraldPreset.scrollIntoViewIfNeeded();
    await emeraldPreset.click();

    await page.waitForFunction(() => {
      const btn = document.getElementById('checkForUpdatesBtn');
      if (!btn) return false;
      return window.getComputedStyle(btn).backgroundColor === 'rgb(16, 185, 129)';
    }, { timeout: 3000 });

    const finalBg = await page.locator('#checkForUpdatesBtn').evaluate((el) => {
      return window.getComputedStyle(el).backgroundColor;
    });
    expect(finalBg).toBe('rgb(16, 185, 129)');
  });
});


