import { describe, it, expect, beforeEach } from 'vitest';
import { storageGet, storageSet, storageRemove } from '../../../src/web/static/modules/utils/storage.js';

describe('storage utility [REQ-FE-004]', () => {
  beforeEach(() => {
    // In node test env without window.localStorage, storage functions should return fallback safely
    if (typeof globalThis.localStorage === 'undefined') {
      globalThis.localStorage = {
        _store: {},
        getItem(key) { return this._store[key] || null; },
        setItem(key, val) { this._store[key] = String(val); },
        removeItem(key) { delete this._store[key]; },
        clear() { this._store = {}; }
      };
    }
    localStorage.clear();
  });

  it('safely stores and retrieves values', () => {
    storageSet('test_key', 'test_value');
    expect(storageGet('test_key')).toBe('test_value');
  });

  it('returns fallback value on missing key', () => {
    expect(storageGet('non_existent_key', 'default_val')).toBe('default_val');
  });

  it('removes keys safely', () => {
    storageSet('temp_key', '123');
    storageRemove('temp_key');
    expect(storageGet('temp_key')).toBeNull();
  });
});
