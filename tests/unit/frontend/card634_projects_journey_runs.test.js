/** CARD-634: Projects Manager markup includes Journey runs panel. */
import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('CARD-634 Projects journey runs panel', () => {
  let html;
  let js;
  beforeEach(() => {
    html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
    js = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/projects.js'), 'utf-8');
  });

  it('manager view has journey runs list and detail hosts', () => {
    expect(html).toContain('id="projectsJourneyRuns"');
    expect(html).toContain('id="projectsJourneyRunsList"');
    expect(html).toContain('id="projectsJourneyRunDetail"');
    expect(html).toContain('data-card="634"');
  });

  it('projects.js loads and opens journey runs', () => {
    expect(js).toContain('loadJourneyRuns');
    expect(js).toContain('/api/projects/journey-runs');
    expect(js).toContain('openJourneyRun');
  });
});
