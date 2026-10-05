import { describe, expect, it } from 'vitest';
import { parseOriginsField } from '../../../src/web/static/modules/studios/settings_allowed_origins.js';

describe('CARD-602 allowed origins field', () => {
  it('splits lines and commas and drops blanks', () => {
    expect(parseOriginsField('https://a.example\n\nhttps://b.example, http://c.example ')).toEqual([
      'https://a.example',
      'https://b.example',
      'http://c.example',
    ]);
  });
  it('empty field is no extras', () => {
    expect(parseOriginsField('')).toEqual([]);
    expect(parseOriginsField(null)).toEqual([]);
  });
});
