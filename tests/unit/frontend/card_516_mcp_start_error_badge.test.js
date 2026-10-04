/**
 * CARD-516: an MCP server that cannot start shows "Failed to start" with the reason,
 * in Settings and Tools Studio; a working server is unchanged.
 */

import { describe, it, expect } from 'vitest';
import {
  describeMcpSaveNotice,
  formatMcpAttachStatus,
  mcpServerFailedToStart,
  mcpServerStatusBadge,
  mcpStartErrorSummary,
  renderMcpServerListMarkup,
  renderSettingsMcpStatus,
} from '../../../src/web/static/modules/studios/tools_studio_catalog.js';

const TRACE = "RuntimeError: MCP server 'c516' process terminated unexpectedly (exit code 1): Traceback (most recent call last):\n  File \"<string>\", line 1, in <module>\nModuleNotFoundError: No module named 'nonexistent_card516_mod'";

const broken = {
  name: 'c516', enabled: true, is_mounted: false, tool_count: 0, tools: [],
  command: ['python', '-c', 'import nonexistent_card516_mod'], last_error: TRACE,
};
const working = {
  name: 'weather', enabled: true, is_mounted: true, tool_count: 2,
  tools: ['mcp_weather_lookup', 'mcp_weather_ping'], command: ['python', 'server.py'], last_error: null,
};

describe('MCP start error badge [CARD-516]', () => {
  it('summarises a Python traceback to its header and last line', () => {
    expect(mcpStartErrorSummary(TRACE)).toBe(
      "MCP server 'c516' process terminated unexpectedly (exit code 1): ModuleNotFoundError: No module named 'nonexistent_card516_mod'",
    );
    expect(mcpStartErrorSummary('FileNotFoundError: [WinError 2] The system cannot find the file specified'))
      .toBe('FileNotFoundError: [WinError 2] The system cannot find the file specified');
    expect(mcpStartErrorSummary('')).toBe('');
    expect(mcpStartErrorSummary('x'.repeat(400))).toHaveLength(240);
  });

  it('only an enabled, unmounted server with a reason counts as failed', () => {
    expect(mcpServerFailedToStart(broken)).toBe(true);
    expect(mcpServerFailedToStart(working)).toBe(false);
    expect(mcpServerFailedToStart({ ...broken, enabled: false })).toBe(false);
    expect(mcpServerFailedToStart({ ...broken, last_error: null })).toBe(false);
  });

  it('Settings shows Failed to start with the reason; the working row is unchanged', () => {
    const { line, listHtml } = renderSettingsMcpStatus([broken, working]);
    expect(line).toBe('2 platform MCP servers attached (1 mounted, 1 failed to start).');
    expect(listHtml).toContain('>Failed to start<');
    expect(listHtml).toContain('data-testid="mcp-start-error"');
    expect(listHtml).toMatch(/No module named (&#0?39;|')nonexistent_card516_mod/);
    expect(listHtml).toContain('>Mounted (2)<');
    expect(listHtml).not.toContain('>Configured<');
    expect(renderSettingsMcpStatus([working]).listHtml).not.toContain('mcp-start-error');
    expect(formatMcpAttachStatus([working])).toBe('1 platform MCP server attached (1 mounted).');
  });

  it('Tools Studio rows say Failed to start and show the reason', () => {
    expect(mcpServerStatusBadge(broken)).toBe('Failed to start');
    expect(mcpServerStatusBadge(working)).toBe('Mounted (2 tools)');
    expect(mcpServerStatusBadge({ ...broken, last_error: null })).toBe('Configured');
    const markup = renderMcpServerListMarkup([broken]);
    expect(markup).toContain('Failed to start');
    expect(markup).toContain('data-testid="mcp-start-error"');
  });

  it('the save toast says why it did not start', () => {
    const notice = describeMcpSaveNotice({ name: 'c516', enabled: true }, {
      status: 'saved', mounted: false,
      error: `Configuration saved, but tool mounting failed: ${TRACE}`, last_error: TRACE,
    });
    expect(notice.kind).toBe('warning');
    expect(notice.message).toContain('Saved c516, but it did not start: ');
    expect(notice.message).toContain("No module named 'nonexistent_card516_mod'");
    expect(describeMcpSaveNotice({ name: 'weather', enabled: true }, { status: 'saved', mounted: true, tools: ['a'] }))
      .toEqual({ kind: 'success', message: 'Saved weather.' });
  });
});
