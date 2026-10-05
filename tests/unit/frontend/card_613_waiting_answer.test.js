/** CARD-613: a job step that asked a question shows "Job waiting for answer"; the answer runs it again. */
import { describe, it, expect } from 'vitest';
import { formatJobPhaseStrip, applyJobPhaseEvent } from '../../../src/web/static/modules/studios/chat/job_strip.js';
import { hydrateJobPhaseStateFromJourney } from '../../../src/web/static/modules/studios/chat/session_select.js';

const journey = {
  jobs: [{
    id: 'job_1', status: 'running', stopped: false, waiting_answer: true,
    phases: [
      { id: 'p0', index: 0, name: 'Formulate', status: 'done', assigned_agent_id: 'autoreiv' },
      { id: 'p1', index: 1, name: 'Execute', status: 'queued', assigned_agent_id: 'autoreiv' },
    ],
  }],
};

describe('CARD-613 waiting for an answer', () => {
  it('hydrates on the waiting step, not as running or done', () => {
    const s = hydrateJobPhaseStateFromJourney(journey);
    expect(s).toMatchObject({ jobId: 'job_1', jobStatus: 'waiting_for_answer', reactState: 'WAITING', phaseId: 'p1' });
    expect(s.stopped).toBeUndefined(); // no Resume button: the reply continues it
    expect(formatJobPhaseStrip(s).jobStatusLabel).toBe('Job waiting for answer');
  });

  it('the live phase_complete event says so too, and the next phase_start clears it', () => {
    const s = applyJobPhaseEvent({ jobId: 'job_1' }, 'phase_complete', { job_id: 'job_1', status: 'waiting_for_answer', react_state: 'STOPPED' });
    expect(s.reactState).toBe('WAITING');
    expect(formatJobPhaseStrip(s).jobStatusLabel).toBe('Job waiting for answer');
    expect(applyJobPhaseEvent(s, 'phase_start', { job_id: 'job_1', phase_id: 'p1' })).toMatchObject({ jobStatus: 'running', reactState: 'THINKING' });
  });

  it('a stopped job still wins over waiting', () => {
    const s = hydrateJobPhaseStateFromJourney({ jobs: [{ ...journey.jobs[0], stopped: true }] });
    expect(s).toMatchObject({ stopped: true, reactState: 'STOPPED' });
  });
});
