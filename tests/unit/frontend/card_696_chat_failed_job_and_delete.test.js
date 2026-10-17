import { describe, it, expect, vi } from 'vitest';
import { hydrateJobPhaseStateFromJourney } from '../../../src/web/static/modules/studios/chat/session_select.js';
import { formatJobPhaseStrip } from '../../../src/web/static/modules/studios/chat/job_strip.js';
import { renderSessionList, deleteSession } from '../../../src/web/static/modules/studios/chat/chrome.js';

describe('CARD-696: Failed job reason on reopen and session deletion', () => {
  it('hydrates the failed phase and failReason instead of the last queued phase when a job failed', () => {
    const journey = {
      jobs: [
        {
          id: 'job-fail-1',
          status: 'failed',
          fail_reason: 'phase_llm_error: Connection refused',
          phases: [
            {
              id: 'ph-1',
              index: 0,
              name: 'Build phase',
              status: 'failed',
              assigned_agent_id: 'autoreiv',
              fail_reason: 'phase_llm_error: Connection refused',
            },
            {
              id: 'ph-2',
              index: 1,
              name: 'Queued follow-up phase',
              status: 'queued',
              assigned_agent_id: 'autoreiv',
            },
          ],
        },
      ],
    };

    const state = hydrateJobPhaseStateFromJourney(journey);
    expect(state.jobStatus).toBe('failed');
    expect(state.reactState).toBe('FAILED');
    expect(state.phaseId).toBe('ph-1');
    expect(state.phaseName).toBe('Build phase');
    expect(state.phaseIndex).toBe(0);
    expect(state.failReason).toBe('phase_llm_error: Connection refused');

    const formatted = formatJobPhaseStrip(state);
    expect(formatted.jobStatusLabel).toBe('Job failed: phase_llm_error: Connection refused');
    expect(formatted.phaseLabel).toBe('Phase 1/2 Build phase');
    expect(formatted.reactState).toBe('FAILED');
  });

  it('renders a delete button per session row and deleteSession removes it and selects the next session', async () => {
    const made = [];
    globalThis.document = {
      createElement: () => {
        const el = {
          attrs: {},
          className: '',
          innerHTML: '',
          listeners: {},
          setAttribute(k, v) { this.attrs[k] = v; },
          addEventListener(ev, fn) { this.listeners[ev] = fn; },
        };
        made.push(el);
        return el;
      },
    };
    const list = { innerHTML: '', items: [], appendChild(el) { this.items.push(el); } };
    const state = {
      activeSessionId: 's-1',
      sessions: [
        { id: 's-1', title: 'First chat' },
        { id: 's-2', title: 'Second chat' },
      ],
    };
    renderSessionList({
      sessionList: list,
      sessions: state.sessions,
      activeSessionId: state.activeSessionId,
    });
    expect(list.items[0].innerHTML).toContain('data-testid="delete-session-s-1"');
    expect(list.items[1].innerHTML).toContain('data-testid="delete-session-s-2"');

    const selected = [];
    const fetchFn = vi.fn(async () => ({ ok: true, json: async () => ({ status: 'deleted', session_id: 's-1' }) }));
    await deleteSession(state, 's-1', {
      sessionList: list,
      selectSessionFn: async (id) => { selected.push(id); state.activeSessionId = id; },
      fetchFn,
    });

    expect(fetchFn).toHaveBeenCalledWith('/api/sessions/s-1', { method: 'DELETE' });
    expect(state.sessions.map((s) => s.id)).toEqual(['s-2']);
    expect(selected).toEqual(['s-2']);
  });
});
