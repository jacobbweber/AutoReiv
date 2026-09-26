import { describe, it, expect } from 'vitest';
import {
  formatHitlArgs,
  formatHitlOutput,
  pendingApprovalsUrl,
  approvalBelongsToOriginSession,
} from '../../../src/web/static/modules/studios/chat/hitl.js';
import {
  formatJobPhaseStrip,
  reactStateToneClass,
  createInlineJobChromeModel,
  applyInlineJobChromeModel,
  formatInlineJobChromeHtml,
} from '../../../src/web/static/modules/studios/chat.js';
import {
  buildChatStreamPayload,
  formatContextBudgetBadge,
  filterToolsList,
} from '../../../src/web/static/modules/studios/chat/stream.js';
import {
  isScrolledNearBottom,
  shouldShowJumpToLatest,
} from '../../../src/web/static/modules/studios/chat/scroll.js';

describe('Chat Decomposed Submodules [REQ-ARCH-003]', () => {
  describe('HITL Submodule', () => {
    it('formats string and json arguments correctly', () => {
      expect(formatHitlArgs(null)).toBe('');
      expect(formatHitlArgs('{"command": "echo test"}')).toContain('echo test');
      expect(formatHitlArgs({ code: 'print(123)' })).toContain('print(123)');
    });

    it('formats hitl output', () => {
      expect(formatHitlOutput(null)).toBe('');
      expect(formatHitlOutput({ stdout: 'success' })).toBe('success');
      expect(formatHitlOutput({ error: 'failed' })).toBe('Error: failed');
    });

    it('determines approval session matching', () => {
      expect(approvalBelongsToOriginSession('sess-1', 'sess-1')).toBe(true);
      expect(approvalBelongsToOriginSession('sess-1_child_2', 'sess-1')).toBe(true);
      expect(approvalBelongsToOriginSession('sess-2', 'sess-1')).toBe(false);
    });

    it('constructs pending approvals url with search params', () => {
      expect(pendingApprovalsUrl('agent-1', 'sess-1')).toBe('/api/approvals/pending?session_id=sess-1');
      expect(pendingApprovalsUrl('agent-1', '')).toBe('/api/approvals/pending?agent_id=agent-1');
    });
  });

  describe('Job Phase Submodule', () => {
    it('formats job phase strip correctly', () => {
      const view = formatJobPhaseStrip({
        jobId: 'job-123',
        jobStatus: 'running',
        phaseName: 'Formulate',
        phaseIndex: 0,
        phaseCount: 2,
        assignedAgentId: 'coder',
        reactState: 'THINKING',
      });
      expect(view.jobStatusLabel).toBe('Job running');
      expect(view.phaseLabel).toBe('Phase 1/2 Formulate');
      expect(view.agentLabel).toBe('coder');
      expect(view.reactState).toBe('THINKING');
    });

    it('formats react state tone class', () => {
      expect(reactStateToneClass('PARKED')).toContain('bg-amber-950');
      expect(reactStateToneClass('FAILED')).toContain('bg-rose-950');
      expect(reactStateToneClass('DONE')).toContain('bg-emerald-950');
      expect(reactStateToneClass('THINKING')).toContain('bg-sky-950');
    });

    it('updates inline job chrome model through lifecycle events', () => {
      let model = createInlineJobChromeModel();
      model = applyInlineJobChromeModel(model, 'phase_start', { phase_name: 'Formulate', index: 0 });
      expect(model.phases['Formulate'].status).toBe('running');

      model = applyInlineJobChromeModel(model, 'phase_complete', { phase_name: 'Formulate', index: 0, status: 'done' });
      expect(model.phases['Formulate'].status).toBe('done');

      const html = formatInlineJobChromeHtml(model);
      expect(html).toContain('Formulate');
      expect(html).toContain('Done');
    });
  });

  describe('Stream Submodule', () => {
    it('builds chat stream payload correctly', () => {
      const payload = buildChatStreamPayload({
        agentId: 'coder',
        sessionId: 'sess-abc',
        content: 'Hello world',
        selfVerify: true,
        approvalAutoRun: true,
      });
      expect(payload.agent_id).toBe('coder');
      expect(payload.session_id).toBe('sess-abc');
      expect(payload.content).toBe('Hello world');
      expect(payload.self_verify).toBe(true);
      expect(payload.approval_mode).toBe('run');
    });

    it('formats context budget badge and filters tools', () => {
      expect(formatContextBudgetBadge(1000, 4000, 25)).toBe('1,000 / 4,000 tokens (25.0%)');

      const tools = [{ name: 'file_search', description: 'Search files' }, { name: 'bash', description: 'Run shell' }];
      expect(filterToolsList(tools, 'search')).toHaveLength(1);
      expect(filterToolsList(tools, 'search')[0].name).toBe('file_search');
    });
  });

  describe('Scroll Submodule', () => {
    it('computes scroll near bottom correctly', () => {
      expect(isScrolledNearBottom(null)).toBe(true);
      const atBottom = { scrollHeight: 1000, scrollTop: 800, clientHeight: 200 };
      expect(isScrolledNearBottom(atBottom, 96)).toBe(true);

      const scrolledUp = { scrollHeight: 1000, scrollTop: 600, clientHeight: 200 };
      expect(isScrolledNearBottom(scrolledUp, 96)).toBe(false);
    });

    it('calculates jump to latest button visibility', () => {
      expect(shouldShowJumpToLatest({ stickToBottom: true, hasOverflow: true })).toBe(false);
      expect(shouldShowJumpToLatest({ stickToBottom: false, hasOverflow: true })).toBe(true);
      expect(shouldShowJumpToLatest({ stickToBottom: false, hasOverflow: false })).toBe(false);
    });
  });
});
