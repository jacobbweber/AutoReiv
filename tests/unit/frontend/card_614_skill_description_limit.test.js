/** CARD-614: skill descriptions are shown in full; the counter is out of 200 and only warns. */
import { describe, it, expect } from 'vitest';
import {
  applyLoadedSkillView, cleanDescription, descriptionCounter, SKILL_DESCRIPTION_LIMIT,
} from '../../../src/web/static/modules/studios/skill_studio/workshop_meta.js';

const LONG = 'Use when Jacob asks to plan, water, feed or prune the vegetable garden beds, including seasonal sowing dates, frost warnings and the weekly watering rota.';

describe('CARD-614 skill description limit', () => {
  it('a loaded description is never cut', () => {
    expect(LONG.length).toBeGreaterThan(60);
    expect(applyLoadedSkillView({ skill_id: 'garden', description: LONG }, 'garden').description).toBe(LONG);
    const longer = `${LONG} ${LONG}`; // over the soft limit still loads in full
    expect(applyLoadedSkillView({ skill_id: 'garden', description: longer }, 'garden').description).toBe(longer);
  });

  it('the counter is out of 200 and warns near the limit', () => {
    expect(SKILL_DESCRIPTION_LIMIT).toBe(200);
    expect(descriptionCounter('')).toEqual({ text: '0/200', warn: false });
    expect(descriptionCounter(LONG)).toEqual({ text: `${LONG.length}/200`, warn: false });
    expect(descriptionCounter('x'.repeat(195)).warn).toBe(true);
  });

  it('line breaks typed in the box become one line for the front matter', () => {
    expect(cleanDescription('  Use when\n  planning beds  ')).toBe('Use when planning beds');
  });
});
