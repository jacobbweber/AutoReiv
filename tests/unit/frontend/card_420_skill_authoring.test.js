/**
 * CARD-420: Skill Studio Build/Review packet, visible job, accept-to-draft.
 * REQ-420-001..005
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { formatStandingJourneyEvent } from '../../../src/web/static/modules/studios/observability.js';
import {
  AUTHORING_JOBS_URL,
  AUTHORING_LINT_URL,
  PACKET_SCHEMA,
  PACKET_VERSION,
  SILENT_RUNBOOK_URL,
  applyAuthoringPatches,
  authoringRequestPlan,
  buildAuthoringPacket,
  lintRequestPlan,
  planAuthoringWatch,
  rejectAuthoringPatches,
  runCheapLint,
  submitSkillAuthoring,
} from '../../../src/web/static/modules/studios/skill_authoring.js';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

function sliceView(html, startId, endId) {
  const start = html.indexOf(`id="${startId}"`);
  const end = html.indexOf(`id="${endId}"`);
  expect(start).toBeGreaterThan(-1);
  expect(end).toBeGreaterThan(start);
  return html.slice(start, end);
}

const draft = {
  skill_id: 'wiki_digest',
  name: 'Wiki Digest',
  description: 'File a short wiki digest',
  tier: 'pack',
  safety: { read_only: true, requires_hitl: false, untrusted_input_allowed: false },
  requires_tools: ['wiki_note_read'],
  markdown: '---\nname: Wiki Digest\n---\n# Wiki Digest\n',
  intent_notes: 'Keep it short',
  source_context: '',
};

describe('Skill Studio developer authoring [CARD-420]', () => {
  const html = read('src/web/templates/index.html');
  const skillView = sliceView(html, 'view-skill-studio', 'artifactModal');
  const skillStudio = read('src/web/static/modules/studios/skill_studio.js');
  const authoring = read('src/web/static/modules/studios/skill_authoring.js');
  const pills = read('src/web/static/modules/studios/forge/skill_pills.js');

  it('packet shape is versioned and Build is not a silent runbook rewrite [REQ-420-001, REQ-420-004]', () => {
    const packet = buildAuthoringPacket({
      intent: 'build',
      draft,
      blockers: [{ code: 'TOOL-UNKNOWN', message: 'Unknown catalog tool ids: nope' }],
    });
    expect(packet.schema).toBe(PACKET_SCHEMA);
    expect(packet.schema).toBe('skill_studio_authoring_packet');
    expect(packet.version).toBe(PACKET_VERSION);
    expect(packet.version).toBe(1);
    expect(packet.studio).toBe('skill');
    expect(packet.intent).toBe('build');
    expect(packet.agent_id).toBe('developer');
    expect(packet.draft.skill_id).toBe('wiki_digest');
    expect(packet.lint.cheap).toBe(true);
    expect(packet.lint.blockers[0].code).toBe('TOOL-UNKNOWN');
    expect(packet.llm_rewrite).toBe(false);

    const build = authoringRequestPlan('build');
    const review = authoringRequestPlan('review');
    const lint = lintRequestPlan();
    expect(build.url).toBe(AUTHORING_JOBS_URL);
    expect(build.url).not.toBe(SILENT_RUNBOOK_URL);
    expect(build.opensJob).toBe(true);
    expect(build.llmRewrite).toBe(false);
    expect(review.intent).toBe('review');
    expect(review.opensJob).toBe(true);
    expect(lint.url).toBe(AUTHORING_LINT_URL);
    expect(lint.opensJob).toBe(false);
    expect(lint.llmRewrite).toBe(false);
    expect(lint.url).not.toBe(SILENT_RUNBOOK_URL);
  });

  it('Build posts a visible developer job and cheap lint does not [REQ-420-001, REQ-420-002, REQ-420-004]', async () => {
    const calls = [];
    const fetchFn = async (url, opts) => {
      calls.push({ url, body: JSON.parse(opts.body) });
      if (url === AUTHORING_LINT_URL) {
        return {
          ok: true,
          json: async () => ({ opened_job: false, job_id: null, llm_rewrite: false, blockers: [] }),
        };
      }
      return {
        ok: true,
        json: async () => ({
          job_id: 'job_420visible',
          agent_id: 'developer',
          resumed: false,
          visible: true,
          llm_rewrite: false,
          packet: { schema: PACKET_SCHEMA, version: 1, studio: 'skill', intent: 'build' },
          watch: {
            primary: 'observe',
            observe: { studio: 'observe', job_id: 'job_420visible' },
            chat: { studio: 'chat', job_id: 'job_420visible', agent_id: 'developer' },
          },
        }),
      };
    };

    const lint = await runCheapLint(draft, { fetchFn });
    expect(lint.openedJob).toBe(false);
    expect(lint.llmRewrite).toBe(false);
    expect(calls[0].url).toBe(AUTHORING_LINT_URL);

    const job = await submitSkillAuthoring(draft, 'build', { fetchFn });
    expect(calls[1].url).toBe(AUTHORING_JOBS_URL);
    expect(calls[1].url).not.toContain('scaffold/runbook');
    expect(calls[1].body.intent).toBe('build');
    expect(calls[1].body.draft.skill_id).toBe('wiki_digest');
    expect(job.jobId).toBe('job_420visible');
    expect(job.agentId).toBe('developer');
    expect(job.llmRewrite).toBe(false);
    expect(job.persistedSkill).toBe(false);
    expect(job.watch.primary).toBe('observe');
    expect(planAuthoringWatch(job.jobId).observe.jobId).toBe('job_420visible');
    expect(planAuthoringWatch(job.jobId).chat.agentId).toBe('developer');
    expect(planAuthoringWatch('')).toBeNull();
  });

  it('Accept applies patches to the draft and Reject leaves it unchanged [REQ-420-003]', () => {
    const accepted = applyAuthoringPatches(draft, [
      { field: 'description', value: 'Shorter trigger text' },
      { field: 'skill_id', value: 'hijack' },
      { field: 'allowed_skill', value: ['nope'] },
    ]);
    expect(accepted.persisted).toBe(false);
    expect(accepted.changed).toBe(true);
    expect(accepted.draft.description).toBe('Shorter trigger text');
    expect(accepted.draft.skill_id).toBe('wiki_digest');
    expect(accepted.draft.allowed_skill).toBeUndefined();
    expect(accepted.ignored).toEqual(['skill_id', 'allowed_skill']);

    const rejected = rejectAuthoringPatches(draft);
    expect(rejected.changed).toBe(false);
    expect(rejected.persisted).toBe(false);
    expect(rejected.draft).toEqual(applyAuthoringPatches(draft, []).draft);
    expect(rejected.draft.description).toBe(draft.description);
    expect(rejected.draft.markdown).toBe(draft.markdown);
  });

  it('Skill Studio exposes Build/Review and does not retarget Agent Studio pills [REQ-420-002, REQ-420-005]', () => {
    expect(skillView).toContain('id="skillStudioBuildBtn"');
    expect(skillView).toContain('id="skillStudioReviewBtn"');
    expect(skillView).toContain('Watch in Observe');
    expect(skillView).toContain('Open in Chat');
    expect(skillView).toContain('id="skillStudioAcceptBtn"');
    expect(skillView).toContain('id="skillStudioRejectBtn"');
    expect(skillView).toContain('data-testid="skill-studio-lint"');
    expect(skillView).toContain('id="factorySaveSkillBtn"');

    expect(skillStudio).toContain('bindSkillStudioAuthoring');
    expect(skillStudio).toContain('/api/agent_training_factory/scaffold/save');
    expect(skillStudio).not.toContain('allowed_skill');
    expect(authoring).toContain('submitSkillAuthoring');
    expect(authoring).toContain('openObserveJob');
    expect(authoring).toContain("submitAuthoringDecision(authoringJobId, 'accept')");
    expect(authoring).toContain("submitAuthoringDecision(authoringJobId, 'reject')");
    const acceptFn = authoring.slice(
      authoring.indexOf('async function handleAcceptPatches'),
      authoring.indexOf('async function handleRejectPatches'),
    );
    expect(acceptFn).not.toContain('scaffold/save');
    expect(acceptFn).not.toContain('handleSaveSkill');
    expect(acceptFn).toContain('writeDraft');

    expect(pills).not.toContain('skillStudioBuildBtn');
    expect(pills).not.toContain('/api/skill_studio/authoring/jobs');

    expect(formatStandingJourneyEvent({
      kind: 'skill_studio_authoring_packet',
      payload: { intent: 'build', skill_id: 'wiki_digest', blocker_count: 1 },
    })).toContain('wiki_digest');
    expect(formatStandingJourneyEvent({
      kind: 'skill_studio_authoring_packet',
      payload: { intent: 'build', skill_id: 'wiki_digest', blocker_count: 1 },
    })).toContain('Skill Studio build packet');
  });

  it('cheap lint refuses a response that minted a job [REQ-420-004]', async () => {
    const fetchFn = async () => ({
      ok: true,
      json: async () => ({ opened_job: true, job_id: 'job_silent', llm_rewrite: true, blockers: [] }),
    });
    await expect(runCheapLint(draft, { fetchFn })).rejects.toThrow(/must not open a developer job/);
  });
});
