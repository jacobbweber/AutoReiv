/** CARD-620: waiting_answer shows WAITING badge; stopped shows STOPPED + Resume path. */
import { describe, it, expect } from 'vitest';
import { formatJobPhaseStrip, reactStateToneClass } from '../../../src/web/static/modules/studios/chat/job_strip.js';
import { hydrateJobPhaseStateFromJourney } from '../../../src/web/static/modules/studios/chat/session_select.js';

describe('CARD-620 waiting badge', () => {
  it('waiting_answer hydrates WAITING, not STOPPED, and strip label says waiting for answer', () => {
    const s = hydrateJobPhaseStateFromJourney({
      jobs: [{
        id: 'job_w', status: 'running', stopped: false, waiting_answer: true,
        phases: [{ id: 'p1', index: 0, name: 'Execute', status: 'queued', assigned_agent_id: 'autoreiv' }],
      }],
    });
    expect(s).toMatchObject({ jobStatus: 'waiting_for_answer', reactState: 'WAITING' });
    expect(s.stopped).toBeUndefined();
    const strip = formatJobPhaseStrip(s);
    expect(strip.jobStatusLabel).toBe('Job waiting for answer');
    expect(strip.reactState).toBe('WAITING');
    expect(strip.stopped).toBe(false);
    expect(reactStateToneClass('WAITING')).toContain('amber');
  });

  it('a stopped job keeps STOPPED (negative)', () => {
    const s = hydrateJobPhaseStateFromJourney({
      jobs: [{
        id: 'job_s', status: 'running', stopped: true, waiting_answer: true,
        phases: [{ id: 'p1', index: 0, name: 'Execute', status: 'queued', assigned_agent_id: 'autoreiv' }],
      }],
    });
    expect(s).toMatchObject({ stopped: true, reactState: 'STOPPED' });
    const strip = formatJobPhaseStrip(s);
    expect(strip.reactState).toBe('STOPPED');
    expect(strip.jobStatusLabel).toBe('Job stopped');
    expect(strip.stopped).toBe(true);
  });
});
