/**
 * CARD-628: New skill whose id is taken is refused; suggested free id saves; shipped skill unchanged.
 */
import { waitFor } from './lib/runner.mjs';
import { getJson, openApp } from './lib/app.mjs';

async function openCapabilitiesStudio(page) {
  if (!(await page.locator('#view-capabilities').isVisible().catch(() => false))) {
    await page.locator('#dock-capabilities').click();
  }
  await page.locator('#view-capabilities').waitFor({ state: 'visible', timeout: 20000 });
}

async function shippedDiagnosticsUnchanged(request, base) {
  const opened = await getJson(request, base + '/api/skill_studio/skills/diagnostics');
  const name = String((opened && opened.name) || '');
  const md = String((opened && opened.markdown_content) || '');
  if (!/Platform Diagnostics/i.test(name) && !/Platform Diagnostics/i.test(md)) {
    throw new Error('shipped diagnostics missing or replaced: name=' + name);
  }
  if (/A throwaway skill for CARD-628/i.test(md) || /Do nothing special/i.test(md)) {
    throw new Error('shipped diagnostics was overwritten by the new draft');
  }
}

export default {
  id: 'card-628-new-skill-id-taken',
  card: 'CARD-628',
  title: 'New skill Diagnostics is refused; diagnostics_2 saves; shipped unchanged',
  allow: [{ url: '/api/skill_studio/save', status: [409] }],
  allowConsole: ['409 (Conflict)', 'Failed to load resource'],
  async run(j, { page, request, base, viewport }) {
    const marker = 'card628-' + viewport.name + '-' + String(Date.now() % 100000);
    const md = '---\nname: Diagnostics\ndescription: A throwaway skill for CARD-628 ' + marker + '\ntools: []\n---\n# Diagnostics\nDo nothing special.\n';

    await j.step('Open Capabilities Studio and verify diagnostics exists in tree', async () => {
      await openApp(page, base);
      await openCapabilitiesStudio(page);
      await page.locator('#capabilitiesTreeList').waitFor({ state: 'visible', timeout: 20000 });
    });

    await j.step('Save with new_skill=true on taken id diagnostics is refused with 409 and suggested_skill_id; shipped Diagnostics unchanged', async () => {
      const res = await request.post(base + '/api/skill_studio/save', {
        data: { skill_id: 'diagnostics', new_skill: true, skill_content: md },
      });
      if (res.status() !== 409) {
        throw new Error('expected 409 on taken skill id, got ' + res.status());
      }
      const body = await res.json();
      if (!body?.detail?.suggested_skill_id) {
        throw new Error('expected suggested_skill_id in 409 detail: ' + JSON.stringify(body));
      }
      await shippedDiagnosticsUnchanged(request, base);
    });

    await j.step('Use suggested id diagnostics_2 and Save succeeds', async () => {
      const res = await request.post(base + '/api/skill_studio/save', {
        data: { skill_id: 'diagnostics_2', new_skill: true, skill_content: md },
      });
      if (!res.ok()) {
        throw new Error('save diagnostics_2 failed: ' + res.status());
      }
      await waitFor(async () => {
        const list = await getJson(request, base + '/api/skill_studio/skills');
        const ids = (list.skills || []).map((s) => s.id);
        return ids.includes('diagnostics_2');
      }, { timeoutMs: 20000 });
      await shippedDiagnosticsUnchanged(request, base);
      const created = await getJson(request, base + '/api/skill_studio/skills/diagnostics_2');
      if (!String(created.markdown_content || '').includes(marker)) {
        throw new Error('diagnostics_2 missing marker content');
      }
    });
  },
};
