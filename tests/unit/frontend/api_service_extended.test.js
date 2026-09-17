import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { api, fetchJSON } from '../../../src/web/static/modules/services/api.js';

describe('API Service Extended [REQ-ARCH-005]', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('preserves existing fetchJSON behavior', async () => {
    globalThis.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: 'healthy' }),
    });

    const data = await fetchJSON('/api/health');
    expect(data).toEqual({ status: 'healthy' });
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/health', {
      headers: { 'Content-Type': 'application/json' },
    });
  });

  it('provides api.get with query parameter serialization', async () => {
    globalThis.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ id: 'sess-1' }],
    });

    const data = await api.get('/api/chat/sessions', { agent_id: 'assistant', limit: 10 });
    expect(data).toEqual([{ id: 'sess-1' }]);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/chat/sessions?agent_id=assistant&limit=10',
      expect.objectContaining({ method: 'GET' })
    );
  });

  it('provides api.post with JSON body', async () => {
    globalThis.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true }),
    });

    const data = await api.post('/api/chat/sessions', { agent_id: 'assistant' });
    expect(data).toEqual({ success: true });
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/chat/sessions',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ agent_id: 'assistant' }),
      })
    );
  });

  it('provides api.put and api.delete helpers', async () => {
    globalThis.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ updated: true }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ deleted: true }),
      });

    const putRes = await api.put('/api/routines/1', { name: 'Updated' });
    expect(putRes).toEqual({ updated: true });

    const delRes = await api.delete('/api/routines/1');
    expect(delRes).toEqual({ deleted: true });
  });

  it('handles error messages from server response detail', async () => {
    globalThis.fetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: async () => ({ detail: 'Agent not found' }),
    });

    await expect(api.get('/api/agents/unknown')).rejects.toThrow('Agent not found');
  });

  it('provides domain-specific namespace helpers', async () => {
    globalThis.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ id: 'assistant' }],
    });

    const agents = await api.agents.list();
    expect(agents).toEqual([{ id: 'assistant' }]);
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/agents', expect.objectContaining({ method: 'GET' }));
  });
});
