/**
 * CARD-638: Lumina Studio is gone. The dock and header tabs have no Lumina launcher, the page has no
 * Lumina view, a saved desktop layout that still names the Lumina window loads without a console
 * error, /api/lumina/* answers 404, and the Education Studio still opens. No model is called.
 */
import path from 'path';
import { openApp } from './lib/app.mjs';

const PREFS_KEY = 'autoreiv.agentDesktop.v1';

async function dockLabels(page) {
  return page.locator('#desktopDockApps .desktop-dock-btn').evaluateAll((els) => els.map((e) => e.getAttribute('aria-label')));
}

export default {
  id: 'card-638-lumina-removed',
  card: 'CARD-638',
  title: 'Lumina Studio removed',
  async run(j, { page, request, base, viewport }) {
    await j.step('The app loads with no Lumina dock launcher, tab or view', async () => {
      await openApp(page, base);
      await page.waitForTimeout(2500);
      const labels = await dockLabels(page);
      j.note(`dock: ${labels.join(', ')}`);
      if (labels.some((l) => /lumina/i.test(l || ''))) throw new Error('Lumina is still on the dock');
      if (!labels.includes('Education')) throw new Error('Education is missing from the dock');
      for (const sel of ['#dock-lumina', '#tab-lumina', '#view-lumina', '#luminaStudio']) {
        const n = await page.locator(sel).count();
        if (n) throw new Error(`${sel} still exists`);
      }
      const box = await page.locator('#desktopDockApps').boundingBox();
      if (box) {
        const pad = 10;
        const vp = page.viewportSize();
        const clip = { x: Math.max(0, box.x - pad), y: Math.max(0, box.y - pad), width: Math.min(vp.width, box.width + 2 * pad), height: box.height + 2 * pad };
        clip.width = Math.min(clip.width, vp.width - clip.x);
        clip.height = Math.min(clip.height, vp.height - clip.y);
        const file = path.join(j.outDir, `card-638-lumina-removed-${viewport.name}-dock.png`);
        await page.screenshot({ path: file, clip });
        j.note(`dock screenshot: ${file}`);
      }
      await j.screenshot('desktop-without-lumina');
    }, { timeoutMs: 60000 });

    await j.step('A saved layout that still names the Lumina window reloads without errors', async () => {
      await page.evaluate((key) => {
        let prefs;
        try { prefs = JSON.parse(localStorage.getItem(key) || '{}') || {}; } catch { prefs = {}; }
        prefs.windows = { ...(prefs.windows || {}), lumina: { x: 40, y: 40, w: 840, h: 620 } };
        prefs.openWindows = Array.from(new Set([...(prefs.openWindows || []), 'lumina', 'education']));
        prefs.autoRestore = true;
        localStorage.setItem(key, JSON.stringify(prefs));
        localStorage.setItem('autoreiv_active_tab', 'lumina');
      }, PREFS_KEY);
      await page.reload({ waitUntil: 'domcontentloaded' });
      await page.locator('#dock-chat').waitFor({ state: 'visible', timeout: 20000 });
      await page.waitForTimeout(3000);
      const wins = await page.locator('#desktopWin-lumina').count();
      j.note(`after reload: lumina windows ${wins}; dock ${(await dockLabels(page)).length} launchers`);
      if (wins) throw new Error('a Lumina window was restored');
      if (await page.locator('#view-lumina').count()) throw new Error('#view-lumina came back');
    }, { timeoutMs: 60000 });

    await j.step('The Lumina API routes are gone', async () => {
      const codes = [];
      for (const [method, url, data] of [
        ['get', '/api/lumina/starters'],
        ['get', '/api/lumina/lesson/photosynthesis'],
        ['post', '/api/lumina/compose', { topic: 'Black holes' }],
        ['post', '/api/lumina/send-to-course', { topic: 'Photosynthesis' }],
      ]) {
        const res = method === 'get' ? await request.get(`${base}${url}`) : await request.post(`${base}${url}`, { data });
        codes.push(`${method.toUpperCase()} ${url} -> ${res.status()}`);
        if (![404, 405].includes(res.status())) throw new Error(`${url} answered ${res.status()}`);
      }
      j.note(codes.join('; '));
    }, { timeoutMs: 30000 });

    await j.step('The Education Studio still opens from the dock', async () => {
      if (!(await page.locator('#view-education').isVisible())) await page.locator('#dock-education').click();
      await page.locator('#view-education').waitFor({ state: 'visible', timeout: 20000 });
      await page.locator('#educationTopicInput').waitFor({ state: 'visible', timeout: 10000 });
      await j.screenshot('education-opens');
    }, { timeoutMs: 60000 });
  },
};
