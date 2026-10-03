/** CARD-617: after an API reject the job card in the chat body says Stopped, like the strip (was Execute Running...). */
import { describe, it, expect } from 'vitest';
import { buildInlineJobChromeFromJourney } from '../../../src/web/static/modules/studios/chat/session_select.js';
import { formatJobChromePhasesRowsHtml } from '../../../src/web/static/modules/studios/chat/job_chrome.js';

const journey = (job) => ({ jobs: [{ id: 'job_1', status: 'waiting_approval', phases: [
  { id: 'p0', index: 0, name: 'Formulate', status: 'done' },
  { id: 'p1', index: 1, name: 'Execute', status: 'waiting_approval' },
], ...job }] });

describe('CARD-617 job card matches the strip', () => {
  it('a stopped job (approval decided outside the chat) shows its open step Stopped, not Running', () => {
    const model = buildInlineJobChromeFromJourney(journey({ stopped: true }));
    expect(model.phases.Execute.status).toBe('stopped');
    expect(model.streaming).toBe(false);
    const html = formatJobChromePhasesRowsHtml(model);
    expect(html).toContain('Stopped');
    expect(html).not.toContain('Running...');
    expect(html).toContain('Done'); // Formulate unchanged
  });

  it('a step waiting for an answer says so', () => {
    const j = journey({ status: 'running', waiting_answer: true });
    j.jobs[0].phases[1].status = 'queued';
    expect(formatJobChromePhasesRowsHtml(buildInlineJobChromeFromJourney(j))).toContain('Waiting for your answer');
  });

  it('a job really waiting for approval (not stopped) is unchanged', () => {
    const model = buildInlineJobChromeFromJourney(journey({}));
    expect(model.phases.Execute.status).toBe('running');
  });
});
