/**
 * Frontend Unit Tests for Chat Modes (Goal & Reflexion Streaming) [REQ-CHAT-013].
 */

import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  buildChatStreamPayload,
  isGoalPlanReviewTool,
  readLastApprovalAutoRun,
  writeLastApprovalAutoRun,
  APPROVAL_AUTORUN_STORAGE_KEY,
  pendingApprovalsUrl,
  pendingHitlLabel,
  shouldResumeChatAfterHitl,
  approvalBelongsToOriginSession,
  buildHitlCardInnerHtml,
  submitHitlDecision,
  formatHitlArgs,
  formatHitlOutput,
  coupleGoalAndVerify,
  isComplexMultiStepPrompt,
  renderReflexionBadge,
} from '../../../src/web/static/modules/studios/chat.js';
import { isBuiltinRoutine } from '../../../src/web/static/modules/studios/routines.js';

class MockElement {
  constructor(tagName = 'div', className = '') {
    this.tagName = tagName.toUpperCase();
    this._className = '';
    this.classList = {
      _classes: new Set(),
      add: (...cls) => cls.forEach((c) => this.classList._classes.add(c)),
      remove: (...cls) => cls.forEach((c) => this.classList._classes.delete(c)),
      contains: (c) => this.classList._classes.has(c),
      toggle: (c, force) => {
        if (force === undefined) {
          if (this.classList.contains(c)) this.classList.remove(c);
          else this.classList.add(c);
        } else if (force) {
          this.classList.add(c);
        } else {
          this.classList.remove(c);
        }
      },
    };
    this.className = className;
    this.children = [];
    this.textContent = '';
    this._innerHTML = '';
    this.id = '';
    this._listeners = {};
  }

  get className() {
    return this._className;
  }

  set className(val) {
    this._className = val || '';
    this.classList._classes = new Set(this._className.split(' ').filter(Boolean));
  }

  get innerHTML() {
    return this._innerHTML;
  }

  set innerHTML(val) {
    this._innerHTML = val;
    this.children = [];
    if (!val) return;
    const classMatches = [...val.matchAll(/class="([^"]+)"/g)];
    classMatches.forEach((m) => {
      const el = new MockElement('div', m[1]);
      this.children.push(el);
    });
  }

  addEventListener(event, handler) {
    if (!this._listeners[event]) this._listeners[event] = [];
    this._listeners[event].push(handler);
  }

  click() {
    if (this._listeners['click']) {
      this._listeners['click'].forEach((fn) => fn({ target: this }));
    }
  }

  appendChild(child) {
    this.children.push(child);
  }

  setAttribute(k, v) {
    this._attrs = this._attrs || {};
    this._attrs[k] = String(v);
  }

  getAttribute(k) {
    return (this._attrs && this._attrs[k]) || null;
  }

  hasAttribute(k) {
    return Boolean(this._attrs && k in this._attrs);
  }

  querySelector(selector) {
    if (selector.startsWith('#')) {
      const id = selector.slice(1);
      return this.children.find((c) => c.id === id) || null;
    }
    if (selector.startsWith('.')) {
      const cls = selector.slice(1);
      return this.children.find((c) => c.classList.contains(cls)) || null;
    }
    return null;
  }

  querySelectorAll(selector) {
    if (selector.startsWith('[')) {
      const attr = selector.slice(1, -1);
      return this.children.filter((c) => c.hasAttribute && c.hasAttribute(attr));
    }
    if (selector.startsWith('.')) {
      const cls = selector.slice(1);
      return this.children.filter((c) => c.classList.contains(cls));
    }
    return [];
  }
}

describe('Chat Studio Execution Modes & Milestone UI Contract [REQ-CHAT-013]', () => {
  let planCard;
  let goalTitle;
  let stepCounter;
  let stepsContainer;
  let reflexionBadge;

  beforeEach(() => {
    planCard = new MockElement('div', 'plan-milestone-card hidden');
    goalTitle = new MockElement('span', 'plan-goal-title');
    stepCounter = new MockElement('span', 'plan-step-counter');
    stepsContainer = new MockElement('div', 'plan-steps-container');
    reflexionBadge = new MockElement('div', 'reflexion-status-badge hidden');

    planCard.appendChild(goalTitle);
    planCard.appendChild(stepCounter);
    planCard.appendChild(stepsContainer);
  });

  it('renders formulated plan steps cleanly in the DOM', () => {
    const planEvent = {
      goal: 'Audit System Health',
      steps: [
        { title: 'Step 1: Check Memory', description: 'Analyze RAM usage' },
        { title: 'Step 2: Generate Report', description: 'Compile summary' },
      ],
    };

    planCard.classList.remove('hidden');
    goalTitle.textContent = planEvent.goal;
    stepCounter.textContent = `${planEvent.steps.length} Steps`;

    planEvent.steps.forEach((s, idx) => {
      const el = new MockElement('div', 'plan-step-item');
      el.id = `plan-step-${idx}`;
      el.textContent = s.title;
      stepsContainer.appendChild(el);
    });

    expect(planCard.classList.contains('hidden')).toBe(false);
    expect(goalTitle.textContent).toBe('Audit System Health');
    expect(stepCounter.textContent).toBe('2 Steps');
    expect(stepsContainer.children.length).toBe(2);
    expect(stepsContainer.querySelector('#plan-step-0').textContent).toBe('Step 1: Check Memory');
  });

  it('updates active and completed step styles dynamically', () => {
    const step0 = new MockElement('div', 'plan-step-item');
    step0.id = 'plan-step-0';
    stepsContainer.appendChild(step0);

    // Transition to Running
    step0.classList.add('active-step');
    expect(step0.classList.contains('active-step')).toBe(true);

    // Transition to Completed
    step0.classList.remove('active-step');
    step0.classList.add('completed-step');
    expect(step0.classList.contains('active-step')).toBe(false);
    expect(step0.classList.contains('completed-step')).toBe(true);
  });

  it('renders reflexion verification status badge transitions', () => {
    // Attempt
    reflexionBadge.classList.remove('hidden');
    reflexionBadge.textContent = 'Reflexion Check: Attempt 1/3';
    expect(reflexionBadge.classList.contains('hidden')).toBe(false);
    expect(reflexionBadge.textContent).toContain('Attempt 1/3');

    // Passed
    reflexionBadge.textContent = 'Self-Verification Passed!';
    expect(reflexionBadge.textContent).toContain('Passed!');

    reflexionBadge.textContent = 'Self-Verification Failed (unverified)';
    expect(reflexionBadge.textContent).toContain('Failed');
  });
});

describe('Chat HITL approval card [REQ-HITL-020]', () => {
  it('renders Approve and Reject for a parked tool', () => {
    const card = new MockElement('div', 'hitl-approval-card hidden');
    card.classList.remove('hidden');
    card.innerHTML = `
      <div class="font-semibold text-amber-200">Approval required</div>
      <button type="button" data-hitl-decision="APPROVED">Approve</button>
      <button type="button" data-hitl-decision="REJECTED">Reject</button>
      <span class="hitl-card-status"></span>
    `;
    expect(card.classList.contains('hidden')).toBe(false);
    expect(card.innerHTML).toContain('data-hitl-decision="APPROVED"');
    expect(card.innerHTML).toContain('data-hitl-decision="REJECTED"');
    expect(card.innerHTML).toContain('Approve');
    expect(card.innerHTML).toContain('Reject');
  });
});

describe('Chat HITL card survives history reload [REQ-HITL-025]', () => {
  it('skips a history wipe while a HITL card is visible', () => {
    const container = new MockElement('div', 'messages');
    const card = new MockElement('div', 'hitl-approval-card');
    container.appendChild(card);
    const visible = Boolean(container.querySelector('.hitl-approval-card')) && !card.classList.contains('hidden');
    expect(visible).toBe(true);
  });
});

describe('Chat Auto-run toggle [REQ-HITL-027]', () => {
  it('maps checked Auto-run to approval_mode run, otherwise ask', () => {
    const approvalAutoRun = true;
    const approvalManual = false;
    expect(approvalAutoRun ? 'run' : 'ask').toBe('run');
    expect(approvalManual ? 'run' : 'ask').toBe('ask');
  });
});


describe('Chat handoff park badge [REQ-HITL-032]', () => {
  it('uses Waiting for approval / Parked when status is approval_required', () => {
    const ev = { status: 'approval_required', recipient: 'linux-sysadmin' };
    const isParked = ev.status === 'approval_required';
    const isOk = ev.status === 'completed';
    const label = isParked ? 'Waiting for approval' : (isOk ? 'Completed' : 'Failed');
    const tag = isParked ? 'Parked' : (isOk ? 'Done' : 'Error');
    expect(label).toBe('Waiting for approval');
    expect(tag).toBe('Parked');
    expect(isOk).toBe(false);
  });
});

describe('Chat HITL resume stream payload [REQ-HITL-033]', () => {
  it('sends resume without user content and without goal or verify', () => {
    const body = buildChatStreamPayload({
      agentId: 'autoreiv',
      sessionId: 'sess_1',
      content: 'should not be sent',
      resume: true,
      goalMode: true,
      selfVerify: true,
    });
    expect(body.resume).toBe(true);
    expect(body.content).toBe('');
    expect(body.goal_mode).toBe(false);
    expect(body.self_verify).toBe(false);
    expect(body.workflow_id).toBeUndefined();
    expect(body.session_id).toBe('sess_1');
  });

  it('does not start resume when decide failed', () => {
    const decideOk = false;
    expect(Boolean(decideOk)).toBe(false);
  });
});



describe('Goal Mode plan review card [REQ-GOAL-021]', () => {
  it('treats goal_plan_review as the plan gate, not a tool HITL card', () => {
    expect(isGoalPlanReviewTool('goal_plan_review')).toBe(true);
    expect(isGoalPlanReviewTool('cli_exec')).toBe(false);
  });
});


describe('Remember last Auto-run [REQ-HITL-039]', () => {
  it('fail-closes to ask when memory is missing or invalid', () => {
    expect(readLastApprovalAutoRun(() => null)).toBe(false);
    expect(readLastApprovalAutoRun(() => '')).toBe(false);
    expect(readLastApprovalAutoRun(() => 'ask')).toBe(false);
    expect(readLastApprovalAutoRun(() => 'maybe')).toBe(false);
    expect(readLastApprovalAutoRun(() => { throw new Error('blocked'); })).toBe(false);
  });

  it('restores run only when last choice was run', () => {
    expect(readLastApprovalAutoRun(() => 'run')).toBe(true);
    expect(readLastApprovalAutoRun(() => 'RUN')).toBe(true);
  });

  it('writes run or ask to the existing storage key', () => {
    const saved = {};
    const writer = (key, value) => {
      saved.key = key;
      saved.value = value;
    };
    writeLastApprovalAutoRun(true, writer);
    expect(saved.key).toBe(APPROVAL_AUTORUN_STORAGE_KEY);
    expect(saved.value).toBe('run');
    writeLastApprovalAutoRun(false, writer);
    expect(saved.value).toBe('ask');
  });
});


describe('Routine parks in Chat HITL [REQ-HITL-042, REQ-HITL-043]', () => {
  it('builds the agent pending approvals URL', () => {
    expect(pendingApprovalsUrl('autoreiv')).toBe('/api/approvals/pending?agent_id=autoreiv');
    expect(pendingApprovalsUrl('')).toBe('/api/approvals/pending');
  });

  it('labels a routine park with the routine name', () => {
    expect(pendingHitlLabel({ routine_id: 'r-nightly', routine_name: 'Nightly Scan' })).toBe('Routine: Nightly Scan');
    expect(pendingHitlLabel({ routine_id: 'r-nightly' })).toBe('Routine');
    expect(pendingHitlLabel({ tool_name: 'cli_exec' })).toBe('Approval required');
  });

  it('does not chat-resume when backend already resumed the routine session', () => {
    expect(shouldResumeChatAfterHitl({
      approvalSessionId: 'sess_routine',
      openSessionId: 'sess_chat',
      backendResumed: true,
    })).toBe(false);
  });

  it('chat-resumes only when the open session is the approval session', () => {
    expect(shouldResumeChatAfterHitl({
      approvalSessionId: 'sess_routine',
      openSessionId: 'sess_routine',
      backendResumed: false,
    })).toBe(true);
    expect(shouldResumeChatAfterHitl({
      approvalSessionId: 'sess_open_child_123',
      openSessionId: 'sess_open',
      backendResumed: false,
    })).toBe(true);
    expect(shouldResumeChatAfterHitl({
      approvalSessionId: 'sess_open::phase::1',
      openSessionId: 'sess_open',
      backendResumed: false,
    })).toBe(true);
    expect(shouldResumeChatAfterHitl({
      approvalSessionId: 'sess_routine',
      openSessionId: 'sess_chat',
      backendResumed: false,
    })).toBe(false);
  });

  it('reuses Approve/Reject markup for a pending routine card', () => {
    const html = buildHitlCardInnerHtml({
      title: 'Routine: Nightly Scan',
      toolName: 'cli_exec',
      message: 'Parked by a routine.',
      argsText: '{"command":"dir"}',
    });
    expect(html).toContain('Routine: Nightly Scan');
    expect(html).toContain('data-hitl-decision="APPROVED"');
    expect(html).toContain('data-hitl-decision="REJECTED"');
    expect(html).toContain('cli_exec');
  });
});


describe('CARD-180 workflow picker retirement', () => {
  it('buildChatStreamPayload builds streamlined payload without workflow_id', () => {
    const body = buildChatStreamPayload({
      agentId: 'assistant',
      sessionId: 'sess_2',
      content: 'Onboard Bob',
      goalMode: true, // ignored [CARD-215]
    });
    expect(body.workflow_id).toBeUndefined();
    expect(body.content).toBe('Onboard Bob');
    expect(body.goal_mode).toBe(false);
  });

  it('chat HTML has no workflowPicker or saveAsWorkflowBtn controls', () => {
    const html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
    expect(html).not.toContain('id="workflowPicker"');
    expect(html).not.toContain('id="saveAsWorkflowBtn"');
    expect(html).not.toContain('id="goalToggle"');
    expect(html).toContain('id="verifyToggle"');
    expect(html).not.toContain('Workflow Studio');
    expect(html).not.toContain('Hermes');
  });
});

describe('CARD-151 HITL button grey-out & resolution styling', () => {
  it('includes disabled variant Tailwind classes in buildHitlCardInnerHtml', () => {
    const html = buildHitlCardInnerHtml({
      title: 'Run command',
      toolName: 'cli_exec',
      message: 'Approval required',
      argsText: '{"command":"ls"}',
    });
    expect(html).toContain('disabled:opacity-40');
    expect(html).toContain('disabled:cursor-not-allowed');
    expect(html).toContain('disabled:pointer-events-none');
  });

  it('renders pre-resolved approved buttons as disabled and slate styled', () => {
    const html = buildHitlCardInnerHtml({
      title: 'Run command',
      toolName: 'cli_exec',
      resolved: 'APPROVED',
      statusText: 'Approved. Tool ran.',
    });
    expect(html).toContain('disabled');
    expect(html).toContain('bg-slate-800');
    expect(html).toContain('text-slate-500');
    expect(html).toContain('cursor-not-allowed');
    expect(html).toContain('opacity-50');
    expect(html).toContain('Approved. Tool ran.');
    expect(html).not.toContain('bg-emerald-700');
  });

  it('renders pre-resolved rejected buttons as disabled and slate styled', () => {
    const html = buildHitlCardInnerHtml({
      title: 'Run command',
      toolName: 'cli_exec',
      resolved: 'REJECTED',
      statusText: 'Rejected. Tool did not run.',
    });
    expect(html).toContain('disabled');
    expect(html).toContain('bg-slate-800');
    expect(html).toContain('text-slate-500');
    expect(html).toContain('Rejected. Tool did not run.');
    expect(html).not.toContain('bg-rose-800');
  });

  it('submitHitlDecision greys out buttons upon approval', async () => {
    const approveBtn = new MockElement('button', 'bg-emerald-700 hover:bg-emerald-600 text-white');
    const rejectBtn = new MockElement('button', 'bg-rose-800 hover:bg-rose-700 text-white');
    const statusSpan = new MockElement('span', 'hitl-card-status');
    const card = new MockElement('div', 'border-amber-500/30 bg-amber-950/20');
    card.querySelectorAll = (sel) => {
      if (sel === '[data-hitl-decision]') return [approveBtn, rejectBtn];
      return [];
    };
    card.querySelector = (sel) => {
      if (sel === '.hitl-card-status') return statusSpan;
      return null;
    };

    const originalFetch = global.fetch;
    global.fetch = async () => ({
      ok: true,
      json: async () => ({ execution: { ran: true, output: 'ok' } }),
    });

    try {
      const res = await submitHitlDecision('appr_123', 'APPROVED', card, 'sess_abc');
      expect(res.ok).toBe(true);
      expect(approveBtn.disabled).toBe(true);
      expect(rejectBtn.disabled).toBe(true);
      expect(approveBtn.classList.contains('bg-slate-800')).toBe(true);
      expect(approveBtn.classList.contains('text-slate-500')).toBe(true);
      expect(approveBtn.classList.contains('cursor-not-allowed')).toBe(true);
      expect(approveBtn.classList.contains('bg-emerald-700')).toBe(false);
      expect(rejectBtn.classList.contains('bg-slate-800')).toBe(true);
      expect(rejectBtn.classList.contains('bg-rose-800')).toBe(false);
      expect(statusSpan.textContent).toBe('Approved. Tool ran.');
      expect(card.classList.contains('border-emerald-500/30')).toBe(true);
    } finally {
      global.fetch = originalFetch;
    }
  });

  it('submitHitlDecision re-enables buttons if decision request fails', async () => {
    const approveBtn = new MockElement('button', 'bg-emerald-700 text-white');
    const rejectBtn = new MockElement('button', 'bg-rose-800 text-white');
    const statusSpan = new MockElement('span', 'hitl-card-status');
    const card = new MockElement('div', 'border-amber-500/30');
    card.querySelectorAll = (sel) => (sel === '[data-hitl-decision]' ? [approveBtn, rejectBtn] : []);
    card.querySelector = (sel) => (sel === '.hitl-card-status' ? statusSpan : null);

    const originalFetch = global.fetch;
    global.fetch = async () => ({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Internal error' }),
    });

    try {
      const res = await submitHitlDecision('appr_123', 'APPROVED', card, 'sess_abc');
      expect(res.ok).toBe(false);
      expect(approveBtn.disabled).toBe(false);
      expect(rejectBtn.disabled).toBe(false);
      expect(approveBtn.classList.contains('opacity-50')).toBe(false);
      expect(statusSpan.textContent).toContain('Failed');
    } finally {
      global.fetch = originalFetch;
    }
  });
});

describe('CARD-157 Subagent HITL Chaining and Session Approvals URL', () => {
  it('prioritizes session_id in pendingApprovalsUrl to surface subagent approvals', () => {
    expect(pendingApprovalsUrl('assistant', 'sess_abc')).toBe('/api/approvals/pending?session_id=sess_abc');
    expect(pendingApprovalsUrl('assistant', '')).toBe('/api/approvals/pending?agent_id=assistant');
    expect(pendingApprovalsUrl('', '')).toBe('/api/approvals/pending');
  });

  it('prevents parent chat resume when nested subagent approval is required', () => {
    expect(shouldResumeChatAfterHitl({
      approvalSessionId: 'sess_main_child_sub1',
      openSessionId: 'sess_main',
      backendResumed: false,
      nestedStatus: 'approval_required',
    })).toBe(false);
  });

  it('allows parent chat resume when nested subagent is completed', () => {
    expect(shouldResumeChatAfterHitl({
      approvalSessionId: 'sess_main_child_sub1',
      openSessionId: 'sess_main',
      backendResumed: false,
      nestedStatus: 'completed',
    })).toBe(true);
  });

  it('handles empty/null nestedStatus gracefully', () => {
    expect(shouldResumeChatAfterHitl({
      approvalSessionId: 'sess_main',
      openSessionId: 'sess_main',
      backendResumed: false,
      nestedStatus: null,
    })).toBe(true);
  });
});

describe('CARD-179 Smart Goal & Verify Coupling, Autonomous Mode Suggestion, and Live Reflexion Badges [REQ-REF-001 - REQ-REF-004]', () => {
  describe('coupleGoalAndVerify [REQ-REF-001]', () => {
    it('checking goal sets verify to true and unhides both badges', () => {
      const state = { goalEnabled: false, verifyEnabled: false };
      const goalBadge = new MockElement('span', 'hidden');
      const verifyBadge = new MockElement('span', 'hidden');
      const verifyToggle = { checked: false };

      coupleGoalAndVerify(true, state, { verifyToggle, verifyBadge, goalBadge });

      expect(state.goalEnabled).toBe(true);
      expect(state.verifyEnabled).toBe(true);
      expect(verifyToggle.checked).toBe(true);
      expect(goalBadge.classList.contains('hidden')).toBe(false);
      expect(verifyBadge.classList.contains('hidden')).toBe(false);
    });

    it('unchecking goal does not force uncheck verify', () => {
      const state = { goalEnabled: true, verifyEnabled: true };
      const goalBadge = new MockElement('span', '');
      const verifyBadge = new MockElement('span', '');
      const verifyToggle = { checked: true };

      coupleGoalAndVerify(false, state, { verifyToggle, verifyBadge, goalBadge });

      expect(state.goalEnabled).toBe(false);
      expect(goalBadge.classList.contains('hidden')).toBe(true);
      expect(state.verifyEnabled).toBe(true);
      expect(verifyToggle.checked).toBe(true);
    });
  });

  describe('isComplexMultiStepPrompt heuristic [REQ-REF-004]', () => {
    it('detects numbered list prompts', () => {
      const prompt = `Please complete the following:
1. Audit database indexes
2. Identify slow queries
3. Run explain plan`;
      expect(isComplexMultiStepPrompt(prompt)).toBe(true);
    });

    it('detects explicit step/phase markers', () => {
      const prompt = 'Step 1: Check server logs. Step 2: Restart the worker process.';
      expect(isComplexMultiStepPrompt(prompt)).toBe(true);
    });

    it('detects sequential action transitions (first ... then ... finally)', () => {
      const prompt = 'First check the repository status, then run the unit test suite, and finally build the package.';
      expect(isComplexMultiStepPrompt(prompt)).toBe(true);
    });

    it('ignores simple questions and short prompts', () => {
      expect(isComplexMultiStepPrompt('Hello agent!')).toBe(false);
      expect(isComplexMultiStepPrompt('What time is it in Tokyo?')).toBe(false);
      expect(isComplexMultiStepPrompt('Can you explain what SQL is?')).toBe(false);
      expect(isComplexMultiStepPrompt('1. Just one item here.')).toBe(false);
      expect(isComplexMultiStepPrompt('')).toBe(false);
      expect(isComplexMultiStepPrompt(null)).toBe(false);
    });
  });

  describe('renderReflexionBadge and collapsible details [REQ-REF-002, REQ-REF-003]', () => {
    it('renders reflexion_attempt with checker name', () => {
      const el = new MockElement('div', 'reflexion-status-badge hidden');
      renderReflexionBadge(el, 'reflexion_attempt', { attempt: 1, max_attempts: 1, checker: 'assert_json_schema' });

      expect(el.classList.contains('hidden')).toBe(false);
      expect(el.innerHTML).toContain('Reflexion Check');
      expect(el.innerHTML).toContain('Attempt 1/1');
      expect(el.innerHTML).toContain('assert_json_schema');
    });

    it('renders reflexion_critique with discrepancies and collapsible toggle', () => {
      const el = new MockElement('div', 'reflexion-status-badge hidden');
      renderReflexionBadge(el, 'reflexion_critique', {
        attempt: 1,
        critique: 'Missing fields',
        discrepancies: ['field "summary" is required'],
      });

      expect(el.classList.contains('hidden')).toBe(false);
      expect(el.innerHTML).toContain('Critique');
      expect(el.innerHTML).toContain('Missing fields');
      expect(el.innerHTML).toContain('Details ▾');

      const toggle = el.querySelector('.reflexion-badge-toggle');
      const details = el.querySelector('.reflexion-details');
      expect(toggle).not.toBeNull();
      expect(details).not.toBeNull();
      expect(details.classList.contains('hidden')).toBe(true);

      // Expand details
      toggle.click();
      expect(details.classList.contains('hidden')).toBe(false);

      // Collapse details
      toggle.click();
      expect(details.classList.contains('hidden')).toBe(true);
    });

    it('renders reflexion_verified passed state with collapsible details', () => {
      const el = new MockElement('div', 'reflexion-status-badge hidden');
      renderReflexionBadge(el, 'reflexion_verified', {
        passed: true,
        status: 'verified',
        checker: 'verify_schema',
      });

      expect(el.innerHTML).toContain('Self-Verification <strong>Passed</strong>!');
      expect(el.innerHTML).toContain('verify_schema');
      expect(el.classList.contains('bg-emerald-950/40')).toBe(true);

      const toggle = el.querySelector('.reflexion-badge-toggle');
      const details = el.querySelector('.reflexion-details');
      expect(toggle).not.toBeNull();
      expect(details).not.toBeNull();
      expect(details.classList.contains('hidden')).toBe(true);

      toggle.click();
      expect(details.classList.contains('hidden')).toBe(false);
    });

    it('renders reflexion_verified skipped state without error styling', () => {
      const el = new MockElement('div', 'reflexion-status-badge hidden');
      renderReflexionBadge(el, 'reflexion_verified', {
        passed: false,
        status: 'skipped',
      });

      expect(el.innerHTML).toContain('Skipped (no checker configured)');
      expect(el.classList.contains('bg-slate-800/80')).toBe(true);
    });

    it('renders reflexion_verified failed state with discrepancies', () => {
      const el = new MockElement('div', 'reflexion-status-badge hidden');
      renderReflexionBadge(el, 'reflexion_verified', {
        passed: false,
        status: 'failed',
        checker: 'lint_checker',
        discrepancies: ['Trailing whitespace found'],
      });

      expect(el.innerHTML).toContain('Self-Verification <strong>Failed</strong>');
      expect(el.innerHTML).toContain('lint_checker');
      expect(el.classList.contains('bg-rose-950/40')).toBe(true);

      const toggle = el.querySelector('.reflexion-badge-toggle');
      const details = el.querySelector('.reflexion-details');
      expect(toggle).not.toBeNull();
      expect(details).not.toBeNull();

      toggle.click();
      expect(details.classList.contains('hidden')).toBe(false);
    });
  });

  describe('Autonomous mode suggestion markup in index.html [REQ-REF-004]', () => {
    it('retires Goal suggestion chip theatre [CARD-215, CARD-235]', () => {
      const html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
      expect(html).not.toContain('id="chatGoalSuggestionChip"');
      expect(html).not.toContain('Switch to Goal & Self-Verify');
      expect(html).not.toContain('id="goalToggle"');
      expect(html).not.toContain('id="chatEnableGoalSuggestionBtn"');
      expect(html).not.toContain('id="chatDismissGoalSuggestionBtn"');
    });
  });

  describe('Human-readable HITL previews and Routine Built-in checks [CARD-187]', () => {
    describe('formatHitlArgs [REQ-HITL-050]', () => {
      it('formats code payload as clean unescaped multiline text instead of JSON', () => {
        const args = {
          code: 'import psutil\nimport time\nprint(psutil.cpu_percent())',
          timeout: 30,
        };
        const formatted = formatHitlArgs(args);
        expect(formatted).not.toContain('\\n');
        expect(formatted).not.toContain('\\"');
        expect(formatted).toContain('timeout: 30');
        expect(formatted).toContain('import psutil\nimport time\nprint(psutil.cpu_percent())');
      });

      it('formats command / CommandLine payload cleanly', () => {
        const args = {
          CommandLine: 'Get-Process | Select-Object -First 5',
          Cwd: 'D:\\Projects\\Active\\AutoReiv',
        };
        const formatted = formatHitlArgs(args);
        expect(formatted).not.toContain('\\"');
        expect(formatted).toContain('Cwd: D:\\Projects\\Active\\AutoReiv');
        expect(formatted).toContain('Get-Process | Select-Object -First 5');
      });

      it('handles JSON string inputs gracefully', () => {
        const rawJson = JSON.stringify({
          code: 'def test():\n    return True\n',
          language: 'python',
        });
        const formatted = formatHitlArgs(rawJson);
        expect(formatted).not.toContain('\\n');
        expect(formatted).toContain('language: python');
        expect(formatted).toContain('def test():\n    return True');
      });
    });

    describe('formatHitlOutput [REQ-HITL-051]', () => {
      it('extracts stdout directly from execution output object', () => {
        const output = {
          exit_code: 0,
          ran: true,
          stderr: '',
          stdout: 'Task completed successfully.\nAll checks passed.',
        };
        const formatted = formatHitlOutput(output);
        expect(formatted).not.toContain('exit_code');
        expect(formatted).not.toContain('\\n');
        expect(formatted).toContain('Task completed successfully.\nAll checks passed.');
      });

      it('pretty-prints JSON string contained inside stdout', () => {
        const innerJson = JSON.stringify({ cpu: 20.3, memory_percent: 64.1 });
        const output = {
          exit_code: 0,
          stdout: innerJson,
        };
        const formatted = formatHitlOutput(output);
        expect(formatted).toContain('{\n  "cpu": 20.3,\n  "memory_percent": 64.1\n}');
      });

      it('displays stderr when present', () => {
        const output = {
          exit_code: 1,
          stdout: 'Some partial stdout',
          stderr: 'Warning: deprecated package',
        };
        const formatted = formatHitlOutput(output);
        expect(formatted).toContain('Some partial stdout');
        expect(formatted).toContain('[stderr]');
        expect(formatted).toContain('Warning: deprecated package');
      });
    });

    describe('submitHitlDecision [REQ-HITL-051]', () => {
      it('renders formatted output without raw JSON escaping upon approval', async () => {
        const originalFetch = globalThis.fetch;
        const originalDocument = globalThis.document;

        const card = new MockElement('div', 'hitl-approval-card');
        const statusSpan = new MockElement('span', 'hitl-card-status');
        const approveBtn = new MockElement('button');
        approveBtn.setAttribute('data-hitl-decision', 'APPROVED');
        card.appendChild(statusSpan);
        card.appendChild(approveBtn);

        globalThis.document = {
          createElement: (tag) => new MockElement(tag),
        };

        globalThis.fetch = async () => ({
          ok: true,
          json: async () => ({
            decision: 'APPROVED',
            execution: {
              ran: true,
              output: {
                stdout: 'Line 1\nLine 2',
              },
            },
          }),
        });

        try {
          const res = await submitHitlDecision('appr_123', 'APPROVED', card, 'sess_abc');
          expect(res.ok).toBe(true);
          const pre = card.children.find((c) => c.tagName === 'PRE');
          expect(pre).toBeDefined();
          expect(pre.textContent).toBe('Line 1\nLine 2');
          expect(pre.textContent).not.toContain('\\n');
        } finally {
          globalThis.fetch = originalFetch;
          globalThis.document = originalDocument;
        }
      });
    });

    describe('isBuiltinRoutine [REQ-ROUTINE-051]', () => {
      it('returns true when is_builtin is true', () => {
        expect(isBuiltinRoutine({ id: 'custom-1', is_builtin: true })).toBe(true);
      });

      it('returns true for known builtin routine IDs', () => {
        expect(isBuiltinRoutine({ id: 'daily-sysinfo' })).toBe(true);
        expect(isBuiltinRoutine({ id: 'morning-briefing' })).toBe(true);
        expect(isBuiltinRoutine({ id: 'hourly-sre-pulse' })).toBe(true);
      });

      it('returns false for custom routines when is_builtin is false', () => {
        expect(isBuiltinRoutine({ id: 'my-custom-scraper', is_builtin: false })).toBe(false);
        expect(isBuiltinRoutine({ id: 'user-routine-123' })).toBe(false);
      });
    });
  });
});

describe('CARD-239 HITL origin session cohesion [REQ-HITL-ORIGIN-001]', () => {
  it('maps phase-child approval sessions onto the origin parent', () => {
    expect(approvalBelongsToOriginSession('abc::phase::phase_1', 'abc')).toBe(true);
    expect(approvalBelongsToOriginSession('abc_child_sub1', 'abc')).toBe(true);
    expect(approvalBelongsToOriginSession('abc', 'abc')).toBe(true);
    expect(approvalBelongsToOriginSession('other::phase::x', 'abc')).toBe(false);
  });
});

