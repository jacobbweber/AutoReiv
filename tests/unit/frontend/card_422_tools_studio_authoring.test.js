/**
 * CARD-422: Tools Studio intent form and developer mediation.
 * REQ-422-001..004
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { renderCatalogMarkup } from '../../../src/web/static/modules/studios/tools_studio_catalog.js';
import {
  interpretAuthoringSubmit,
  interpretAuthoringTalk,
  intentValidationError,
  normalizeToolIntentDraft,
} from '../../../src/web/static/modules/studios/tools_studio_authoring.js';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

const draft = {
  intent: 'create',
  tool_name: 'wiki_note_peek',
  behavior: 'Look up a wiki note by title and return the first paragraph.',
  language_hint: 'Python',
  runtime_hint: 'in-process',
  path_context: 'packs/demo/tools',
  packaging_preference: 'native',
};

describe('Tools Studio authoring helper contracts [CARD-422, CARD-742]', () => {
  const html = read('src/web/templates/index.html');
  const chat = read('src/web/static/modules/studios/chat.js');

  it('retires legacy view-tools-studio and tools_studio.js [CARD-742]', () => {
    expect(html).not.toContain('id="view-tools-studio"');
    expect(html).not.toContain('id="toolsStudioCodeInput"');
    expect(fs.existsSync(path.join(repoRoot, 'src/web/static/modules/studios/tools_studio.js'))).toBe(false);
  });

  it('routes create, modify, and delete through Talk and Submit in tools_studio_authoring.js [REQ-422-001][REQ-422-004]', () => {
    const authoring = read('src/web/static/modules/studios/tools_studio_authoring.js');
    expect(authoring).toContain('/api/tools_studio/authoring/talk');
    expect(authoring).toContain('/api/tools_studio/authoring/jobs');
    expect(authoring).toContain('interpretAuthoringTalk');
    expect(authoring).toContain('interpretAuthoringSubmit');
    expect(authoring).toContain('openDeveloperSession');
    expect(chat).toContain('openDeveloperSession');
    expect(chat).toContain("async function openDeveloperSession(sessionId, composerText = '', agentId = 'toolsmith')");
    const markup = renderCatalogMarkup([
      {
        id: 'builtin',
        name: 'Built-in',
        source: 'platform',
        tools: [{ name: 'wiki_note_read', description: 'Read a wiki note' }],
      },
    ]);
    expect(markup).toContain('data-action="tools-studio-modify"');
    expect(markup).toContain('data-action="tools-studio-delete-intent"');
    expect(markup).toContain('data-tool-name="wiki_note_read"');
    expect(markup).not.toContain('<textarea');
    expect(markup).not.toContain('monaco');
  });
});

describe('Tools Studio mediation result interpretation [CARD-422]', () => {
  it('Talk requires a developer session that already contains the form [REQ-422-001]', () => {
    const plan = interpretAuthoringTalk({
      session_id: 'sess-1',
      agent_id: 'toolsmith',
      prompt: `Tool name: ${draft.tool_name}\nWhat it should do: ${draft.behavior}`,
      opened_job: false,
      job_id: null,
    }, draft);
    expect(plan.sessionId).toBe('sess-1');
    expect(plan.agentId).toBe('toolsmith');
    expect(plan.openedJob).toBe(false);
    expect(plan.prompt).toContain(draft.behavior);

    expect(() => interpretAuthoringTalk({
      session_id: 'sess-1',
      agent_id: 'toolsmith',
      prompt: 'empty of the form',
      opened_job: false,
    }, draft)).toThrow(/missing the tool intent/);
    expect(() => interpretAuthoringTalk({
      session_id: 'sess-2',
      job_id: 'job_queued',
      prompt: draft.behavior,
      opened_job: true,
    }, draft)).toThrow(/without starting a job/);
  });

  it('Submit refuses a queued or empty mediation result [REQ-422-002]', () => {
    expect(() => interpretAuthoringSubmit({
      job_id: 'job_1',
      session_id: 'sess-1',
      status: 'queued',
      ran: true,
      queued_only: false,
      mediation: 'developer_turn',
      reply: 'done',
    })).toThrow(/did not run/);
    expect(() => interpretAuthoringSubmit({
      job_id: 'job_1',
      session_id: 'sess-1',
      status: 'done',
      ran: false,
      queued_only: true,
      mediation: 'developer_turn',
      reply: 'done',
    })).toThrow(/did not run/);
    expect(() => interpretAuthoringSubmit({
      job_id: 'job_1',
      session_id: 'sess-1',
      status: 'done',
      ran: true,
      mediation: 'developer_turn',
      reply: '',
    })).toThrow(/empty reply/);
    expect(() => interpretAuthoringSubmit({
      job_id: 'job_1',
      session_id: 'sess-1',
      status: 'done',
      ran: true,
      mediation: 'developer_turn',
      reply: 'next step',
      packaging_applied: true,
    })).toThrow(/packaging/);

    const plan = interpretAuthoringSubmit({
      job_id: 'job_1',
      session_id: 'sess-1',
      agent_id: 'toolsmith',
      status: 'done',
      ran: true,
      queued_only: false,
      mediation: 'developer_turn',
      reply: 'I will add a read-only wiki lookup.',
      persisted_tool: false,
      packaging_applied: false,
    });
    expect(plan.jobId).toBe('job_1');
    expect(plan.status).toBe('done');
    expect(plan.ran).toBe(true);
    expect(plan.queuedOnly).toBe(false);
    expect(plan.persistedTool).toBe(false);
    expect(plan.packagingApplied).toBe(false);
  });

  it('rejects pasted implementation code and empty create intent [REQ-422-003][REQ-422-004]', () => {
    expect(() => normalizeToolIntentDraft({ ...draft, code: 'def peek(): pass' })).toThrow(/implementation code/);
    expect(intentValidationError({ intent: 'create', behavior: '' })).toMatch(/Describe what the tool should do/);
    expect(intentValidationError({ intent: 'delete', tool_name: '' })).toMatch(/Name the tool/);
    const clean = normalizeToolIntentDraft(draft);
    expect(clean.packaging_preference).toBe('native');
    expect(clean.code).toBeUndefined();
  });
});

describe('CARD-511: Submit carries the tool check result', () => {
  const AUTHORING = '../../../src/web/static/modules/studios/tools_studio_authoring.js';
  const base = {
    job_id: 'job_1', session_id: 's_1', status: 'done', ran: true, mediation: 'developer_turn', reply: 'Not registered.',
    persisted_tool: false, packaging_applied: false,
  };

  it('passes tool_checks through and still refuses persisted_tool (REQ-511-010)', async () => {
    const { interpretAuthoringSubmit: interpret, formatToolCheckLines } = await import(AUTHORING);
    const checks = [{ tool: 'x_tool', status: 'failed', stage: 'import', message: 'Not registered: x_tool failed the import check. ModuleNotFoundError' }];
    const plan = interpret({ ...base, tool_checks: checks });
    expect(plan.toolChecks).toEqual(checks);
    expect(interpret(base).toolChecks).toEqual([]);
    expect(() => interpret({ ...base, tool_checks: checks, persisted_tool: true })).toThrow('Tools Studio must not apply tool packaging from this form.');
    expect(formatToolCheckLines(checks)).toEqual(['Not registered: x_tool failed the import check. ModuleNotFoundError']);
    expect(formatToolCheckLines([{ tool: 'y', status: 'passed' }])).toEqual(['Checked: y']);
    expect(formatToolCheckLines(null)).toEqual([]);
  });

  it('tools_studio_authoring.js exports formatToolCheckLines', () => {
    const authoring = read('src/web/static/modules/studios/tools_studio_authoring.js');
    expect(authoring).toContain('export function formatToolCheckLines');
  });
});
