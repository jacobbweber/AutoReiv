/**
 * CARD-711: Single-lever YAML frontmatter parsing, SKILL.md resolution, and SQLite DDL constants.
 */
import { openApp } from './lib/app.mjs';

export default {
  id: 'card-711-single-lever-frontmatter-and-ddl',
  card: 'CARD-711',
  title: 'Capabilities Studio and skill catalog load SKILL.md frontmatter cleanly via single-lever parser',
  allow: [],

  async run(j, { page, request, base }) {
    await j.step('1. Verify skill catalog API returns parsed skills cleanly', async () => {
      const res = await request.get(`${base}/api/skills/user-skills`);
      if (res.status() !== 200) {
        throw new Error(`Expected 200 from /api/skills/user-skills, got ${res.status()}`);
      }
      const data = await res.json();
      const skills = Array.isArray(data) ? data : data.skills || [];
      if (!skills.length) {
        throw new Error('Expected at least one skill from /api/skills/user-skills');
      }
      j.note(`verified /api/skills/user-skills returned ${skills.length} skills`);
    });

    await j.step('2. Open Capabilities Studio (#view-capabilities) and verify tree renders', async () => {
      await openApp(page, base);
      await page.evaluate(() => {
        window.__autoreivSwitchTab('capabilities');
      });
      await page.locator('#view-capabilities').waitFor({ state: 'visible', timeout: 10000 });
      await page.locator('#capabilitiesTreeList').waitFor({ state: 'visible', timeout: 10000 });
      j.note('verified #view-capabilities and #capabilitiesTreeList visible');
    });
  },
};
