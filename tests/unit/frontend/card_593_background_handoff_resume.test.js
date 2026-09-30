import { describe, it, expect } from 'vitest';

import * as hitl from '../../../src/web/static/modules/studios/chat/hitl.js';

/** CARD-593: a hand-off approval returns at once; the card polls /api/approvals/{id}/resume (phone-safe). */

const resp = (status, body) => ({ status, ok: status >= 200 && status < 300, json: async () => body });

describe('CARD-593 background hand-off resume', () => {
  it('polls until the work ends and survives network blips', async () => {
    const answers = [
      () => { throw new Error('offline'); },
      () => resp(200, { status: 'running' }),
      () => resp(502, {}),
      () => resp(200, { status: 'completed', summary: 'Card done.' }),
    ];
    const urls = [];
    const updates = [];
    const out = await hitl.pollBackgroundResume('appr_1', {
      fetchImpl: async (url) => { urls.push(url); return answers.shift()(); },
      sleep: async () => {},
      onUpdate: (b) => updates.push(b.status),
    });
    expect(out).toEqual({ status: 'completed', summary: 'Card done.' });
    expect(urls.every((u) => u === '/api/approvals/appr_1/resume')).toBe(true);
    expect(updates).toEqual(['running', 'completed']);
  });

  it('a 404 (server restarted) ends as lost', async () => {
    const out = await hitl.pollBackgroundResume('appr_2', { fetchImpl: async () => resp(404, {}), sleep: async () => {} });
    expect(out.status).toBe('lost');
  });

  it('never resumes the chat while running or lost; resumes after completed or failed', () => {
    const base = { approvalSessionId: 's1_child_ab', openSessionId: 's1', backendResumed: false, resumeChat: true };
    expect(hitl.shouldResumeChatAfterHitl({ ...base, nestedStatus: 'running' })).toBe(false);
    expect(hitl.shouldResumeChatAfterHitl({ ...base, nestedStatus: 'lost' })).toBe(false);
    expect(hitl.shouldResumeChatAfterHitl({ ...base, nestedStatus: 'approval_required' })).toBe(false);
    expect(hitl.shouldResumeChatAfterHitl({ ...base, nestedStatus: 'completed' })).toBe(true);
    expect(hitl.shouldResumeChatAfterHitl({ ...base, nestedStatus: 'failed' })).toBe(true);
  });

  it('says in plain words what is happening', () => {
    expect(hitl.backgroundStatusText({ status: 'running' })).toMatch(/background; you can leave this page/);
    expect(hitl.backgroundStatusText({ status: 'completed' })).toBe('Approved. The hand-off finished.');
    expect(hitl.backgroundStatusText({ status: 'failed', summary: 'no developer' }, 'REJECTED'))
      .toBe('Rejected. The hand-off failed: no developer');
    expect(hitl.backgroundStatusText({ status: 'lost' })).toMatch(/server restarted/);
  });
});
