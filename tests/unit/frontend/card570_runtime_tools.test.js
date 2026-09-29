import { describe, it, expect } from 'vitest';
import { runtimeToolApprovalText, mountRuntimeTools } from '../../../src/web/static/modules/studios/tools_studio_runtime_tools.js';

// Node env, no jsdom in this repo: labels and the no-host path only (the enable flow is covered live).
describe('CARD-570 runtime-built tools panel', () => {
  it('labels each approval state', () => {
    expect(runtimeToolApprovalText({ approval: 'enabled' })).toContain('Enabled');
    expect(runtimeToolApprovalText({ approval: 'needs_reapproval' })).toContain('Code changed');
    expect(runtimeToolApprovalText({ approval: 'disabled' })).toContain('Not enabled');
    expect(runtimeToolApprovalText(null)).toContain('Not enabled');
  });

  it('is a no-op without a host', async () => {
    const panel = mountRuntimeTools({ host: null });
    await expect(panel.refresh()).resolves.toBeUndefined();
  });
});
