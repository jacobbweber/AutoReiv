import { describe, it, expect, vi, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  applyJobPhaseEvent,
  formatJobPhaseStrip,
  isJobPhaseChromeEvent,
  JOB_PHASE_CHROME_EVENTS,
} from '../../../src/web/static/modules/studios/chat.js';
import { forwardJobPhaseChromeEvent } from '../../../src/web/static/modules/studios/education.js';

describe('Unified Job phase chrome [CARD-240 / REQ-JOB-CHROME-001..003]', () => {
  let educationJs;
  let chatJs;

  beforeEach(() => {
    educationJs = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/studios/education.js'),
      'utf-8',
    );
    chatJs = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/studios/chat.js'),
      'utf-8',
    );
  });

  it('exports shared Job phase chrome event list from Chat [REQ-JOB-CHROME-002]', () => {
    expect(JOB_PHASE_CHROME_EVENTS).toEqual(expect.arrayContaining([
      'job_created',
      'phase_start',
      'plan_formulated',
      'approval_required',
    ]));
    expect(isJobPhaseChromeEvent('job_created')).toBe(true);
    expect(isJobPhaseChromeEvent('phase_start')).toBe(true);
    expect(isJobPhaseChromeEvent('plan_formulated')).toBe(true);
    expect(isJobPhaseChromeEvent('approval_required')).toBe(true);
    expect(isJobPhaseChromeEvent('token')).toBe(false);
    expect(chatJs).toMatch(/updateJobPhaseFromEvent/);
    expect(chatJs).toMatch(/updateJobPhaseFromEvent,/);
  });

  it('Education Ask wires SSE phase events into Chat strip (no second UI) [REQ-JOB-CHROME-001/002]', () => {
    expect(educationJs).toMatch(/REQ-JOB-CHROME/);
    expect(educationJs).toMatch(/forwardJobPhaseChromeEvent/);
    expect(educationJs).toMatch(/isJobPhaseChromeEvent|JOB_PHASE_CHROME_EVENTS/);
    expect(educationJs).toMatch(/updateJobPhaseFromEvent/);
    expect(educationJs).toMatch(/onEvent/);
    // Must re-apply after selectSession (which resets the strip)
    expect(educationJs).toMatch(/selectSession[\s\S]{0,400}forwardJobPhaseChromeEvent|forwardJobPhaseChromeEvent[\s\S]{0,200}selectSession/);
    // Anti-theatre: no Education-only progress chrome
    expect(educationJs.toLowerCase()).not.toMatch(/edu-phase-strip|educationPhaseStrip|eduJobProgress/);
  });

  it('forwardJobPhaseChromeEvent mounts Chat strip state from Education SSE sequence [REQ-JOB-CHROME-003]', () => {
    const calls = [];
    const chatCtrl = {
      updateJobPhaseFromEvent: (type, ev) => {
        calls.push({ type, ev });
      },
    };

    expect(forwardJobPhaseChromeEvent(chatCtrl, 'token', { text: 'hi' })).toBe(false);
    expect(forwardJobPhaseChromeEvent(null, 'job_created', { job_id: 'job_1' })).toBe(false);
    expect(forwardJobPhaseChromeEvent({}, 'job_created', { job_id: 'job_1' })).toBe(false);

    expect(forwardJobPhaseChromeEvent(chatCtrl, 'job_created', {
      job_id: 'job_edu_1',
      status: 'queued',
      phase_count: 2,
      agent_id: 'assistant',
    })).toBe(true);
    expect(forwardJobPhaseChromeEvent(chatCtrl, 'phase_start', {
      job_id: 'job_edu_1',
      phase_name: 'Formulate',
      index: 0,
      phase_count: 2,
    })).toBe(true);
    expect(forwardJobPhaseChromeEvent(chatCtrl, 'plan_formulated', {
      job_id: 'job_edu_1',
      steps: [{ title: 'a' }, { title: 'b' }],
      standing: true,
    })).toBe(true);
    expect(forwardJobPhaseChromeEvent(chatCtrl, 'approval_required', {
      job_id: 'job_edu_1',
      job_status: 'waiting_approval',
      react_state: 'PARKED',
    })).toBe(true);

    expect(calls.map((c) => c.type)).toEqual([
      'job_created',
      'phase_start',
      'plan_formulated',
      'approval_required',
    ]);
  });

  it('Education-style SSE sequence paints Formulate then waiting_approval strip via Chat applyJobPhaseEvent', () => {
    let state = {};
    state = applyJobPhaseEvent(state, 'job_created', {
      job_id: 'job_edu_docker',
      status: 'queued',
      phase_count: 2,
      agent_id: 'assistant',
    });
    state = applyJobPhaseEvent(state, 'phase_start', {
      job_id: 'job_edu_docker',
      phase_name: 'Formulate',
      index: 0,
      phase_count: 2,
    });
    let view = formatJobPhaseStrip(state);
    expect(view.jobId).toBe('job_edu_docker');
    expect(view.phaseLabel).toMatch(/Formulate/);
    expect(view.jobStatusLabel.toLowerCase()).toMatch(/running|queued/);

    state = applyJobPhaseEvent(state, 'plan_formulated', {
      job_id: 'job_edu_docker',
      steps: [{ title: 'search' }, { title: 'write' }],
      standing: true,
      status: 'running',
    });
    state = applyJobPhaseEvent(state, 'phase_start', {
      job_id: 'job_edu_docker',
      phase_name: 'Execute',
      index: 1,
      phase_count: 2,
    });
    state = applyJobPhaseEvent(state, 'approval_required', {
      job_id: 'job_edu_docker',
      job_status: 'waiting_approval',
      react_state: 'PARKED',
    });
    view = formatJobPhaseStrip(state);
    expect(view.phaseLabel).toMatch(/Execute/);
    expect(view.jobStatusLabel.toLowerCase()).toMatch(/waiting approval/);
    expect(view.reactState).toBe('PARKED');
  });
});
