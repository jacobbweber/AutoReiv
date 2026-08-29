/**
 * Frontend Unit Tests for Forge allowlist warning [REQ-FORGE-007].
 */

import { describe, it, expect } from 'vitest';
import {
  FORGE_ALLOWLIST_WARN_AT,
  allowlistWarningVisible,
  formatAllowlistWarning,
} from '../../../src/web/static/modules/utils/forge_allowlist.js';

describe('Forge allowlist warning threshold [REQ-FORGE-007]', () => {
  it('uses 12 as the single warn-at constant', () => {
    expect(FORGE_ALLOWLIST_WARN_AT).toBe(12);
  });

  it('hides the banner when the checked tool count is below 12', () => {
    expect(allowlistWarningVisible(0)).toBe(false);
    expect(allowlistWarningVisible(11)).toBe(false);
    expect(allowlistWarningVisible(11, FORGE_ALLOWLIST_WARN_AT)).toBe(false);
  });

  it('shows the banner when the checked tool count is 12 or more', () => {
    expect(allowlistWarningVisible(12)).toBe(true);
    expect(allowlistWarningVisible(15)).toBe(true);
  });

  it('includes the count and the threshold in the copy', () => {
    expect(formatAllowlistWarning(15)).toBe(
      '15 tools selected. Local models get unreliable past about 12. Split this into a specialist.'
    );
    expect(formatAllowlistWarning(12)).toContain('12 tools selected');
  });
});
