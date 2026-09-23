/**
 * CARD-424: Tools Studio disable badge and save notice.
 * REQ-424-001, REQ-424-004
 */

import { describe, it, expect } from 'vitest';
import {
  describeMcpSaveNotice,
  mcpServerStatusBadge,
  renderMcpServerListMarkup,
} from '../../../src/web/static/modules/studios/tools_studio_catalog.js';

const mounted = {
  name: 'hyperv',
  enabled: true,
  is_mounted: true,
  tool_count: 2,
  tools: ['mcp_hyperv_ping', 'mcp_hyperv_list'],
  url: 'http://127.0.0.1:9/sse',
  transport: 'sse',
};

describe('Tools Studio MCP disable badge [CARD-424]', () => {
  it('shows plain Disabled after a successful unmount [REQ-424-004]', () => {
    const server = { ...mounted, enabled: false, is_mounted: false, tool_count: 0, tools: [] };
    expect(mcpServerStatusBadge(server)).toBe('Disabled');
    const markup = renderMcpServerListMarkup([server]);
    expect(markup).toContain('>Disabled<');
    expect(markup).not.toContain('still mounted');
    expect(markup).toContain('>Enable<');
  });

  it('keeps still-mounted wording only when the server is actually mounted', () => {
    const server = { ...mounted, enabled: false, is_mounted: true };
    expect(mcpServerStatusBadge(server)).toBe('Disabled (still mounted, 2 tools)');
    const markup = renderMcpServerListMarkup([server]);
    expect(markup).toContain('Disabled (still mounted, 2 tools)');
    expect(markup).not.toContain('>Disabled<');
  });

  it('warns when disable leaves the server mounted and stays quiet on the happy path', () => {
    const off = { name: 'hyperv', enabled: false };
    expect(describeMcpSaveNotice(off, { status: 'saved', mounted: false, tools: [] })).toEqual({
      kind: 'success',
      message: 'Disabled hyperv.',
    });
    const stuck = describeMcpSaveNotice(off, {
      status: 'saved',
      mounted: true,
      error: 'Configuration saved, but unmount failed: unmount refused',
    });
    expect(stuck.kind).toBe('warning');
    expect(stuck.message).toContain('still mounted');
    expect(describeMcpSaveNotice(
      { name: 'hyperv', enabled: true },
      { mounted: false, error: 'Configuration saved, but tool mounting failed: handshake down' },
    ).message).toBe('Saved hyperv, mount failed.');
  });
});
