/**
 * CARD-628: New skill whose id is taken is refused; suggested free id saves; shipped skill unchanged.
 */
import { clickExpect, waitFor } from './lib/runner.mjs';
import { getJson, openApp } from './lib/app.mjs';

async function openSkillStudio(page) {
  if (!(await page.locator('#view-skill-studio').isVisible().catch(() => false))) {
    await page.locator('#dock-skill-studio').click();
  }
  await page.locator('#view-skill-studio').waitFor({ state: 'visible', timeout: 20000 });
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

    await j.step('Open Skill Studio and start a New skill named Diagnostics', async () => {
      await openApp(page, base);
      await openSkillStudio(page);
      await page.locator('#factoryNewSkillFormBtn').click();
      await page.locator('#factorySkillNameInput').fill('Diagnostics');
      await page.locator('#factorySkillNameInput').dispatchEvent('input');
      await expectId(page, 'diagnostics');
      await page.locator('#factorySkillTriggerInput').fill('When to use this throwaway ' + marker);
      await page.locator('#factorySkillMarkdownEditor').fill(
        '---\nname: Diagnostics\ndescription: A throwaway skill for CARD-628 ' + marker + '\ntools: []\n---\n# Diagnostics\nDo nothing special.\n',
      );
    });

    await j.step('Save is refused with id-taken offer; shipped Diagnostics unchanged', async () => {
      await page.locator('#factorySaveSkillBtn').click();
      await page.locator('[data-testid="skill-studio-id-taken"]').waitFor({ state: 'visible', timeout: 15000 });
      await expectText(page, '[data-testid="skill-studio-id-taken"]', /already uses id/i);
      await shippedDiagnosticsUnchanged(request, base);
    });

    await j.step('Use suggested id diagnostics_2 and Save succeeds', async () => {
      await page.locator('[data-action="use-suggested-id"]').click();
      await expectId(page, 'diagnostics_2');
      await page.locator('#factorySaveSkillBtn').click();
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

async function expectId(page, id) {
  await waitFor(async () => (await page.locator('#factorySkillIdInput').inputValue()) === id, { timeoutMs: 5000 });
  const v = await page.locator('#factorySkillIdInput').inputValue();
  if (v !== id) throw new Error('expected skill id ' + id + ' got ' + v);
}

async function expectText(page, sel, re) {
  const t = await page.locator(sel).innerText();
  if (!re.test(t)) throw new Error('expected ' + re + ' in ' + t);
}
