import { describe, it, expect } from 'vitest';
import { formatBytes, formatTokenCount, formatTimestamp, escapeHtml } from '../../../src/web/static/modules/utils/formatters.js';

describe('formatters utility [REQ-FE-004]', () => {
  it('formats bytes into readable SI units', () => {
    expect(formatBytes(0)).toBe('0 B');
    expect(formatBytes(1024)).toBe('1.0 KB');
    expect(formatBytes(1048576)).toBe('1.0 MB');
    expect(formatBytes(1073741824)).toBe('1.0 GB');
  });

  it('formats token counts into compact representations', () => {
    expect(formatTokenCount(500)).toBe('500');
    expect(formatTokenCount(1500)).toBe('1.5k');
    expect(formatTokenCount(1000000)).toBe('1.0M');
  });

  it('formats unix timestamp safely', () => {
    const ts = 1700000000;
    const formatted = formatTimestamp(ts);
    expect(typeof formatted).toBe('string');
    expect(formatted.length).toBeGreaterThan(0);
  });

  it('escapes special characters to prevent HTML injection', () => {
    expect(escapeHtml('<script>alert("XSS & danger")</script>')).toBe(
      '&lt;script&gt;alert(&quot;XSS &amp; danger&quot;)&lt;/script&gt;'
    );
    expect(escapeHtml('')).toBe('');
    expect(escapeHtml(null)).toBe('');
  });
});

