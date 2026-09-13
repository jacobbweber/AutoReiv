import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('CARD-307 Journey + Debug under + Options', () => {
  const html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');

  it('keeps Journey/Debug ids but only inside chatOptionsDrawer', () => {
    expect(html).toContain('id="chatShowJourneyBtn"');
    expect(html).toContain('id="chatDebugToggleBtn"');
    const opt = html.indexOf('id="chatOptionsDrawer"');
    const journey = html.indexOf('id="chatShowJourneyBtn"');
    const debug = html.indexOf('id="chatDebugToggleBtn"');
    const workbench = html.indexOf('id="workbenchToggleBtn"');
    expect(opt).toBeGreaterThan(-1);
    expect(journey).toBeGreaterThan(opt);
    expect(debug).toBeGreaterThan(journey);
    // not in the top header cluster right after Workbench
    const headerSlice = html.slice(workbench, workbench + 900);
    expect(headerSlice).not.toContain('id="chatShowJourneyBtn"');
    expect(headerSlice).not.toContain('id="chatDebugToggleBtn"');
  });
});
