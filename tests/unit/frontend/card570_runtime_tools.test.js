import { describe, it, expect } from 'vitest';
import { runtimeToolApprovalText, runtimeToolAttachText, mountRuntimeTools } from '../../../src/web/static/modules/studios/tools_studio_runtime_tools.js';

// Node env, no jsdom in this repo: labels and the no-host path only (the enable flow is covered live).
describe('CARD-570 runtime-built tools panel', () => {
  it('labels each approval state', () => {
    expect(runtimeToolApprovalText({ approval: 'enabled' })).toContain('Enabled');
    expect(runtimeToolApprovalText({ approval: 'needs_reapproval' })).toContain('Code changed');
    expect(runtimeToolApprovalText({ approval: 'disabled' })).toContain('Not enabled');
    expect(runtimeToolApprovalText(null)).toContain('Not enabled');
  });

  it('CARD-571: says what enabling also accepts', () => {
    expect(runtimeToolAttachText({ pending_attach: [] })).toBe('');
    expect(runtimeToolAttachText({ pending_attach: [{ agent_id: 'tutor', skill_id: 'c571-tool' }] }))
      .toBe('Enabling also gives it to: tutor (skill c571-tool).');
  });

  it('is a no-op without a host', async () => {
    const panel = mountRuntimeTools({ host: null });
    await expect(panel.refresh()).resolves.toBeUndefined();
  });
});
