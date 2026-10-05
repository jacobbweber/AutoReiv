/**
 * CARD-629: on phone, friction card summaries are full-width (not ~90px); badges stay on one line.
 */
import { openApp } from './lib/app.mjs';

const LONG = 'This is a long friction summary that must not squeeze into a ninety-pixel column on a phone width.';

const RECS = [
  {
    id: 'rec_629_patch', agent_id: 'autoreiv', skill_path: 'skills/wiki/SKILL.md', friction_type: 'search_thrashing',
    remedy_kind: 'runbook_patch', tool_name: 'wiki_note_search', status: 'pending', created_at: '2026-10-04T12:00:00Z',
    summary: LONG, proposed_patch: '- Enforce pagination limit on wiki_note_search.',
  },
  {
    id: 'rec_629_tool', agent_id: 'autoreiv', skill_path: null, friction_type: 'payload_bloat',
    remedy_kind: 'tool_escalation', tool_name: 'get_629_dump', payload_bytes: 20790, status: 'pending', created_at: '2026-10-04T12:00:00Z',
    summary: LONG, proposed_patch: 'Ask Developer to add pagination or a filter to get_629_dump.',
  },
  {
    id: 'rec_629_code', agent_id: 'autoreiv', skill_path: null, friction_type: 'payload_bloat',
    remedy_kind: 'code_change', tool_name: 'c629_builtin', status: 'pending', created_at: '2026-10-04T12:00:00Z',
    summary: LONG, proposed_patch: 'Built-in tool: c629_builtin needs a code change in AutoReiv.',
  },
];

export default {
  id: 'card-629-friction-card-phone-header',
  card: 'CARD-629',
  title: 'Friction card phone header: summary full width',
  async run(j, { page, base, viewport }) {
    await j.step('Observability friction cards: summary width >= 250px at this viewport', async () => {
      await page.route('**/api/observability/friction/recommendations*', async (route) => {
        if (route.request().method() !== 'GET') return route.continue();
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(RECS) });
      });
      await openApp(page, base);
      await page.locator('#dock-observability').click();
      await page.locator('#view-observability').waitFor({ state: 'visible', timeout: 15000 });
      const section = page.locator('#view-observability details[data-obs-section="friction"]');
      if (!(await section.getAttribute('open').catch(() => null))) {
        await section.locator(':scope > summary').click();
      }
      for (const id of ['rec_629_patch', 'rec_629_tool', 'rec_629_code']) {
        const card = page.locator(`#frictionRecommendationsList [data-rec-id="${id}"]`).first();
        await card.waitFor({ state: 'visible', timeout: 10000 });
        const summary = card.locator('.friction-rec-summary');
        await summary.waitFor({ state: 'visible', timeout: 5000 });
        const box = await summary.boundingBox();
        if (!box || box.width < 250) {
          throw new Error(`${id} summary width ${box && box.width} < 250 at ${viewport && viewport.name}`);
        }
        const badges = card.locator('span.uppercase.font-bold').first();
        const b = await badges.boundingBox();
        if (b && b.height > 40) {
          throw new Error(`${id} badge height ${b.height} looks wrapped`);
        }
      }
    });
  },
};
