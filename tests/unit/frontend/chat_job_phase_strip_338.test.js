import { describe, expect, it } from 'vitest';
import {
  applyJobPhaseEvent,
  formatJobPhaseStrip,
  humanizeJobStatus,
} from '../../../src/web/static/modules/studios/chat.js';

describe('CARD-338: Chat Job ID Resolution and Phase Strip Hygiene', () => {
  it('humanizeJobStatus never returns "unknown" for empty, null, undefined, or "unknown"', () => {
    expect(humanizeJobStatus(null)).toBe('');
    expect(humanizeJobStatus(undefined)).toBe('');
    expect(humanizeJobStatus('')).toBe('');
    expect(humanizeJobStatus('   ')).toBe('');
    expect(humanizeJobStatus('unknown')).toBe('');
    expect(humanizeJobStatus('UNKNOWN')).toBe('');
    expect(humanizeJobStatus('running')).toBe('running');
    expect(humanizeJobStatus('waiting_approval')).toBe('waiting approval');
  });

  it('formatJobPhaseStrip never generates "Job unknown" for plain turns without jobId', () => {
    const plainTurnState = {
      reactState: 'DONE',
      assignedAgentId: 'autoreiv',
    };
    const view = formatJobPhaseStrip(plainTurnState);
    expect(view.jobId).toBe('');
    expect(view.jobStatusLabel).not.toMatch(/unknown/i);
    expect(view.jobStatusLabel).toBe('');
    expect(view.reactState).toBe('DONE');
  });

  it('formatJobPhaseStrip displays real jobStatusLabel and jobId when jobId is bound', () => {
    const standingJobState = {
      jobId: 'job_test_338',
      jobStatus: 'running',
      phaseName: 'Execute',
      phaseIndex: 1,
      phaseCount: 2,
      assignedAgentId: 'autoreiv',
      reactState: 'THINKING',
    };
    const view = formatJobPhaseStrip(standingJobState);
    expect(view.jobId).toBe('job_test_338');
    expect(view.jobStatusLabel).toBe('Job running');
    expect(view.phaseLabel).toBe('Phase 2/2 Execute');
    expect(view.agentLabel).toBe('autoreiv');
    expect(view.reactState).toBe('THINKING');
  });

  it('formatJobPhaseStrip defaults to "Job" (not "Job unknown") when jobId is set but status is missing', () => {
    const boundNoStatusState = {
      jobId: 'job_test_338_nostatus',
    };
    const view = formatJobPhaseStrip(boundNoStatusState);
    expect(view.jobId).toBe('job_test_338_nostatus');
    expect(view.jobStatusLabel).toBe('Job');
  });

  it('applyJobPhaseEvent preserves jobId and updates status through lifecycle', () => {
    let state = {};
    state = applyJobPhaseEvent(state, 'job_created', {
      job_id: 'job_auto_999',
      status: 'queued',
      agent_id: 'autoreiv',
      phase_count: 3,
    });
    expect(state.jobId).toBe('job_auto_999');
    expect(state.jobStatus).toBe('queued');

    state = applyJobPhaseEvent(state, 'phase_start', {
      job_id: 'job_auto_999',
      phase_name: 'Formulate',
      index: 0,
    });
    expect(state.jobId).toBe('job_auto_999');
    expect(state.jobStatus).toBe('running');
    expect(state.phaseName).toBe('Formulate');

    state = applyJobPhaseEvent(state, 'react_state', {
      job_id: 'job_auto_999',
      react_state: 'DONE',
      job_status: 'done',
    });
    expect(state.jobId).toBe('job_auto_999');
    expect(state.jobStatus).toBe('done');
    expect(state.reactState).toBe('DONE');

    const view = formatJobPhaseStrip(state);
    expect(view.jobId).toBe('job_auto_999');
    expect(view.jobStatusLabel).toBe('Job done');
  });

  it('plain turn react_state without job_id does not inject a fake jobId or "unknown" status', () => {
    let state = {};
    state = applyJobPhaseEvent(state, 'react_state', {
      react_state: 'DONE',
      assigned_agent_id: 'autoreiv',
    });
    expect(state.jobId).toBeFalsy();
    expect(state.jobStatus).toBeFalsy();
    expect(state.reactState).toBe('DONE');

    const view = formatJobPhaseStrip(state);
    expect(view.jobId).toBe('');
    expect(view.jobStatusLabel).toBe('');
  });
});
