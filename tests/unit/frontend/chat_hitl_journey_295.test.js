import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  isHitlParkSseEvent,
  hydrateJobPhaseStateFromJourney,
  formatJobPhaseStrip,
  applyJobPhaseEvent,
} from '../../../src/web/static/modules/studios/chat.js';

describe('Chat journey + HITL stay intact without refresh [CARD-295]', () => {
  let chatJs;

  beforeEach(() => {
    chatJs = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/studios/chat.js'),
      'utf-8',
    );
  });

  it('detects park-shaped SSE that must surface HITL on the live thread', () => {
    expect(isHitlParkSseEvent('approval_required', { approval_id: 'ap_1' })).toBe(true);
    expect(isHitlParkSseEvent('phase_complete', {
      status: 'waiting_approval',
      react_state: 'PARKED',
      job_id: 'job_1',
    })).toBe(true);
    expect(isHitlParkSseEvent('react_state', { react_state: 'PARKED', job_status: 'waiting_approval' })).toBe(true);
    expect(isHitlParkSseEvent('turn_done', { waiting_approval: true, job_id: 'job_1' })).toBe(true);
    expect(isHitlParkSseEvent('phase_start', { phase_name: 'Execute' })).toBe(false);
    expect(isHitlParkSseEvent('token', { text: 'hi' })).toBe(false);
  });

  it('hydrates job phase strip from session journey so refresh keeps chrome bound to same job_id', () => {
    const state = hydrateJobPhaseStateFromJourney({
      jobs: [
        {
          id: 'job_live_295',
          status: 'waiting_approval',
          goal: 'Park for HITL',
          phases: [
            { id: 'p0', index: 0, name: 'Formulate', status: 'done', assigned_agent_id: 'assistant' },
            { id: 'p1', index: 1, name: 'Execute', status: 'waiting_approval', assigned_agent_id: 'assistant' },
          ],
        },
      ],
    });
    expect(state).toBeTruthy();
    expect(state.jobId).toBe('job_live_295');
    expect(state.jobStatus).toBe('waiting_approval');
    expect(state.reactState).toBe('PARKED');
    expect(state.phaseName).toMatch(/Execute/i);
    const view = formatJobPhaseStrip(state);
    expect(view.jobId).toBe('job_live_295');
    expect(view.jobStatusLabel.toLowerCase()).toMatch(/waiting approval/);
    expect(view.phaseLabel).toMatch(/Execute/);
  });

  it('Formulate\u2192Execute\u2192approval_required keeps same job_id through park in applyJobPhaseEvent', () => {
    let state = {};
    state = applyJobPhaseEvent(state, 'job_created', {
      job_id: 'job_295',
      status: 'queued',
      phase_count: 2,
      agent_id: 'assistant',
    });
    state = applyJobPhaseEvent(state, 'phase_start', {
      job_id: 'job_295',
      phase_name: 'Formulate',
      index: 0,
      phase_count: 2,
    });
    state = applyJobPhaseEvent(state, 'phase_complete', {
      job_id: 'job_295',
      phase_name: 'Formulate',
      status: 'done',
      index: 0,
    });
    state = applyJobPhaseEvent(state, 'phase_start', {
      job_id: 'job_295',
      phase_name: 'Execute',
      index: 1,
      phase_count: 2,
    });
    state = applyJobPhaseEvent(state, 'approval_required', {
      job_id: 'job_295',
      approval_id: 'ap_295',
      react_state: 'PARKED',
      job_status: 'waiting_approval',
    });
    expect(state.jobId).toBe('job_295');
    expect(state.jobStatus).toBe('waiting_approval');
    expect(String(state.reactState).toUpperCase()).toBe('PARKED');
    expect(state.phaseName).toMatch(/Execute/i);
  });

  it('Chat stream path refreshes pending HITL on park and at stream end (no refresh required) [CARD-295]', () => {
    // Live SSE must drive full chrome (strip + inline), not strip-only.
    expect(chatJs).toMatch(/updateJobChromeFromEvent\(eventType,\s*ev\)/);
    // Park signal and stream finally must pull pending approvals into the live thread.
    const finallyChunk = chatJs.slice(chatJs.indexOf('async function executeChatTurn'));
    expect(finallyChunk).toMatch(/await refreshPendingHitl\(\)/);
    expect(chatJs).toMatch(/isHitlParkSseEvent\(/);
    expect(chatJs).toMatch(/hydrateJobPhaseStateFromJourney|hydrateJobChromeFromSession/);
  });
});
