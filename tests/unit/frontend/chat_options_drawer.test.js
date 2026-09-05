import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Collapsible Chat Actions Drawer [CARD-142]', () => {
  let html;

  beforeEach(() => {
    html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  });

  it('provides compact input dock with options toggle button [REQ-CHAT-DRAWER-001]', () => {
    expect(html).toContain('id="chatOptionsToggleBtn"');
    expect(html).toContain('id="chatActiveModesIndicator"');
  });

  it('includes collapsible options drawer with close button [REQ-CHAT-DRAWER-002]', () => {
    expect(html).toContain('id="chatOptionsDrawer"');
    expect(html).toContain('id="chatOptionsCloseBtn"');
  });

  it('preserves all mode toggles and workflow selector IDs [REQ-CHAT-DRAWER-004]', () => {
    expect(html).toContain('id="verifyToggle"');
    expect(html).toContain('id="goalToggle"');
    expect(html).toContain('id="approvalToggle"');
    expect(html).toContain('id="workflowPicker"');
    expect(html).toContain('id="saveAsWorkflowBtn"');
  });

  it('provides action controls for file attachments and prompt catalog [REQ-CHAT-DRAWER-003]', () => {
    expect(html).toMatch(/id="chatAttachBtn(Placeholder)?"/);
    expect(html).toMatch(/id="chatPromptsBtn|chatPromptCatalogBtnPlaceholder"/);
  });

  it('provides context budget token badge, progress bar, and compact button [CARD-161]', () => {
    expect(html).toContain('id="chatContextTokensBadge"');
    expect(html).toContain('id="chatContextProgressBar"');
    expect(html).toContain('id="chatManualCompactBtn"');
  });

  it('provides loaded tools count badge, view tools button, and tools modal [CARD-161]', () => {
    expect(html).toContain('id="chatToolsCountBadge"');
    expect(html).toContain('id="chatViewToolsBtn"');
    expect(html).toContain('id="chatToolsModal"');
    expect(html).toContain('id="chatToolsSearchInput"');
    expect(html).toContain('id="chatToolsModalList"');
  });
});

describe('Chat Context & Tools Helpers [CARD-161]', () => {
  it('formats context budget badge correctly', async () => {
    const { formatContextBudgetBadge } = await import('../../../src/web/static/modules/studios/chat.js');
    expect(formatContextBudgetBadge(2150, 32768, 6.56)).toBe('2,150 / 32,768 tokens (6.6%)');
    expect(formatContextBudgetBadge(0, 8192, 0)).toBe('0 / 8,192 tokens (0.0%)');
  });

  it('filters tools list by name and description', async () => {
    const { filterToolsList } = await import('../../../src/web/static/modules/studios/chat.js');
    const tools = [
      { name: 'read_document_file', description: 'Read PDF, CSV, Excel files' },
      { name: 'query_agent_database', description: 'Execute SELECT queries' },
      { name: 'log_transactions', description: 'Record bank transactions' },
    ];
    expect(filterToolsList(tools, 'csv')).toEqual([tools[0]]);
    expect(filterToolsList(tools, 'database')).toEqual([tools[1]]);
    expect(filterToolsList(tools, 'TRANS')).toEqual([tools[2]]);
    expect(filterToolsList(tools, '')).toHaveLength(3);
    expect(filterToolsList(tools, 'nonexistent')).toHaveLength(0);
  });

  it('queries session context via mock fetch', async () => {
    const { querySessionContext } = await import('../../../src/web/static/modules/studios/chat.js');
    const mockFetch = async () => ({
      ok: true,
      json: async () => ({ used_tokens: 1500, max_tokens: 8192, percent_used: 18.3, tools_count: 3 }),
    });
    const data = await querySessionContext('test-sess-1', mockFetch);
    expect(data.used_tokens).toBe(1500);
    expect(data.tools_count).toBe(3);
  });

  it('posts session compaction via mock fetch', async () => {
    const { postSessionCompaction } = await import('../../../src/web/static/modules/studios/chat.js');
    const mockFetch = async () => ({
      ok: true,
      json: async () => ({ success: true, compaction_applied: true, turns_compacted: 4 }),
    });
    const result = await postSessionCompaction('test-sess-1', mockFetch);
    expect(result.success).toBe(true);
    expect(result.compaction_applied).toBe(true);
    expect(result.turns_compacted).toBe(4);
  });
});
