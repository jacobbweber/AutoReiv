import { describe, it, expect } from 'vitest';
import {
  formatBytes,
  formatTokenCount,
  formatTimestamp,
  escapeHtml,
} from '../../../src/web/static/modules/utils/formatters.js';

describe('Formatters & Sanitizers Boundary Test Suite [REQ-FE-004, REQ-UNIT-003]', () => {
  describe('formatBytes', () => {
    it('formats bytes into readable SI units', () => {
      expect(formatBytes(0)).toBe('0 B');
      expect(formatBytes(1024)).toBe('1.0 KB');
      expect(formatBytes(1048576)).toBe('1.0 MB');
      expect(formatBytes(1073741824)).toBe('1.0 GB');
      expect(formatBytes(1099511627776)).toBe('1.0 TB');
    });

    it('handles negative, NaN, null, and non-numeric inputs safely', () => {
      expect(formatBytes(-100)).toBe('0 B');
      expect(formatBytes(null)).toBe('0 B');
      expect(formatBytes(undefined)).toBe('0 B');
      expect(formatBytes(NaN)).toBe('0 B');
      expect(formatBytes('invalid')).toBe('0 B');
    });
  });

  describe('formatTokenCount', () => {
    it('formats token counts into compact representations', () => {
      expect(formatTokenCount(500)).toBe('500');
      expect(formatTokenCount(1500)).toBe('1.5k');
      expect(formatTokenCount(1000000)).toBe('1.0M');
      expect(formatTokenCount(2500000000)).toBe('2.5B');
    });

    it('handles zero, negative, null, and non-numeric values gracefully', () => {
      expect(formatTokenCount(0)).toBe('0');
      expect(formatTokenCount(-50)).toBe('0');
      expect(formatTokenCount(null)).toBe('0');
      expect(formatTokenCount(undefined)).toBe('0');
      expect(formatTokenCount(NaN)).toBe('0');
      expect(formatTokenCount('invalid')).toBe('0');
    });
  });

  describe('formatTimestamp', () => {
    it('formats seconds and milliseconds unix timestamps safely', () => {
      const tsSeconds = 1700000000;
      const tsMs = 1700000000000;
      expect(typeof formatTimestamp(tsSeconds)).toBe('string');
      expect(typeof formatTimestamp(tsMs)).toBe('string');
      expect(formatTimestamp(tsSeconds).length).toBeGreaterThan(0);
      expect(formatTimestamp(tsMs).length).toBeGreaterThan(0);
    });

    it('formats valid ISO strings', () => {
      const iso = '2026-08-24T12:00:00Z';
      const formatted = formatTimestamp(iso);
      expect(typeof formatted).toBe('string');
      expect(formatted.length).toBeGreaterThan(0);
    });

    it('returns empty string on empty or invalid timestamps', () => {
      expect(formatTimestamp(null)).toBe('');
      expect(formatTimestamp(undefined)).toBe('');
      expect(formatTimestamp('')).toBe('');
      expect(formatTimestamp('not-a-real-date')).toBe('');
    });
  });

  describe('escapeHtml', () => {
    it('escapes special characters to prevent HTML/XSS injection', () => {
      expect(escapeHtml('<script>alert("XSS & danger")</script>')).toBe(
        '&lt;script&gt;alert(&quot;XSS &amp; danger&quot;)&lt;/script&gt;'
      );
      expect(escapeHtml("onclick='evil()';")).toBe('onclick=&#039;evil()&#039;;');
    });

    it('handles null, undefined, empty, and non-string values safely', () => {
      expect(escapeHtml('')).toBe('');
      expect(escapeHtml(null)).toBe('');
      expect(escapeHtml(undefined)).toBe('');
      expect(escapeHtml(12345)).toBe('12345');
    });
  });
});
