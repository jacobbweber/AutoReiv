import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  agentsFromApiPayload,
  buildCreateAgentSelectList,
  buildFilterAgentOptionsHtml,
  readScheduleRuleFromUi,
} from '../../../src/web/static/modules/studios/routines.js';

describe('CARD-310 structured schedule + full agent pickers', () => {
  const html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  const js = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/routines.js'), 'utf-8');

  it('exposes structured schedule chrome ids', () => {
    expect(html).toContain('id="routineStructuredSchedulePanel"');
    expect(html).toContain('id="routineMonthPicker"');
    expect(html).toContain('id="routineWeekdayPicker"');
    expect(html).toContain('id="routineDomPicker"');
    expect(html).toContain('id="routineHourInput"');
    expect(html).toContain('id="routineMinuteInput"');
    expect(html).toContain('id="routineEveryNWeeksInput"');
    expect(html).toContain('id="routineAnchorDateInput"');
    expect(html).toContain('id="routineNextFirePreview"');
    expect(html).toContain('id="routineStructuredCronPreview"');
    expect(html).toContain('app.js?v=2.0.46');
  });

  it('filter and create agents use /api/agents — not routine-derived / 3-agent fallback', () => {
    expect(js).toContain("fetch('/api/agents')");
    expect(js).toContain('buildFilterAgentOptionsHtml');
    expect(js).toContain('buildCreateAgentSelectList');
    expect(js).not.toContain("id: 'librarian'");
    expect(js).not.toContain("id: 'sre-diagnostics'");
    expect(js).toMatch(/populateRoutinesFilterAgents[\s\S]*fetchAllAgents|fetchAllAgents[\s\S]*populateRoutinesFilterAgents/);

    const agents = [
      { id: 'assistant', name: 'Assistant' },
      { id: 'developer', name: 'Developer' },
      { id: 'autoreiv', name: 'AutoReiv' },
      { id: 'extra-agent', name: 'Extra' },
    ];
    expect(agentsFromApiPayload(agents).map((a) => a.id)).toHaveLength(4);
    expect(buildCreateAgentSelectList(agents)).toHaveLength(4);
    expect(buildCreateAgentSelectList([])).toEqual([]);
    const htmlOpts = buildFilterAgentOptionsHtml(agents);
    expect(htmlOpts).toContain('extra-agent');
    expect(htmlOpts).toContain('All agents');
  });

  it('readScheduleRuleFromUi collects chip selections', () => {
    function makeRoot(values) {
      return {
        querySelectorAll: (sel) => {
          if (sel !== 'button.schedule-chip.is-selected') return [];
          return values.map((v) => ({ dataset: { value: String(v) } }));
        },
      };
    }
    const rule = readScheduleRuleFromUi({
      monthRoot: makeRoot([1, 9]),
      weekdayRoot: makeRoot([2]),
      domRoot: makeRoot([]),
      hourInput: { value: '18' },
      minuteInput: { value: '0' },
      everyNInput: { value: '2' },
      anchorInput: { value: '2026-09-01' },
    });
    expect(rule.months).toEqual([1, 9]);
    expect(rule.weekdays).toEqual([2]);
    expect(rule.days_of_month).toBeNull();
    expect(rule.hour).toBe(18);
    expect(rule.every_n_weeks).toBe(2);
    expect(rule.anchor_date).toBe('2026-09-01');
  });
});
