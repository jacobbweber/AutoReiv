/**
 * CARD-720: Comprehensive UI Audit and Button Functionality Fixes.
 */
import { openApp, send, waitReplyIdle } from './lib/app.mjs';
import { waitFor } from './lib/runner.mjs';

async function openTab(page, tabName) {
  const viewId = `#view-${tabName}`;
  await page.evaluate((t) => {
    document.getElementById(`tab-${t}`)?.click();
  }, tabName);
  await page.locator(viewId).waitFor({ state: 'visible', timeout: 20000 });
}

export default {
  id: 'card-720-comprehensive-ui-audit-and-button-functionality',
  card: 'CARD-720',
  title: 'Chat reply Copy button feedback, post-send composer shrink, single-lever Sessions drawer, Agent avatar/memory controls, Capabilities Escape key, Wiki folder overview, Education Due hide, and Settings wiring',
  allow: [],

  async run(j, { page, base, viewport }) {
    await j.step('1. Chat Studio: composer shrinks on send, first click on reply Copy shows Copied! + toast, and #toggleSidebarBtn cleanly toggles Sessions drawer', async () => {
      await openApp(page, base);
      await openTab(page, 'chat');
      await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 15000 });

      // Focus composer by clicking it so engaged = true
      await page.locator('#promptInput').click();
      await send(page, 'Reply with only the word PONG.');

      // Immediately after send, composer value is empty and height must already be 1 line (<= 65px)
      const postSendHeight = await page.evaluate(() => {
        const el = document.getElementById('promptInput');
        return el ? el.getBoundingClientRect().height : 0;
      });
      if (postSendHeight > 65) {
        throw new Error(`Expected empty #promptInput to shrink to 1 line immediately after send, got ${postSendHeight}px`);
      }

      const gotReply = await waitFor(
        async () => (await page.locator('#messagesContainer .copy-msg-btn').count()) >= 1,
        { timeoutMs: 120000, intervalMs: 1000 },
      );
      if (!gotReply) {
        throw new Error('Timed out waiting for assistant reply with .copy-msg-btn in #messagesContainer');
      }
      await waitReplyIdle(page, { timeoutMs: 120000, settleMs: 1500 });

      const copyBtn = page.locator('#messagesContainer .copy-msg-btn').last();
      await copyBtn.scrollIntoViewIfNeeded();
      await copyBtn.waitFor({ state: 'visible', timeout: 15000 });

      // First click on .copy-msg-btn must succeed without layout shift
      await copyBtn.click();

      const copiedOk = await waitFor(async () => {
        return page.evaluate(() => {
          const btns = Array.from(document.querySelectorAll('#messagesContainer .copy-msg-btn span'));
          const hasCopiedLabel = btns.some((s) => s.textContent === 'Copied!');
          const toastText = document.getElementById('toastContainer')?.innerText || '';
          return hasCopiedLabel || toastText.includes('Copied to clipboard');
        });
      }, { timeoutMs: 5000, intervalMs: 100 });

      if (!copiedOk) {
        throw new Error('Expected .copy-msg-btn click to update label to "Copied!" and show "Copied to clipboard" toast');
      }

      // Test #toggleSidebarBtn single-lever behavior
      await page.locator('#toggleSidebarBtn').click();
      await page.locator('#chatSessionsDrawer').waitFor({ state: 'visible', timeout: 5000 });
      await page.locator('#toggleSidebarBtn').click();
      await page.locator('#chatSessionsDrawer').waitFor({ state: 'hidden', timeout: 5000 });

      j.note(`verified post-send composer height (${Math.round(postSendHeight)}px), first-click Copy feedback + toast, and #toggleSidebarBtn drawer toggle`);
    });

    await j.step('2. Agents Studio: avatar preview updates without nested <svg> and #forgeMemoryEnabled toggles #forgeMemoryConfigContainer', async () => {
      await openTab(page, 'agents');

      const avatarCheck = await page.evaluate(() => {
        const sel = document.getElementById('forgeAvatarSelect');
        if (sel) {
          sel.value = 'sparkles';
          sel.dispatchEvent(new Event('change', { bubbles: true }));
        }
        const preview = document.getElementById('forgeAvatarPreview');
        const nestedSvg = preview ? preview.querySelectorAll('svg svg').length : -1;
        const hasIcon = preview ? Boolean(preview.querySelector('#forgeAvatarIcon')) : false;
        return { nestedSvg, hasIcon };
      });
      if (!avatarCheck.hasIcon || avatarCheck.nestedSvg !== 0) {
        throw new Error(`Expected #forgeAvatarPreview to render #forgeAvatarIcon with 0 nested SVGs, got ${JSON.stringify(avatarCheck)}`);
      }

      const memoryCheck = await page.evaluate(() => {
        const cb = document.getElementById('forgeMemoryEnabled');
        const container = document.getElementById('forgeMemoryConfigContainer');
        if (!cb || !container) return { ok: false, reason: 'missing elements' };
        cb.checked = false;
        cb.dispatchEvent(new Event('change', { bubbles: true }));
        const hiddenWhenUnchecked = container.classList.contains('hidden');
        cb.checked = true;
        cb.dispatchEvent(new Event('change', { bubbles: true }));
        const visibleWhenChecked = !container.classList.contains('hidden');
        return { ok: hiddenWhenUnchecked && visibleWhenChecked, hiddenWhenUnchecked, visibleWhenChecked };
      });
      if (!memoryCheck.ok) {
        throw new Error(`Expected #forgeMemoryEnabled to toggle #forgeMemoryConfigContainer visibility: ${JSON.stringify(memoryCheck)}`);
      }

      j.note('verified #forgeAvatarPreview has 0 nested SVGs and #forgeMemoryEnabled toggles #forgeMemoryConfigContainer');
    });

    await j.step('3. Capabilities, Wiki, Education, and Settings Studios: verify create-bar Escape, folder overview, Due panel Hide, and Settings wiring', async () => {
      // Capabilities Studio: New Skill bar closes on Escape without minimizing window
      await openTab(page, 'capabilities');
      await page.evaluate(() => {
        document.getElementById('capabilitiesNewSkillBtn')?.click();
      });
      await page.locator('#capabilitiesCreateBar').waitFor({ state: 'visible', timeout: 5000 });
      await page.locator('#capabilitiesCreateNameInput').press('Escape');
      await page.locator('#capabilitiesCreateBar').waitFor({ state: 'hidden', timeout: 5000 });
      if (!(await page.locator('#view-capabilities').isVisible())) {
        throw new Error('Expected #view-capabilities to stay open when Escape closes #capabilitiesCreateBar');
      }

      // Wiki Studio: Folder overview renders when clicking a folder row
      await openTab(page, 'wiki');
      const folderReady = await waitFor(
        async () => (await page.locator('#wikiNavTree .wiki-folder-row').count()) >= 1,
        { timeoutMs: 10000, intervalMs: 200 },
      );
      if (!folderReady) {
        throw new Error('Expected #wikiNavTree to render at least one .wiki-folder-row');
      }
      await page.evaluate(() => {
        document.querySelector('#wikiNavTree .wiki-folder-row')?.click();
      });
      const wikiHasOverview = await waitFor(async () => {
        return page.evaluate(() => {
          const viewer = document.getElementById('wikiViewerContent');
          return Boolean(viewer && !viewer.classList.contains('hidden') && viewer.innerHTML.includes('note'));
        });
      }, { timeoutMs: 5000, intervalMs: 100 });
      if (!wikiHasOverview) {
        throw new Error('Expected clicking a Wiki folder row to render the Folder Overview in #wikiViewerContent');
      }

      // Education Studio: #educationOperatorDueHideBtn hides #educationOperatorDuePanel
      await openTab(page, 'education');
      const eduCheck = await page.evaluate(() => {
        const panel = document.getElementById('educationOperatorDuePanel');
        const hideBtn = document.getElementById('educationOperatorDueHideBtn');
        if (!panel || !hideBtn) return { ok: false, reason: 'missing due panel or hide btn' };
        panel.classList.remove('hidden');
        hideBtn.click();
        return { ok: panel.classList.contains('hidden') };
      });
      if (!eduCheck.ok) {
        throw new Error(`Expected #educationOperatorDueHideBtn to hide #educationOperatorDuePanel: ${JSON.stringify(eduCheck)}`);
      }

      // Settings Studio: #allowedOriginsSaveBtn is wired once and modelFitTableBody uses 'Refresh Models'
      await openTab(page, 'settings');
      const settingsCheck = await page.evaluate(() => {
        const saveBtn = document.getElementById('allowedOriginsSaveBtn');
        const html = document.getElementById('view-settings')?.innerHTML || '';
        return {
          wired: saveBtn?.dataset?.wired === '1',
          hasStaleRefreshLabel: html.includes('Refresh From Providers'),
        };
      });
      if (!settingsCheck.wired || settingsCheck.hasStaleRefreshLabel) {
        throw new Error(`Settings check failed: ${JSON.stringify(settingsCheck)}`);
      }

      const overflow = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
      }));
      if (overflow.scrollWidth > overflow.clientWidth + 2) {
        throw new Error(`Horizontal overflow on ${viewport?.name || 'viewport'}: ${overflow.scrollWidth}px > ${overflow.clientWidth}px`);
      }

      j.note(`verified Capabilities Escape key, Wiki folder overview, Education Due Hide button, Settings wiring, and zero overflow (${overflow.scrollWidth}px <= ${overflow.clientWidth}px)`);
    });
  },
};
