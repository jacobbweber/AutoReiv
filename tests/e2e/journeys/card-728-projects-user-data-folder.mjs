/**
 * CARD-728 / CARD-729 journey: projects live in one user-data folder and the app never pushes a template.
 * 1) Projects Manager shows the fixed projects folder (read-only), no root input, no drift banner or Align button.
 * 2) Creating a project from the UI makes an empty git repository inside that folder on disk.
 * 3) A project with its own CLAUDE.md becomes active; the explorer lists its files and nothing asks to "align" it.
 * 4) Selecting a folder outside the projects folder (the AutoReiv checkout, OS temp) is refused with 400.
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { clickExpect, waitFor } from './lib/runner.mjs';
import { getJson, openApp } from './lib/app.mjs';

const isHidden = (loc) => loc.evaluate((el) => el.classList.contains('hidden')).catch(() => true);

async function openProjectsManager(page) {
  if (!(await page.locator('#view-projects').isVisible().catch(() => false))) {
    await page.locator('#dock-projects').click();
  }
  await page.locator('#view-projects').waitFor({ state: 'visible', timeout: 20000 });
  await page.locator('#projectsModeManagerBtn').click();
  await waitFor(async () => !(await isHidden(page.locator('#projectsManagerView'))), { timeoutMs: 10000 });
}

async function assertNoTemplatePush(page) {
  if (await page.locator('#projectsRootInput').count()) throw new Error('#projectsRootInput still rendered');
  if (await page.locator('#projectsDriftBanner').count()) throw new Error('#projectsDriftBanner still rendered');
  const align = page.locator('#view-projects button', { hasText: /^\s*Align/i });
  if (await align.count()) throw new Error('an Align button is still rendered');
}

export default {
  id: 'card-728-projects-user-data-folder',
  card: 'CARD-728',
  title: 'Projects live in one user-data folder; no template push',
  allow: [],
  async run(j, { page, request, base, viewport }) {
    const slug = `demo-728-${viewport.name}`.replace(/[^a-z0-9-]/gi, '').toLowerCase();
    let projectsRoot = '';
    let projPath = '';
    await request.delete(`${base}/api/projects/${encodeURIComponent(slug)}?confirm=true`).catch(() => {});

    try {
      await j.step('Projects Manager shows the fixed projects folder and no root input or drift banner', async () => {
        const listed = await getJson(request, `${base}/api/projects`);
        projectsRoot = String(listed.projects_root || '');
        if (!projectsRoot) throw new Error('GET /api/projects returned no projects_root');
        if (!fs.existsSync(projectsRoot)) throw new Error(`projects folder ${projectsRoot} does not exist on disk`);
        await openApp(page, base);
        await openProjectsManager(page);
        await waitFor(
          async () => (await page.locator('#projectsFolderPath').innerText().catch(() => '')).trim() === projectsRoot,
          { timeoutMs: 15000, label: '#projectsFolderPath shows projects_root' },
        );
        await assertNoTemplatePush(page);
        j.note(`projects folder ${projectsRoot}`);
      });

      await j.step('Create a project from the UI and see an empty git repository on disk', async () => {
        await page.locator('#projectsSlugInput').fill(slug);
        const row = page.locator(`#projectsList [data-act="set-active"][data-slug="${slug}"]`);
        await clickExpect(page.locator('#projectsCreateBtn'), async () => (await row.count()) > 0, {
          label: 'Create project and see it listed',
          timeoutMs: 20000,
        });
        projPath = path.join(projectsRoot, slug);
        if (!fs.existsSync(path.join(projPath, '.git'))) throw new Error(`${projPath} is not a git repository`);
        const files = fs.readdirSync(projPath).filter((f) => f !== '.git');
        if (files.length) throw new Error(`new project is not empty (template pushed?): ${files.join(', ')}`);
        if (fs.existsSync(path.join(projPath, 'AGENTS.md'))) throw new Error('AGENTS.md template was written');
      });

      await j.step('A project with its own CLAUDE.md becomes active and the explorer lists its files', async () => {
        fs.writeFileSync(path.join(projPath, 'CLAUDE.md'), '# CLAUDE.md\n\nThis repo keeps its own rules.\n');
        await page.locator('#projectsRefreshBtn').click();
        const setActive = page.locator(`#projectsList [data-act="set-active"][data-slug="${slug}"]`);
        await setActive.waitFor({ state: 'visible', timeout: 15000 });
        await clickExpect(
          setActive,
          async () => (await page.locator('#projectsActiveName').innerText().catch(() => '')).includes(slug),
          { label: 'Set as Active', timeoutMs: 15000 },
        );
        const sel = await getJson(request, `${base}/api/projects/selected`);
        const picked = sel.selected || sel;
        if (picked.slug !== slug) throw new Error(`selected slug ${picked.slug}, expected ${slug}`);
        await page.locator('#projectsModeExplorerBtn').click();
        await waitFor(
          async () => (await page.locator('#projectsTreeList', { hasText: 'CLAUDE.md' }).count()) > 0,
          { timeoutMs: 15000, label: 'explorer lists CLAUDE.md' },
        );
        await assertNoTemplatePush(page);
        if (fs.existsSync(path.join(projPath, 'AGENTS.md'))) throw new Error('AGENTS.md appeared next to CLAUDE.md');
      });

      await j.step('Selecting a folder outside the projects folder is refused', async () => {
        for (const outside of [process.cwd(), os.tmpdir()]) {
          const res = await request.put(`${base}/api/projects/selected`, { data: { slug: 'outside', path: outside } });
          if (res.status() !== 400) throw new Error(`PUT selected ${outside} -> ${res.status()}, expected 400`);
        }
        const sel = await getJson(request, `${base}/api/projects/selected`);
        const picked = sel.selected || sel;
        if (picked.slug !== slug) throw new Error(`refused selection changed the active project to ${picked.slug}`);
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
        if (overflow > 2) throw new Error(`Horizontal overflow on ${viewport.name}: ${overflow}px`);
      });
    } finally {
      await request.put(`${base}/api/projects/selected`, { data: {} }).catch(() => {});
      await request.delete(`${base}/api/projects/${encodeURIComponent(slug)}?confirm=true`).catch(() => {});
    }
  },
};
