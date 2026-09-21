import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('CARD-308 Wiki Graduate Inbox pass/fail honesty', () => {
  const html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  const wikiJs =
    fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/wiki.js'), 'utf-8') +
    fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/wiki/templates.js'), 'utf-8');

  it('keeps Graduate Inbox (not Curate) and mentions held/failures', () => {
    expect(html).toMatch(/Graduate Inbox/);
    expect(html.toLowerCase()).not.toMatch(/>\s*curate inbox\s*</);
    expect(html).toMatch(/graduate_errors|pass\/fail|Failures stay/i);
    expect(wikiJs).toContain('held_count');
  });
});
