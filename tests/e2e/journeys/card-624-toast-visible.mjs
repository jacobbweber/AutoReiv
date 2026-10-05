/**
 * CARD-624: toasts render above the desktop dock (visible and hit-testable).
 */
import { waitFor } from './lib/runner.mjs';
import { openApp } from './lib/app.mjs';

async function showProbeToast(page) {
  // Prefer the real Chat header path (stable under full smoke); fall back to showToast.
  if (!(await page.locator('#promptInput').isVisible().catch(() => false))) {
    await page.locator('#dock-chat').click();
  }
  await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 15000 });
  await page.locator('#exportThreadWikiBtn').click();
  const shown = await waitFor(async () => (await page.locator('#toastContainer > div').count()) > 0, { timeoutMs: 5000 });
  if (!shown) {
    await page.evaluate(() => {
      // Synchronous path: create via already-parsed module graph if present on window.
      const ev = new CustomEvent('autoreiv:show-toast', { detail: { message: 'CARD-624 toast probe', type: 'success' } });
      document.dispatchEvent(ev);
    });
  }
  await waitFor(async () => (await page.locator('#toastContainer > div').count()) > 0, { timeoutMs: 10000 });
}

async function hitTestToast(page) {
  return page.evaluate(() => {
    const toast = document.querySelector('#toastContainer > div');
    if (!toast) return { ok: false, reason: 'no toast' };
    const r = toast.getBoundingClientRect();
    const x = r.left + r.width / 2;
    const y = r.top + r.height / 2;
    const el = document.elementFromPoint(x, y);
    if (!el) return { ok: false, reason: 'elementFromPoint null', x, y, top: r.top, bottom: r.bottom };
    const inToast = !!(el.closest && el.closest('#toastContainer > div'));
    const dockHit = !!(el.closest && (el.closest('.desktop-dock') || el.closest('#desktopDock') || el.closest('.desktop-dock-icon') || el.id === 'desktopDockApps'));
    const dock = document.querySelector('#desktopDock, .desktop-dock');
    const dockTop = dock ? dock.getBoundingClientRect().top : null;
    return {
      ok: inToast && !dockHit,
      inToast,
      dockHit,
      id: el.id || null,
      cls: (el.className && String(el.className).slice(0, 80)) || '',
      x, y,
      toastTop: r.top,
      toastBottom: r.bottom,
      dockTop,
      aboveDock: dockTop == null || r.bottom <= dockTop + 1,
    };
  });
}

export default {
  id: 'card-624-toast-visible',
  card: 'CARD-624',
  title: 'Toast centre hit-tests to the toast above the dock',
  allow: [],
  async run(j, { page, base, viewport }) {
    await j.step('Open app and show a success toast', async () => {
      await openApp(page, base);
      await showProbeToast(page);
    });

    await j.step('Toast centre is the toast (not a dock icon) and sits above the dock', async () => {
      const hit = await hitTestToast(page);
      if (!hit.ok) throw new Error('toast still under dock: ' + JSON.stringify(hit));
      if (!hit.aboveDock) throw new Error('toast overlaps dock band: ' + JSON.stringify(hit));
    });
  },
};
