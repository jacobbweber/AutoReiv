import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Chat Attachments UI [CARD-143]', () => {
  let html;

  beforeEach(() => {
    html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  });

  it('includes interactive attach button in options drawer [REQ-ATTACH-003]', () => {
    expect(html).toContain('id="chatAttachBtn"');
    expect(html).toContain('id="chatFileInput"');
  });

  it('includes attachments preview list container inside chat form [REQ-ATTACH-004]', () => {
    expect(html).toContain('id="chatAttachmentsPreviewList"');
  });
});
