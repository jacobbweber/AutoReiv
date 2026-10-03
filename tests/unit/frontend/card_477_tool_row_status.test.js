import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

import { toolContentStatus, toolRowStatus, TOOL_ROW_STATUS } from '../../../src/web/static/modules/studios/chat/tool_status.js';

/** CARD-477: a tool row says what actually happened, never a green Complete for a tool that did not run. */

const ROOT = path.resolve(__dirname, '../../..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf-8');

describe('REQ-477-001: an approval park reads Waiting for approval (amber)', () => {
  it('the kernel park text and a parked JSON result', () => {
    expect(toolContentStatus('Tool Error: approval_required:appr_123')).toBe('waiting');
    expect(toolContentStatus('{"status": "parked", "approval_id": "a1"}')).toBe('waiting');
    expect(toolContentStatus('{"status": "approval_required"}')).toBe('waiting');
    const st = toolRowStatus({ role: 'tool', content: 'Tool Error: approval_required:appr_1' });
    expect(st.label).toContain('Waiting for approval');
    expect(st.cls).toBe('text-amber-400');
  });

  it('once a later row answers the same call, the park row reads Asked for approval', () => {
    const all = [
      { role: 'tool', tool_call_id: 'c1', content: 'Tool Error: approval_required:appr_1' },
      { role: 'tool', tool_call_id: 'c2', content: 'Tool Error: approval_required:appr_2' },
      { role: 'tool', tool_call_id: 'c1', content: '{"success": true}' },
    ];
    expect(toolRowStatus(all[0], 0, all).key).toBe('asked');
    expect(toolRowStatus(all[1], 1, all).key).toBe('waiting');
    expect(toolRowStatus(all[2], 2, all).key).toBe('complete');
  });
});

describe('REQ-477-002: an error or policy block reads Failed (rose)', () => {
  it('Tool Error, policy block and failed JSON results', () => {
    expect(toolContentStatus("Tool Error: Note 'x.md' not found")).toBe('failed');
    expect(toolContentStatus('Tool Error: tool_policy_blocked:DENY')).toBe('failed');
    expect(toolContentStatus('tool_policy_blocked:REQUIRE_CONFIRM but HITL engine missing')).toBe('failed');
    expect(toolContentStatus('{"success": false, "error": "boom"}')).toBe('failed');
    expect(toolContentStatus('{"status": "error"}')).toBe('failed');
    expect(toolRowStatus({ content: 'Tool Error: x' }).cls).toBe('text-rose-400');
  });

  it('a rejected approval and a call that was not run say so', () => {
    expect(toolContentStatus('Rejected. Tool did not run.')).toBe('rejected');
    expect(toolContentStatus('{"status": "rejected"}')).toBe('rejected');
    expect(toolContentStatus("Not run: the turn ended to wait for the user's answer to the clarification question.")).toBe('notRun');
  });
});

describe('REQ-477-003: anything else reads Complete', () => {
  it('plain text, JSON success, empty and non-JSON braces', () => {
    for (const c of ['done', '{"success": true}', '{"session_id": "abc"}', '', null, '{not json', '["a"]', 'The error rate is low']) {
      expect(toolContentStatus(c)).toBe('complete');
    }
    expect(toolRowStatus({ content: 'ok' })).toBe(TOOL_ROW_STATUS.complete);
  });
});

describe('render.js uses the helper', () => {
  it('no hard-coded green Complete label in the generic tool row', () => {
    const src = read('src/web/static/modules/studios/chat/render.js');
    expect(src).toContain("import { toolRowStatus } from './tool_status.js';");
    expect(src).toContain('toolRowStatus(msg, _idx, _allMessages)');
    expect(src).not.toContain('text-emerald-400 font-mono">\u2713 Complete');
    expect(src.split('\n').length).toBeLessThanOrEqual(800);
  });
});
