import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  formatKpiField,
  collectUniqueJobIdsFromTraces,
} from '../../../src/web/static/modules/studios/observability.js';

describe('CARD-311 Observe collapse + agent KPIs', () => {
  const html = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/templates/index.html'),
    'utf-8',
  );
  const obsJs = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/static/modules/studios/observability.js'),
    'utf-8',
  );
  const forgeJs = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/static/modules/studios/forge.js'),
    'utf-8',
  );

  it('wraps Observe sections as collapsed details.obs-section', () => {
    const names = ['metrics', 'agent-kpi', 'tools', 'logs', 'journey', 'capability'];
    for (const name of names) {
      expect(html).toContain(`data-obs-section="${name}"`);
    }
    expect(html).toMatch(/<details class="obs-section"/g);
    const matches = html.match(/<details class="obs-section"[^>]*>/g) || [];
    expect(matches).toHaveLength(6);
    for (const tag of matches) {
      expect(tag).not.toMatch(/\sopen\b/);
    }
  });

  it('exposes agent KPI select and journey chips', () => {
    expect(html).toContain('id="observeAgentKpiSelect"');
    expect(html).toContain('All agents');
    expect(html).toContain('id="standingJourneyChips"');
    expect(obsJs).toContain('/api/observability/kpi?agent_id=');
    expect(obsJs).toContain('/api/observability/traces?limit=30');
    expect(obsJs).toContain('loadStandingJourney');
  });

  it('keeps standing-journey on durable job_id (CARD-266 honesty)', () => {
    expect(obsJs).toContain('/api/observability/standing-journey?job_id=');
    expect(obsJs).toContain('HTTP ${res.status}');
  });

  it('collapses Agents Studio telemetry and links to Observe', () => {
    expect(html).toContain('data-section="telemetry"');
    expect(html).toContain('id="forgeOpenObserveBtn"');
    expect(forgeJs).toContain("callbacks.switchTab('observability')");
  });

  it('cache-busts app.js at 2.0.47', () => {
    expect(html).toMatch(/\/static\/app\.js\?v=2\.0\.(4[7-9]|[5-9]\d)/);
  });

  it('formatKpiField uses em-dash for omitted fields, not fake zeros', () => {
    expect(formatKpiField(null)).toBe('—');
    expect(formatKpiField(undefined)).toBe('—');
    expect(formatKpiField('')).toBe('—');
    expect(formatKpiField(0)).toBe('0');
    expect(formatKpiField(12.5, 'cost')).toBe('$12.50');
    expect(formatKpiField(0.005, 'cost')).toBe('$0.0050');
  });

  it('collectUniqueJobIdsFromTraces reads job_id on span or metadata only', () => {
    expect(
      collectUniqueJobIdsFromTraces([
        { id: 'a', metadata: { job_id: 'job_one' } },
        { id: 'b', job_id: 'job_two' },
        { id: 'c', metadata: { job_id: 'job_one' } },
        { id: 'd' },
      ]),
    ).toEqual(['job_one', 'job_two']);
  });
});
