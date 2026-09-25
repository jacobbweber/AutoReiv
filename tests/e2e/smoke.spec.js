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
    await expect(page.locator('#agentSelect')).toBeAttached();
    await expect(page.locator('#activeAgentTitle')).toBeAttached();
    await expect(page.locator('#artifactModal')).toBeAttached();
  });

  test('TC-2: Studio navigation via dock launches critical window components without error [REQ-SMK-002]', async ({
    page,
  }) => {
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
    await expect(page.locator('#forgeSkillsSection')).toBeAttached();
    await expect(page.locator('#studioRunbookBody')).toHaveCount(0);
    await expect(page.locator('#studioRunbookEditor')).toHaveCount(0);
    await expect(page.getByRole('heading', { name: 'Agent Studio' })).toBeAttached();

    // 4. Settings Studio
    await page.locator('#dock-settings').click();
    await expect(page.locator('#desktopWin-settings')).toBeVisible();
    await expect(page.locator('#view-settings')).toBeVisible();
    await expect(page.locator('#provPresetSelect')).toBeAttached();
    await expect(page.locator('#saveProvidersBtn')).toBeAttached();
    await expect(page.locator('#saveMatrixBtn')).toHaveCount(0);
    await expect(page.locator('#matrixGeneral')).toHaveCount(0);
    await expect(page.locator('#settingsOpenToolsStudioBtn')).toBeAttached();
    await expect(page.locator('#settingsMcpAttachStatus')).toBeAttached();
    await expect(page.locator('#mcpServerList')).toBeAttached();
    await expect(page.locator('#addMcpServerBtn')).toHaveCount(0);
    await expect(page.locator('#mcpServerFormContainer')).toHaveCount(0);
    await expect(page.getByText('Hosted MCP Server Active')).toBeAttached();

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
    await expect(page.locator('#chatEngineSelector')).toBeVisible();
    await expect(page.locator('#agentSelect')).toBeAttached();

    const agentSelect = page.locator('#agentSelect');
    await expect(agentSelect.locator('option[value="autoreiv"]')).toHaveCount(1);
    await expect(page.locator('#activeAgentTitle')).toHaveText('AutoReiv');
  });

  test('TC-5: Sessions window cleanup, studio scrolling, and window corner resize [CARD-207]', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // 1. Sessions Drawer: opens in Chat Studio via toggleSidebarBtn, sessionList attached
    await page.locator('#dock-chat').click();
    await page.waitForTimeout(200);
    await expect(page.locator('#desktopWin-chat')).toBeVisible();
    await expect(page.locator('#sessionList')).toBeAttached();

    const winBox = await page.locator('#desktopWin-chat').boundingBox();
    expect(winBox).toBeTruthy();

    // Drag Chat window by titlebar and verify it moves
    const titleHandle = page.locator('#desktopWin-chat .desktop-win-titlebar');
    const titleBox = await titleHandle.boundingBox();
    expect(titleBox).toBeTruthy();
    if (titleBox && winBox) {
      await page.mouse.move(titleBox.x + titleBox.width / 2, titleBox.y + titleBox.height / 2);
      await page.mouse.down();
      await page.mouse.move(titleBox.x + titleBox.width / 2 + 80, titleBox.y + titleBox.height / 2 + 60, { steps: 5 });
      await page.mouse.up();
      await page.waitForTimeout(200);

      const movedWinBox = await page.locator('#desktopWin-chat').boundingBox();
      expect(movedWinBox).toBeTruthy();
      if (movedWinBox) {
        expect(movedWinBox.x).toBeGreaterThan(winBox.x + 40);
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
    const routinesOverflow = await page
      .locator('#view-routines')
      .evaluate((el) => window.getComputedStyle(el).overflowY);
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
        const topElement = await page.evaluate(
          ({ x, y }) => {
            const el = document.elementFromPoint(x, y);
            return el?.classList?.contains('desktop-win-resize-se') || false;
          },
          { x: hx, y: hy }
        );
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

    // Expand Preferences accordion section [CARD-313]
    await page.locator('[data-settings-section="preferences"] summary').click();
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
    expect(rootBg).toBe('#09090b');

    // 3. Select Emerald Matrix preset
    await presetsList.locator('[data-theme-preset="emerald-matrix"]').click();
    let rootBrand = await page.evaluate(() => {
      return document.documentElement.style.getPropertyValue('--theme-brand');
    });
    expect(rootBrand).toBe('#2dd4bf');

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
      const raw = localStorage.getItem('autoreiv.theme.v2');
      return raw ? JSON.parse(raw).hue : null;
    });
    expect(persistedHue).toBe(38);

    // 7. Reset to default (Settings is auto-restored after reload under CARD-279)
    if (!(await page.locator('#desktopWin-settings').isVisible())) {
      await page.locator('#dock-settings').click();
    }
    await page.locator('[data-settings-section="preferences"] summary').click();
    await page.locator('#resetThemeBtn').click();
    const resetBrand = await page.evaluate(() => {
      return document.documentElement.style.getPropertyValue('--theme-brand');
    });
    expect(resetBrand).toBe('#6366f1');
  });

  test('TC-7: Deep Desktop & Studio Theme Skinning transforms wallpaper, studio cards, and buttons [CARD-209]', async ({
    page,
  }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // Open Settings and select Amber Phosphor (Warm Sand)
    await page.locator('#dock-settings').click();
    await expect(page.locator('#desktopWin-settings')).toBeVisible();

    // Expand Preferences accordion section [CARD-313]
    await page.locator('[data-settings-section="preferences"] summary').click();

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
    expect(tokens.brand).toBe('#c4a35a');
    expect(tokens.bgBase).toBe('#0c0b09');
    expect(tokens.bgSurface).toBe('#161410');

    // Open Observability and verify card is visible
    await page.locator('#dock-observability').click();
    await expect(page.locator('#desktopWin-observability')).toBeVisible();

    const card = page.locator('#view-observability [data-obs-section="metrics"]').first();
    await expect(card).toBeVisible();

    // Verify primary button background turns to brand (#c4a35a -> rgb(196, 163, 90))
    const updateBtnBg = await page.locator('#checkForUpdatesBtn').evaluate((el) => {
      return window.getComputedStyle(el).backgroundColor;
    });
    expect(updateBtnBg).toBe('rgb(196, 163, 90)');

    // Verify window icon retains neutral slate chrome
    const iconColor = await page.locator('#desktopWin-settings .desktop-win-icon').evaluate((el) => {
      return window.getComputedStyle(el).color;
    });
    expect(iconColor).toBe('rgb(148, 163, 184)');

    // Switch to Emerald Matrix (Teal) and verify button background turns to teal (#2dd4bf -> rgb(45, 212, 191))
    await page.locator('#dock-settings').click();
    const emeraldPreset = presetsList.locator('[data-theme-preset="emerald-matrix"]');
    await emeraldPreset.scrollIntoViewIfNeeded();
    await emeraldPreset.click();

    await page.waitForFunction(
      () => {
        const btn = document.getElementById('checkForUpdatesBtn');
        if (!btn) return false;
        return window.getComputedStyle(btn).backgroundColor === 'rgb(45, 212, 191)';
      },
      { timeout: 3000 }
    );

    const finalBg = await page.locator('#checkForUpdatesBtn').evaluate((el) => {
      return window.getComputedStyle(el).backgroundColor;
    });
    expect(finalBg).toBe('rgb(45, 212, 191)');
  });

  test('TC-8: Chat composer grows on focus and the message list stays visible and scrollable [CARD-465]', async ({
    page,
  }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await page.locator('#dock-chat').click();
    await expect(page.locator('#view-chat')).toBeVisible();
    const input = page.locator('#promptInput');
    const list = page.locator('#messagesContainer');
    await expect(input).toBeVisible();

    const idle = await input.evaluate((el) => el.getBoundingClientRect().height);
    const listIdle = await list.evaluate((el) => el.clientHeight);
    // Chat auto-focuses the box on open; it stays one line until clicked [CARD-465].
    expect(idle).toBeLessThan(40);
    await input.click();
    await expect.poll(() => input.evaluate((el) => el.getBoundingClientRect().height)).toBeGreaterThan(idle * 2);
    const focused = await input.evaluate((el) => el.getBoundingClientRect().height);

    // Pushes up, never covers: list shrank, still visible, still scrollable, and ends above the composer.
    const listFocused = await list.evaluate((el) => el.clientHeight);
    expect(listFocused).toBeLessThan(listIdle);
    expect(listFocused).toBeGreaterThan(0);
    await expect(list).toBeVisible();
    expect(await list.evaluate((el) => getComputedStyle(el).overflowY)).toBe('auto');
    const listBottom = await list.evaluate((el) => el.getBoundingClientRect().bottom);
    const inputTop = await input.evaluate((el) => el.getBoundingClientRect().top);
    expect(listBottom).toBeLessThanOrEqual(inputTop + 1);

    // Cap: never more than 40% of the chat column.
    const column = await page.locator('#chatMessagesViewport').evaluate((el) => el.parentElement.clientHeight);
    expect(focused).toBeLessThanOrEqual(Math.ceil(column * 0.4) + 1);

    // Blur while empty -> back to one line.
    await page.locator('#messagesContainer').click({ position: { x: 10, y: 10 } });
    await expect.poll(() => input.evaluate((el) => el.getBoundingClientRect().height)).toBeLessThan(idle + 2);
  });

  // CARD-469: composer wiring restored after the CARD-397 split. All network calls that would
  // reach an LLM or write uploads are intercepted.
  async function openChatWithInterceptedStream(page) {
    const streamPosts = [];
    await page.route('**/api/chat/stream', async (route) => {
      streamPosts.push(route.request().postDataJSON());
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'data: {"type":"token","text":"ok"}\n\ndata: [DONE]\n\n',
      });
    });
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await page.locator('#dock-chat').click();
    await expect(page.locator('#view-chat')).toBeVisible();
    await expect(page.locator('#promptInput')).toBeVisible();
    return streamPosts;
  }

  test('TC-9: Enter sends once, Shift+Enter adds a newline [CARD-469]', async ({ page }) => {
    const streamPosts = await openChatWithInterceptedStream(page);
    const input = page.locator('#promptInput');
    await input.click();
    await input.type('line one');
    await input.press('Shift+Enter');
    await input.type('line two');
    await expect(input).toHaveValue('line one\nline two');
    expect(streamPosts.length).toBe(0);
    await input.press('Enter');
    await expect.poll(() => streamPosts.length).toBe(1);
    expect(streamPosts[0].content).toBe('line one\nline two');
    await expect(input).toHaveValue('');
  });

  test('TC-10: Enter also sends on a phone-sized touch viewport (D1) [CARD-469]', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    const streamPosts = await openChatWithInterceptedStream(page);
    const input = page.locator('#promptInput');
    await input.click();
    await input.type('from the phone');
    await input.press('Enter');
    await expect.poll(() => streamPosts.length).toBe(1);
    expect(streamPosts[0].content).toBe('from the phone');
  });

  test('TC-11: Quick Prompts picker opens and a pick fills the composer [CARD-469]', async ({ page }) => {
    await page.route('**/api/prompts', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: 'smoke-1', title: 'Smoke Prompt', category: 'test', description: 'd', template_text: 'Hello from a quick prompt' },
        ]),
      })
    );
    await openChatWithInterceptedStream(page);
    await page.locator('#chatOptionsToggleBtn').click();
    await expect(page.locator('#chatOptionsDrawer')).toBeVisible();
    await page.locator('#chatPromptsBtn').click();
    await expect(page.locator('#chatPromptsQuickPicker')).toBeVisible();
    await page.locator('#chatPromptsQuickList [data-quick-idx="0"]').click();
    await expect(page.locator('#promptInput')).toHaveValue('Hello from a quick prompt');
    await expect(page.locator('#chatPromptsQuickPicker')).toBeHidden();
  });

  test('TC-12: Paperclip attach stages a chip [CARD-469]', async ({ page }) => {
    await page.route('**/api/chat/upload', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: 'up-1', filename: 'smoke.txt', size_bytes: 5, content_type: 'text/plain', url: '/x', path: '/x' }),
      })
    );
    await openChatWithInterceptedStream(page);
    await page.locator('#chatOptionsToggleBtn').click();
    const [chooser] = await Promise.all([
      page.waitForEvent('filechooser'),
      page.locator('#chatAttachBtn').click(),
    ]);
    await chooser.setFiles({ name: 'smoke.txt', mimeType: 'text/plain', buffer: Buffer.from('hello') });
    await expect(page.locator('#chatAttachmentsPreviewList')).toBeVisible();
    await expect(page.locator('#chatAttachmentsPreviewList')).toContainText('smoke.txt');
  });

  test('TC-13: A failed reply (backend error event) shows an error, not silence [CARD-469]', async ({ page }) => {
    await page.route('**/api/chat/upload', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: 'up-2', filename: 'pic.png', size_bytes: 70, content_type: 'image/png', url: '/x', path: '/x' }),
      })
    );
    await page.route('**/api/chat/stream', (route) =>
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'event: error\ndata: {"error": "[vllm] Provider HTTP error 400: text-only-model is not a multimodal model"}\n\n',
      })
    );
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await page.locator('#dock-chat').click();
    await expect(page.locator('#promptInput')).toBeVisible();
    await page.locator('#chatOptionsToggleBtn').click();
    const [chooser] = await Promise.all([page.waitForEvent('filechooser'), page.locator('#chatAttachBtn').click()]);
    await chooser.setFiles({ name: 'pic.png', mimeType: 'image/png', buffer: Buffer.from('png') });
    await expect(page.locator('#chatAttachmentsPreviewList')).toContainText('pic.png');
    const input = page.locator('#promptInput');
    await input.click();
    await input.type('What is this?');
    await input.press('Enter');
    const alert = page.locator('#messagesContainer .chat-stream-error');
    await expect(alert).toBeVisible();
    await expect(alert).toContainText('not a multimodal model');
  });

  // CARD-470: Auto-run was inverted after the CARD-397 split. Unchecked must send "ask".
  // /api/chat/stream is intercepted, so no tool can run.
  async function sendAndCapture(page, streamPosts, text) {
    const n = streamPosts.length;
    const input = page.locator('#promptInput');
    await input.click();
    await input.type(text);
    await input.press('Enter');
    await expect.poll(() => streamPosts.length).toBe(n + 1);
    return streamPosts[n];
  }

  test('TC-14: Auto-run off by default sends approval_mode "ask" [CARD-470]', async ({ page }) => {
    const streamPosts = await openChatWithInterceptedStream(page);
    await page.locator('#chatOptionsToggleBtn').click();
    await expect(page.locator('#approvalToggle')).not.toBeChecked();
    await expect(page.locator('#approvalBadge')).toBeHidden();
    const body = await sendAndCapture(page, streamPosts, 'default mode');
    expect(body.approval_mode).toBe('ask');
  });

  test('TC-15: Checking Auto-run sends "run" and shows the amber chip [CARD-470]', async ({ page }) => {
    const streamPosts = await openChatWithInterceptedStream(page);
    await page.locator('#chatOptionsToggleBtn').click();
    await page.locator('#approvalToggle').check();
    await expect(page.locator('#approvalBadge')).toBeVisible();
    await expect(page.locator('#approvalBadge')).toHaveText('Auto-run ON');
    const body = await sendAndCapture(page, streamPosts, 'auto mode');
    expect(body.approval_mode).toBe('run');
  });

  test('TC-16: The Auto-run choice survives a reload [CARD-470]', async ({ page }) => {
    await openChatWithInterceptedStream(page);
    await page.locator('#chatOptionsToggleBtn').click();
    await page.locator('#approvalToggle').check();
    await expect.poll(() => page.evaluate(() => localStorage.getItem('autoreiv_approval_autorun'))).toBe('run');
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('load');
    if (!(await page.locator('#view-chat').isVisible())) await page.locator('#dock-chat').click();
    await expect(page.locator('#approvalToggle')).toBeChecked();
    await expect(page.locator('#approvalBadge')).toBeVisible();
  });

  test('TC-17: A saved "run" from before the fix is reset to "ask" once [CARD-470]', async ({ page }) => {
    // Seed a pre-fix saved 'run' (no reset marker) on the first real page load only.
    await page.addInitScript(() => {
      try {
        if (location.protocol.startsWith('http') && !sessionStorage.getItem('card470_seeded')) {
          localStorage.setItem('autoreiv_approval_autorun', 'run');
          sessionStorage.setItem('card470_seeded', '1');
        }
      } catch { /* about:blank has no storage */ }
    });
    const streamPosts = await openChatWithInterceptedStream(page);
    await page.locator('#chatOptionsToggleBtn').click();
    await expect(page.locator('#approvalToggle')).not.toBeChecked();
    const body = await sendAndCapture(page, streamPosts, 'after reset');
    expect(body.approval_mode).toBe('ask');
    expect(await page.evaluate(() => localStorage.getItem('autoreiv_approval_autorun'))).toBe('ask');
  });

  test('TC-18: A parked tool shows an Approve/Reject card; Reject posts the decision [CARD-470]', async ({ page }) => {
    const row = { id: 'appr_smoke', session_id: null, agent_id: 'autoreiv', routine_id: null, tool_name: 'wiki_note_create', arguments: { title: 'test470' }, status: 'pending' };
    let decided = null;
    await page.route('**/api/chat/stream', (route) => {
      row.session_id = route.request().postDataJSON().session_id;
      return route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'event: approval_required\ndata: ' + JSON.stringify({ type: 'approval_required', approval_id: 'appr_smoke', tool_name: 'wiki_note_create', arguments: { title: 'test470' }, message: 'Parked for operator approval (appr_smoke). The tool was not executed.' }) + '\n\nevent: turn_done\ndata: {"content": ""}\n\n',
      });
    });
    await page.route('**/api/approvals/pending**', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(decided || !row.session_id ? [] : [row]) }));
    await page.route('**/api/approvals/appr_smoke/decision', (route) => {
      decided = route.request().postDataJSON();
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'REJECTED', resumed: true }) });
    });
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await page.locator('#dock-chat').click();
    await expect(page.locator('#promptInput')).toBeVisible();
    const created = page.waitForResponse((r) => r.url().endsWith('/api/sessions') && r.request().method() === 'POST');
    await page.locator('#newChatBtn').dispatchEvent('click');
    await created;
    const input = page.locator('#promptInput');
    await input.click();
    await input.type('Create a wiki note titled test470');
    await input.press('Enter');
    const card = page.locator('#pendingHitlHost [data-approval-id="appr_smoke"]');
    await expect(card).toBeVisible();
    await expect(card).toContainText('wiki_note_create');
    await expect(card).toContainText('test470');
    await card.locator('[data-hitl-decision="REJECTED"]').click();
    await expect.poll(() => decided && decided.decision).toBe('REJECTED');
  });

  test('TC-19: An image on a text-only model shows the attachment notice under the reply [CARD-475]', async ({ page }) => {
    const notice = "This model can't view images, so it only saw the file name `pic.png`. "
      + 'Switch to a vision model (e.g. gemma-4-26b-a4b) to include pictures.';
    await page.route('**/api/chat/upload', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: 'up-3', filename: 'pic.png', size_bytes: 70, content_type: 'image/png', url: '/x', path: '/x' }),
      })
    );
    await page.route('**/api/chat/stream', (route) =>
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body:
          `event: attachment_notice\ndata: ${JSON.stringify({ type: 'attachment_notice', message: notice, files: ['pic.png'] })}\n\n`
          + 'event: token\ndata: {"text": "I cannot see the picture."}\n\n'
          + 'event: turn_done\ndata: {"content": "I cannot see the picture."}\n\n',
      })
    );
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await page.locator('#dock-chat').click();
    await expect(page.locator('#promptInput')).toBeVisible();
    await page.locator('#chatOptionsToggleBtn').click();
    const [chooser] = await Promise.all([page.waitForEvent('filechooser'), page.locator('#chatAttachBtn').click()]);
    await chooser.setFiles({ name: 'pic.png', mimeType: 'image/png', buffer: Buffer.from('png') });
    await expect(page.locator('#chatAttachmentsPreviewList')).toContainText('pic.png');
    const input = page.locator('#promptInput');
    await input.click();
    await input.type('What is this?');
    await input.press('Enter');
    const shown = page.locator('#messagesContainer .chat-attachment-notice');
    await expect(shown).toBeVisible();
    await expect(shown).toHaveText(notice);
    await expect(page.locator('#messagesContainer .chat-stream-error')).toHaveCount(0);
  });

  // CARD-476: a chat always has a session; the last one on this device is restored.
  for (const vp of [{ name: 'desktop', width: 1280, height: 800 }, { name: 'phone', width: 390, height: 844 }]) {
    async function openChat476(page, { agentId = null, storedSessionId = null } = {}) {
      const posts = [];
      await page.route('**/api/chat/stream', async (route) => {
        posts.push(route.request().postDataJSON());
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'text/event-stream' },
          body: 'event: token\ndata: {"text": "ok"}\n\nevent: turn_done\ndata: {"content": "ok"}\n\n',
        });
      });
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.addInitScript(({ a, s }) => {
        try {
          if (a) localStorage.setItem('autoreiv_active_agent_id', a);
          if (s) localStorage.setItem('autoreiv_active_session_id', s);
        } catch { /* ignore */ }
      }, { a: agentId, s: storedSessionId });
      // Wait for a chat to be opened (its messages load) so restore, not the load race, is tested.
      const opened = page.waitForResponse((r) => /\/api\/sessions\/[^/]+\/messages/.test(r.url()));
      await page.goto('/', { waitUntil: 'domcontentloaded' });
      await page.locator('#dock-chat').click();
      await expect(page.locator('#promptInput')).toBeVisible();
      if (storedSessionId) await opened;
      return posts;
    }

    async function seedSessions476(request, agentId) {
      const older = await (await request.post('/api/sessions', { data: { agent_id: agentId, title: 'older 476' } })).json();
      await new Promise((r) => setTimeout(r, 1100));
      const newer = await (await request.post('/api/sessions', { data: { agent_id: agentId, title: 'newer 476' } })).json();
      return { older, newer };
    }

    async function send476(page, text = 'hi') {
      const input = page.locator('#promptInput');
      await input.click();
      await input.type(text);
      await input.press('Enter');
    }

    test(`TC-20 (${vp.name}): an agent with no chats gets one, and the first message sends [CARD-476]`, async ({ page, request }) => {
      const agentId = `smoke-476-${vp.name}-${Date.now()}`;
      const made = await request.post('/api/agents', { data: { id: agentId, name: `Smoke 476 ${vp.name}`, system_prompt: 'Smoke test agent.' } });
      expect(made.ok()).toBeTruthy();
      const posts = await openChat476(page, { agentId });
      await expect.poll(async () => (await (await request.get(`/api/sessions?agent_id=${agentId}`)).json()).length).toBe(1);
      const [sess] = await (await request.get(`/api/sessions?agent_id=${agentId}`)).json();
      await send476(page);
      await expect.poll(() => posts.length).toBe(1);
      expect(posts[0].session_id).toBe(sess.id);
      await expect(page.getByText('HTTP 422')).toHaveCount(0);
    });

    test(`TC-21 (${vp.name}): reload reopens this device's last chat, not the newest [CARD-476]`, async ({ page, request }) => {
      const { older } = await seedSessions476(request, 'autoreiv');
      const posts = await openChat476(page, { agentId: 'autoreiv', storedSessionId: older.id });
      await send476(page);
      await expect.poll(() => posts.length).toBe(1);
      expect(posts[0].session_id).toBe(older.id);
      expect(await page.evaluate(() => localStorage.getItem('autoreiv_active_session_id'))).toBe(older.id);
    });

    test(`TC-22 (${vp.name}): a send right after load never posts a null session [CARD-476]`, async ({ page, request }) => {
      await seedSessions476(request, 'autoreiv');
      const posts = [];
      await page.route('**/api/chat/stream', async (route) => {
        posts.push(route.request().postDataJSON());
        await route.fulfill({ status: 200, headers: { 'Content-Type': 'text/event-stream' }, body: 'event: turn_done\ndata: {"content": "ok"}\n\n' });
      });
      // Hold the session list so the send is sure to race the load.
      await page.route('**/api/sessions?agent_id=*', async (route) => {
        await new Promise((r) => setTimeout(r, 1500));
        await route.continue();
      });
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto('/', { waitUntil: 'domcontentloaded' });
      await page.locator('#dock-chat').click();
      await expect(page.locator('#promptInput')).toBeVisible();
      await send476(page, 'fast');
      await expect.poll(() => posts.length, { timeout: 10000 }).toBe(1);
      expect(typeof posts[0].session_id).toBe('string');
      expect(posts[0].session_id.length).toBeGreaterThan(0);
    });

    test(`TC-23 (${vp.name}): a stored chat that no longer exists falls back to the newest [CARD-476]`, async ({ page, request }) => {
      const { newer } = await seedSessions476(request, 'autoreiv');
      const posts = await openChat476(page, { agentId: 'autoreiv', storedSessionId: 'gone-476-session' });
      await send476(page);
      await expect.poll(() => posts.length).toBe(1);
      expect(posts[0].session_id).toBe(newer.id);
    });
  }
});
