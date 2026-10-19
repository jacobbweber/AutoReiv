/**
 * CARD-726 journey:
 * Verifies Settings Studio theme preset switching (amber-phosphor and emerald-matrix) transitions
 * #checkForUpdatesBtn computed background-color cleanly on desktop and mobile viewports.
 */
import { clickExpect, waitFor } from './lib/runner.mjs';
import { openApp } from './lib/app.mjs';

export default {
  id: 'card-726-card-cli-and-theme-transition',
  card: 'CARD-726',
  title: 'Settings Studio theme transitions settle on #checkForUpdatesBtn across presets',
  allow: [],
  async run(j, { page, base }) {
    await j.step('Select Amber Phosphor preset in Settings Studio and verify #checkForUpdatesBtn settles to rgb(196, 163, 90)', async () => {
      await openApp(page, base);
      await clickExpect(
        page.locator('#dock-settings'),
        () => page.locator('#view-settings').isVisible(),
        { label: 'Settings dock', what: 'Settings Studio window', timeoutMs: 10000 }
      );

      const prefsDetails = page.locator('details[data-settings-section="preferences"]');
      if (!(await prefsDetails.evaluate((el) => el.open).catch(() => false))) {
        await prefsDetails.locator('summary').first().click();
      }

      const amberBtn = page.locator('#themePresetsList [data-theme-preset="amber-phosphor"]');
      await amberBtn.waitFor({ state: 'visible', timeout: 10000 });
      await amberBtn.scrollIntoViewIfNeeded();
      await amberBtn.click();

      const settledAmber = await waitFor(
        async () => {
          return page.evaluate(() => {
            const btn = document.getElementById('checkForUpdatesBtn');
            const brand = document.documentElement.style.getPropertyValue('--theme-brand');
            return Boolean(btn && brand === '#c4a35a' && window.getComputedStyle(btn).backgroundColor === 'rgb(196, 163, 90)');
          });
        },
        { timeoutMs: 5000, intervalMs: 100 }
      );
      if (!settledAmber) {
        throw new Error('#checkForUpdatesBtn did not settle to rgb(196, 163, 90) after selecting amber-phosphor');
      }
    }, { timeoutMs: 25000 });

    await j.step('Switch to Emerald Matrix preset, verify #checkForUpdatesBtn settles to rgb(45, 212, 191), and reset theme', async () => {
      const emeraldBtn = page.locator('#themePresetsList [data-theme-preset="emerald-matrix"]');
      await emeraldBtn.scrollIntoViewIfNeeded();
      await emeraldBtn.click();

      const settledEmerald = await waitFor(
        async () => {
          return page.evaluate(() => {
            const btn = document.getElementById('checkForUpdatesBtn');
            const brand = document.documentElement.style.getPropertyValue('--theme-brand');
            return Boolean(btn && brand === '#2dd4bf' && window.getComputedStyle(btn).backgroundColor === 'rgb(45, 212, 191)');
          });
        },
        { timeoutMs: 5000, intervalMs: 100 }
      );
      if (!settledEmerald) {
        throw new Error('#checkForUpdatesBtn did not settle to rgb(45, 212, 191) after selecting emerald-matrix');
      }

      const resetBtn = page.locator('#resetThemeBtn');
      await resetBtn.scrollIntoViewIfNeeded();
      await resetBtn.click();
    }, { timeoutMs: 25000 });
  },
};
