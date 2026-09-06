/**
 * CARD-171: Lab Monitor verify fail reason line in live feed.
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

describe('Lab Monitor verify fail reason [CARD-171]', () => {
  it('exports formatLabPacketFeedLines and includes Reason for failed verify', async () => {
    const mod = await import('../../../src/web/static/modules/studios/forge.js');
    expect(typeof mod.formatLabPacketFeedLines).toBe('function');
    const lines = mod.formatLabPacketFeedLines({
      sender_role: 'verify',
      payload: {
        message: 'Verify battery FAILED (1/3) for manage_hyperv. Reason: Safety Guardrail Alert',
        passed: false,
        critic_notes: 'Safety Guardrail Alert: Path traversal segment detected',
        verify_rinse_count: 1,
      },
    });
    expect(lines[0]).toMatch(/FAILED/);
    expect(lines.some((l) => /^Reason:/i.test(l))).toBe(true);
    expect(lines.join('\n')).toMatch(/Path traversal|Safety Guardrail/i);
  });

  it('forge.js live feed uses formatLabPacketFeedLines', () => {
    const forgeJs = fs.readFileSync(path.join(repoRoot, 'src/web/static/modules/studios/forge.js'), 'utf-8');
    expect(forgeJs).toContain('formatLabPacketFeedLines');
    expect(forgeJs).toContain('critic_notes');
  });

  it('includes Rinse line for outer/inner failure class', async () => {
    const mod = await import('../../../src/web/static/modules/studios/forge.js');
    const lines = mod.formatLabPacketFeedLines({
      sender_role: 'scenario_verify',
      payload: {
        message: 'Scenario Verify FAILED — outer rinse (1/2) [sop_how]. Reason: Missing SOP',
        passed: false,
        critic_notes: 'Missing SOP for procedure',
        rinse_kind: 'outer',
        failure_class: 'sop_how',
      },
    });
    expect(lines.some((l) => /^Rinse:/i.test(l))).toBe(true);
    expect(lines.join('\n')).toMatch(/outer/i);
    expect(lines.some((l) => /^Reason:/i.test(l))).toBe(true);
  });

});
