/**
 * CARD-634: Projects Manager lists seeded journey runs and opens detail with failing step.
 */
import { openApp, getJson } from './lib/app.mjs';
import { waitFor } from './lib/runner.mjs';
import fs from 'fs';
import os from 'os';
import path from 'path';

async function openProjectsManager(page) {
  if (!(await page.locator('#projectsModeManagerBtn').isVisible().catch(() => false))) {
    await page.locator('#dock-projects').click();
  }
  await page.locator('#view-projects').waitFor({ state: 'visible', timeout: 20000 });
  await page.locator('#projectsModeManagerBtn').click();
  await waitFor(async () => {
    const mgr = page.locator('#projectsManagerView');
    return !(await mgr.evaluate((el) => el.classList.contains('hidden')).catch(() => true));
  }, { timeoutMs: 10000 });
}

export default {
  id: 'card-634-projects-journey-runs',
  card: 'CARD-634',
  title: 'Projects Studio lists journey runs',
  async run(j, { page, request, base, viewport }) {
    const root = process.env.AUTOREIV_QA_REPORT_DIR || path.join(os.tmpdir(), 'autoreiv-qa');
    const cardDir = path.join(root, 'card-634-seed');
    fs.mkdirSync(cardDir, { recursive: true });
    fs.writeFileSync(
      path.join(cardDir, 'report.json'),
      JSON.stringify({
        title: 'AutoReiv live QA',
        startedAt: new Date().toString(),
        base,
        runs: [
          {
            journey: 'card-634-seed',
            viewport: viewport.name,
            outcome: 'fail',
            steps: [
              {
                step: 'Expect green',
                status: 'fail',
                reason: 'seeded for CARD-634',
                screenshot: path.join(cardDir, 'seed.png'),
                ms: 1,
              },
            ],
            notes: [],
            consoleErrors: [],
            failedRequests: [],
          },
        ],
      }),
    );
    fs.writeFileSync(path.join(cardDir, 'summary.md'), '# seeded fail\n');
    fs.writeFileSync(path.join(cardDir, 'seed.png'), Buffer.from([0x89, 0x50, 0x4e, 0x47]));

    await j.step('API lists the seeded fail run with failing step', async () => {
      const body = await getJson(request, base + '/api/projects/journey-runs?limit=50');
      const row = (body.runs || []).find((r) => r.card === 'card-634-seed');
      if (!row) throw new Error('seed run missing from API');
      if (row.overall !== 'fail') throw new Error('expected fail');
      if (row.failing_step !== 'Expect green') throw new Error('failing_step=' + row.failing_step);
    });

    await j.step('Projects Manager shows the run and opens detail', async () => {
      // Throwaway env has no projects_root; set one so Projects Studio does not toast an error.
      const rootRes = await request.put(base + '/api/settings/projects_root', {
        data: { path: path.join(process.cwd(), 'scratch') },
      });
      if (!rootRes.ok()) throw new Error('set projects_root -> ' + rootRes.status());
      await openApp(page, base);
      await openProjectsManager(page);
      await page.locator('#projectsJourneyRunsRefreshBtn').click();
      const row = page.locator('.projects-journey-run[data-card-folder="card-634-seed"]');
      await row.waitFor({ state: 'visible', timeout: 15000 });
      await row.click();
      await page.locator('#projectsJourneyRunDetail').waitFor({ state: 'visible', timeout: 10000 });
      const title = await page.locator('#projectsJourneyRunDetailTitle').innerText();
      if (!/card-634-seed/.test(title)) throw new Error('detail title ' + title);
      const ready = await waitFor(async () => {
        const summ = (await page.locator('#projectsJourneyRunDetailSummary').innerText()).trim();
        return summ && !/^Loading/i.test(summ);
      }, { timeoutMs: 15000 });
      if (!ready) throw new Error('detail summary stayed on Loading');
      const summ = await page.locator('#projectsJourneyRunDetailSummary').innerText();
      if (!/Expect green|seeded for CARD-634/i.test(summ)) throw new Error('summary missing fail: ' + summ);
      const shot = page.locator('#projectsJourneyRunScreenshots', { hasText: 'seed.png' });
      await shot.waitFor({ state: 'visible', timeout: 5000 });
    });
  },
};
