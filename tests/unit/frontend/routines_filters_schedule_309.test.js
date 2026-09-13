import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { filterRoutinesList, getHumanCronPreview } from '../../../src/web/static/modules/studios/routines.js';

describe('CARD-309 Routines filters + schedule honesty', () => {
  const html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  const js = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/routines.js'), 'utf-8');

  it('exposes filter bar and honest Active copy', () => {
    expect(html).toContain('id="routinesFilterBar"');
    expect(html).toContain('id="routinesFilterSearch"');
    expect(html).toContain('id="routinesFilterAgent"');
    expect(html).toContain('id="routinesFilterStatus"');
    expect(html).toContain('id="routinesFilterLastRan"');
    expect(html).toMatch(/paused.*Resume|Resume.*paused/i);
    expect(html).toContain('enabled');
  });

  it('shows exact stored cron preview and weekday presets', () => {
    expect(html).toContain('id="routineCronExactPreview"');
    expect(html).toContain('0 9 * * 1-5');
    expect(js).toContain('syncCronExactPreview');
    expect(getHumanCronPreview('0 9 * * 1-5')).toMatch(/Weekdays/);
  });

  it('filters by agent/status/lastRan/search on real fields', () => {
    const rows = [
      { id: 'a', name: 'Alpha', agent_id: 'assistant', enabled: true, last_run_at: '2026-01-01', prompt: 'hello' },
      { id: 'b', name: 'Beta', agent_id: 'sre', enabled: false, last_run_at: null, prompt: 'world' },
    ];
    expect(filterRoutinesList(rows, { agent: 'sre' }).map((r) => r.id)).toEqual(['b']);
    expect(filterRoutinesList(rows, { status: 'active' }).map((r) => r.id)).toEqual(['a']);
    expect(filterRoutinesList(rows, { lastRan: 'never' }).map((r) => r.id)).toEqual(['b']);
    expect(filterRoutinesList(rows, { search: 'beta' }).map((r) => r.id)).toEqual(['b']);
  });
});
