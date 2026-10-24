/**
 * CARD-420: authoring packet helpers stay; Skill Studio does not show Ask developer.
 * REQ-420-001..005
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { indexListedSkills } from '../../../src/web/static/modules/studios/skill_studio/skill_scope.js';
import { applyLoadedSkillView, skillDeleteRequest } from '../../../src/web/static/modules/studios/skill_studio/workshop_meta.js';
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

const draft = {
  skill_id: 'wiki_digest',
  name: 'Wiki Digest',
  description: 'File a short wiki digest',
  tier: 'pack',
  safety: { read_only: true, requires_hitl: false, untrusted_input_allowed: false },
  tools: ['wiki_note_read'],
  markdown: '---\nname: Wiki Digest\n---\n# Wiki Digest\n',
  intent_notes: 'Keep it short',
  source_context: '',
};

describe('Skill Studio authoring by Toolsmith [CARD-420, CARD-574, CARD-742]', () => {
  const html = read('src/web/templates/index.html');
  const capView = html.slice(html.indexOf('id="view-capabilities"'));
  const capStudio = read('src/web/static/modules/studios/capabilities_studio.js');
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
    expect(packet.agent_id).toBe('toolsmith'); // CARD-574
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

  it('Build posts a visible Toolsmith job and cheap lint does not [REQ-420-001, REQ-420-002, REQ-420-004]', async () => {
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
          agent_id: 'toolsmith',
          resumed: false,
          visible: true,
          llm_rewrite: false,
          packet: { schema: PACKET_SCHEMA, version: 1, studio: 'skill', intent: 'build' },
          watch: {
            primary: 'observe',
            observe: { studio: 'observe', job_id: 'job_420visible' },
            chat: { studio: 'chat', job_id: 'job_420visible', agent_id: 'toolsmith' },
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
    expect(job.agentId).toBe('toolsmith');
    expect(job.llmRewrite).toBe(false);
    expect(job.persistedSkill).toBe(false);
    expect(job.watch.primary).toBe('observe');
    expect(planAuthoringWatch(job.jobId).observe.jobId).toBe('job_420visible');
    expect(planAuthoringWatch(job.jobId).chat.agentId).toBe('toolsmith');
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

  it('Capabilities Studio does not show Ask developer and legacy view-skill-studio is retired [REQ-420-005, CARD-742]', () => {
    expect(html).not.toContain('id="view-skill-studio"');
    expect(capView).not.toContain('id="skillStudioAskDeveloperBtn"');
    expect(capView).not.toContain('>Ask developer</span>');
    expect(capView).not.toContain('id="skillStudioBuildBtn"');
    expect(capView).toContain('id="capabilitiesSaveFileBtn"');
    expect(capView).toContain('id="capabilitiesNewSkillBtn"');

    expect(capStudio).not.toContain('bindSkillStudioAuthoring');
    expect(capStudio).not.toContain('openObserveJob');
    expect(capStudio).not.toContain('skillStudioAskDeveloperBtn');
    expect(capStudio).not.toContain('confirm_seed');
    expect(capStudio).not.toContain('allowed_skill');
    expect(authoring).toContain('submitSkillAuthoring');
    expect(authoring).toContain('applyAuthoringPatches');
    expect(authoring).not.toContain('bindSkillStudioAuthoring');
    expect(authoring).not.toContain('skillStudioAskDeveloperBtn');
    expect(authoring).not.toContain('openObserveJob');
    expect(authoring).not.toContain('scaffold/save');

    expect(pills).not.toContain('skillStudioAskDeveloperBtn');
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

  it('delete confirms, encodes the id, and refuses protected skills', () => {
    const blocked = skillDeleteRequest('wiki', { confirmed: true, deletable: false });
    expect(blocked.allowed).toBe(false);
    expect(blocked.url).toBeNull();

    const unconfirmed = skillDeleteRequest('notes', { confirmed: false, deletable: true });
    expect(unconfirmed.allowed).toBe(false);

    const planned = skillDeleteRequest('group/notes', { confirmed: true, deletable: true });
    expect(planned.allowed).toBe(true);
    expect(planned.method).toBe('DELETE');
    expect(planned.url).toBe('/api/skills/user-skills/group/notes?confirm=true');
    expect(planned.url).not.toContain('confirm_seed');

    const loaded = applyLoadedSkillView({
      skill_id: 'notes',
      name: 'Notes',
      deletable: true,
      markdown_content: '# Notes\n',
    }, 'notes');
    expect(loaded.deletable).toBe(true);
    const seed = applyLoadedSkillView({ skill_id: 'wiki', name: 'Wiki' }, 'wiki');
    expect(seed.deletable).toBe(false);

    const options = indexListedSkills(
      [
        { id: 'notes', name: 'Notes', source: 'store', deletable: true },
        { id: 'wiki', name: 'Wiki', source: 'store', deletable: false },
      ],
      ['notes'],
    );
    expect(options.find((row) => row.id === 'notes').deletable).toBe(true);
    expect(options.find((row) => row.id === 'notes').source).toBe('assigned');
    expect(options.find((row) => row.id === 'wiki').deletable).toBe(false);
  });

  it('cheap lint refuses a response that minted a job [REQ-420-004]', async () => {
    const fetchFn = async () => ({
      ok: true,
      json: async () => ({ opened_job: true, job_id: 'job_silent', llm_rewrite: true, blockers: [] }),
    });
    await expect(runCheapLint(draft, { fetchFn })).rejects.toThrow(/must not open a Toolsmith job/);
  });
});
