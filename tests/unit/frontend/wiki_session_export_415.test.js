import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

vi.mock('../../../src/web/static/modules/ui/toast.js', () => ({
  showToast: vi.fn(),
}));

vi.mock('../../../src/web/static/modules/dom.js', () => ({
  $: (id) => (id === 'activeAgentTitle' ? { textContent: 'AutoReiv' } : null),
  safeCreateIcons: () => {},
}));

import { exportSessionToWiki, exportMessageToWiki } from '../../../src/web/static/modules/studios/wiki/export.js';
import { showToast } from '../../../src/web/static/modules/ui/toast.js';

describe('CARD-415: Wiki session thread export', () => {
  let fetchMock;

  beforeEach(() => {
    fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({ status: 'success', filename: 'note.md' }),
    }));
    globalThis.fetch = fetchMock;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('exportSessionToWiki POSTs messages[] thread payload', async () => {
    const state = {
      selectedAgentId: 'autoreiv',
      activeSessionId: 'sess-1',
      messages: [
        { role: 'user', content: 'Hello' },
        { role: 'assistant', content: 'Hi there', reasoning: 'ignored in body' },
        { role: 'tool', content: '', name: 'noop' },
      ],
    };
    await exportSessionToWiki(state, 'sess-1');
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/export/wiki');
    const body = JSON.parse(opts.body);
    expect(body.messages).toHaveLength(2);
    expect(body.messages[0].role).toBe('user');
    expect(body.messages[1].content).toBe('Hi there');
    expect(body.category).toBe('inbox');
    expect(body.tags).toContain('chat_thread');
    expect(body.session_id).toBe('sess-1');
    expect(showToast).toHaveBeenCalled();
  });

  it('exportMessageToWiki still posts single_note content', async () => {
    await exportMessageToWiki({ selectedAgentId: 'autoreiv', activeSessionId: 's' }, 'note body');
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.content).toBe('note body');
    expect(body.tags).toContain('single_note');
  });

  it('exportSessionToWiki warns when thread empty', async () => {
    await exportSessionToWiki({ messages: [] }, null);
    expect(fetchMock).not.toHaveBeenCalled();
    expect(showToast).toHaveBeenCalledWith('No messages to export', 'warning');
  });
});
