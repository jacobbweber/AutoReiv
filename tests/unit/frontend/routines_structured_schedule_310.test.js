import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { agentOptionsFromApiList, filterRoutinesList } from '../../../src/web/static/modules/studios/routines.js';

describe('CARD-310 agent roster + structured schedule chrome', () => {
  const html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');

  it('exposes structured schedule panel ids', () => {
    expect(html).toContain('id="routineStructuredSchedule"');
    expect(html).toContain('id="routineMonthBoxes"');
    expect(html).toContain('id="routineWeekdayBoxes"');
    expect(html).toContain('id="routineDomBoxes"');
    expect(html).toContain('id="routineEveryNWeeks"');
    expect(html).toContain('id="routineAnchorDate"');
    expect(html).toContain('id="routineNextFirePreview"');
  });

  it('agentOptionsFromApiList returns all agents sorted by name', () => {
    const opts = agentOptionsFromApiList([
      { id: 'zulu', name: 'Zulu' },
      { id: 'alpha', name: 'Alpha' },
      { id: 'mid', name: 'Mid' },
    ]);
    expect(opts.map((o) => o.id)).toEqual(['alpha', 'mid', 'zulu']);
    expect(opts).toHaveLength(3);
  });

  it('filter still respects agent_id field', () => {
    const rows = [
      { id: '1', agent_id: 'alpha', name: 'A', enabled: true },
      { id: '2', agent_id: 'beta', name: 'B', enabled: true },
    ];
    expect(filterRoutinesList(rows, { agent: 'beta' })).toHaveLength(1);
  });
});
