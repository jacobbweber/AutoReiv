/**
 * CARD-656 journey: Agent Studio skill list is name, one-line description and a switch.
 * 1) Architect's skills open in two groups, Enabled (sorted by name) above Available, with "N of M enabled",
 *    no tool chips or per-row badges, and one "Manage skills" link in the header.
 * 2) The search box filters both groups.
 * 3) Switching an enabled skill off moves it to Available; Save Profile persists it across a reload.
 * 4) Switching it back on moves it to Enabled; Save persists it and the allowlist is back to where it started.
 * Throwaway server only (live_qa); the agent ends with the same allowed skills it started with.
 */
import { waitFor, clickExpect } from './lib/runner.mjs';
import { getJson, openApp } from './lib/app.mjs';

const AGENT = 'architect';
const ids = (list) => (Array.isArray(list) ? list : []).map((s) => (typeof s === 'string' ? s : (s && (s.id || s.name)) || '')).filter(Boolean);

async function allowed(request, base) {
  return ids((await getJson(request, `${base}/api/agents/${AGENT}`)).allowed_skill);
}

async function openArchitect(page, base) {
  await openApp(page, base);
  if (!(await page.locator('#forgeAgentSelect').isVisible().catch(() => false))) await page.locator('#dock-agents').click();
  await page.locator('#forgeAgentSelect').waitFor({ state: 'visible', timeout: 20000 });
  await waitFor(async () => (await page.locator(`#forgeAgentSelect option[value="${AGENT}"]`).count()) > 0, { timeoutMs: 20000 });
  await page.selectOption('#forgeAgentSelect', AGENT);
  await waitFor(async () => /architect/i.test(await page.inputValue('#forgeNameInput').catch(() => '')), { timeoutMs: 20000 });
  const caps = page.locator('details[data-section="capabilities"]');
  await waitFor(async () => (await caps.getAttribute('aria-busy').catch(() => 'true')) !== 'true', { timeoutMs: 20000 });
  if (!(await caps.evaluate((el) => el.open).catch(() => true))) await caps.locator('summary').first().click();
  const ok = await waitFor(async () => (await page.locator('#forgeSkillsGrid .forge-skill-row').count()) > 0, { timeoutMs: 20000 });
  if (!ok) throw new Error('no skill rows rendered for Architect');
  await page.waitForTimeout(800); // the list can re-render once after the agent loads
}

const groupIds = (page, key) => page.locator(`[data-skill-group-list="${key}"] .forge-skill-row`).evaluateAll((rows) => rows.map((r) => r.dataset.skillId));
const groupNames = (page, key) => page.locator(`[data-skill-group-list="${key}"] .forge-skill-name`).allTextContents();
const sortedCopy = (xs) => [...xs].sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()));

async function save(page, request, base, want) {
  await page.locator('#saveAgentBtn').scrollIntoViewIfNeeded().catch(() => {});
  await clickExpect(page.locator('#saveAgentBtn'), async () => want(await allowed(request, base)),
    { label: 'Save Profile', what: 'the allowlist saved', timeoutMs: 20000 });
}

export default {
  id: 'card-656-agent-skills-simple-list',
  card: 'CARD-656',
  title: 'Agent Studio skills: Enabled on top, Available below, switch saves across reload',
  allow: [],
  async run(j, { page, request, base }) {
    let start = [];
    let target = '';

    await j.step('Architect skills: Enabled group on top, sorted, with a count and no tool chips', async () => {
      start = await allowed(request, base);
      await openArchitect(page, base);
      const en = await groupIds(page, 'enabled');
      const av = await groupIds(page, 'available');
      const count = (await page.locator('#forgeSkillCount').textContent()) || '';
      j.note(`allowed (API): ${start.join(', ')}; enabled rows: ${en.join(', ')}; available: ${av.length}; count "${count}"`);
      const top = await page.locator('[data-testid="forge-skill-group-enabled"]').boundingBox();
      const below = await page.locator('[data-testid="forge-skill-group-available"]').boundingBox();
      if (!top || !below || top.y >= below.y) throw new Error('Enabled group is not above Available');
      const missing = start.filter((id) => av.includes(id));
      if (missing.length) throw new Error(`allowed skills shown as Available: ${missing.join(', ')}`);
      if (!en.length) throw new Error('no enabled skills shown');
      for (const key of ['enabled', 'available']) {
        const names = await groupNames(page, key);
        if (JSON.stringify(names) !== JSON.stringify(sortedCopy(names))) throw new Error(`${key} group not sorted by name: ${names.join(', ')}`);
      }
      if (count.trim() !== `${en.length} of ${en.length + av.length} enabled`) throw new Error(`count reads "${count}"`);
      const sectionText = (await page.locator('#forgeSkillsSection').innerText()).toUpperCase();
      for (const noise of ['DECLARED TOOL', 'OPEN IN SKILL STUDIO', 'OS BASELINE']) {
        if (sectionText.includes(noise)) throw new Error(`skill section still shows "${noise.trim()}"`);
      }
      if (!(await page.locator('[data-testid="forge-open-skill-studio"]').isVisible())) throw new Error('no Manage skills link');
      await page.locator('#forgeSkillsSection').scrollIntoViewIfNeeded();
    });

    await j.step('Search filters both groups by name', async () => {
      const first = (await groupNames(page, 'enabled'))[0] || '';
      const q = first.slice(0, Math.min(5, first.length));
      await page.locator('#forgeSkillSearch').fill(q);
      await page.waitForTimeout(300);
      const visible = await page.locator('#forgeSkillsGrid .forge-skill-row:not(.hidden) .forge-skill-name').allTextContents();
      j.note(`search "${q}": ${visible.join(', ')}`);
      if (!visible.includes(first)) throw new Error(`search "${q}" hid ${first}`);
      const total = await page.locator('#forgeSkillsGrid [data-skill-group-list] .forge-skill-row').count();
      if (visible.length >= total) throw new Error('search did not filter anything');
      await page.locator('#forgeSkillsSection').scrollIntoViewIfNeeded();
      await page.locator('#forgeSkillSearch').fill('');
      await page.waitForTimeout(300);
    });

    await j.step('Switch one skill off: it moves to Available and stays off after Save and reload', async () => {
      const en = await groupIds(page, 'enabled');
      target = en.find((id) => id !== 'sqlite-storage') || en[0];
      const pill = page.locator(`.forge-skill-pill[data-skill-id="${target}"]`).first();
      await pill.scrollIntoViewIfNeeded();
      await pill.click();
      const moved = await waitFor(async () => (await groupIds(page, 'available')).includes(target), { timeoutMs: 5000 });
      if (!moved) throw new Error(`${target} did not move to Available`);
      await save(page, request, base, (list) => !list.includes(target));
      await page.reload();
      await openArchitect(page, base);
      const av = await groupIds(page, 'available');
      if (!av.includes(target)) throw new Error(`${target} is not in Available after reload`);
      j.note(`${target} off; saved allowlist: ${(await allowed(request, base)).join(', ')}`);
      await page.locator(`.forge-skill-row[data-skill-id="${target}"]`).first().scrollIntoViewIfNeeded();
    }, { timeoutMs: 90000 });

    await j.step('Switch it back on: it moves to Enabled and stays on after Save and reload', async () => {
      const pill = page.locator(`.forge-skill-pill[data-skill-id="${target}"]`).first();
      await pill.scrollIntoViewIfNeeded();
      await pill.click();
      const moved = await waitFor(async () => (await groupIds(page, 'enabled')).includes(target), { timeoutMs: 5000 });
      if (!moved) throw new Error(`${target} did not move to Enabled`);
      await save(page, request, base, (list) => list.includes(target));
      await page.reload();
      await openArchitect(page, base);
      if (!(await groupIds(page, 'enabled')).includes(target)) throw new Error(`${target} is not in Enabled after reload`);
      const end = await allowed(request, base);
      j.note(`${target} on; saved allowlist: ${end.join(', ')}`);
      if (JSON.stringify(sortedCopy(end)) !== JSON.stringify(sortedCopy(start))) throw new Error(`allowlist changed: ${start.join(',')} -> ${end.join(',')}`);
      await page.locator('#forgeSkillsSection').scrollIntoViewIfNeeded();
    }, { timeoutMs: 90000 });
  },
};
