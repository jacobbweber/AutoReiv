/** CARD-545: Tools Studio shows the risk a runtime tool declared, so Jacob sees it before enabling. */

import { describe, it, expect } from 'vitest';
import { runtimeToolRiskText } from '../../../src/web/static/modules/studios/tools_studio_runtime_tools.js';

describe('CARD-545: runtimeToolRiskText', () => {
  it('read-only runs without asking unless set to ask', () => {
    expect(runtimeToolRiskText({ risk: 'read_only', requires_hitl: false })).toBe('Declared read-only: runs without asking.');
    expect(runtimeToolRiskText({ risk: 'read_only', requires_hitl: true })).toBe('Declared read-only, but set to ask before each call.');
  });

  it('write, network and destructive ask before each call', () => {
    expect(runtimeToolRiskText({ risk: 'write', requires_hitl: true })).toBe('Declared write: asks before each call.');
    expect(runtimeToolRiskText({ risk: 'network', requires_hitl: false })).toBe('Declared network: asks before each call.');
    expect(runtimeToolRiskText({ risk: 'destructive', requires_hitl: true })).toBe('Declared destructive: asks before each call.');
  });

  it('an undeclared tool says so', () => {
    expect(runtimeToolRiskText({ requires_hitl: true })).toBe('No risk declared: asks before each call.');
    expect(runtimeToolRiskText({})).toBe('No risk declared.');
    expect(runtimeToolRiskText(null)).toBe('No risk declared.');
  });
});
