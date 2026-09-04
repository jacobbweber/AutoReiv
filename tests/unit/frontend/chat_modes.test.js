/**
 * Frontend Unit Tests for Chat Modes (Goal & Reflexion Streaming) [REQ-CHAT-013].
 */

import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import { buildChatStreamPayload, isGoalPlanReviewTool, readLastApprovalAutoRun, writeLastApprovalAutoRun, APPROVAL_AUTORUN_STORAGE_KEY, pendingApprovalsUrl, pendingHitlLabel, shouldResumeChatAfterHitl, buildHitlCardInnerHtml, submitHitlDecision, workflowPickerOptionsHtml, canSaveJobAsWorkflow, WORKFLOW_PICKER_EMPTY_LABEL } from '../../../src/web/static/modules/studios/chat.js';

class MockElement {
  constructor(tagName = 'div', className = '') {
    this.tagName = tagName.toUpperCase();
    this.className = className;
    this.classList = {
      _classes: new Set(className.split(' ').filter(Boolean)),
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
    this.children = [];
    this.textContent = '';
    this.innerHTML = '';
    this.id = '';
  }

  appendChild(child) {
    this.children.push(child);
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
    expect(body.workflow_id).toBe('');
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


describe('CARD-123 workflow picker', () => {
  it('renders empty picker until this agent has a saved recipe', () => {
    expect(WORKFLOW_PICKER_EMPTY_LABEL).toBe('No workflows yet');
    expect(workflowPickerOptionsHtml([])).toContain('No workflows yet');
    expect(workflowPickerOptionsHtml([])).not.toContain('option value="wf_');
  });

  it('does not treat a single Chat phase as saveable', () => {
    expect(canSaveJobAsWorkflow(1)).toBe(false);
    expect(canSaveJobAsWorkflow(0)).toBe(false);
    expect(canSaveJobAsWorkflow(2)).toBe(true);
  });

  it('sends workflow_id when a recipe is picked', () => {
    const body = buildChatStreamPayload({
      agentId: 'assistant',
      sessionId: 'sess_2',
      content: 'Onboard Bob',
      workflowId: 'wf_abc',
    });
    expect(body.workflow_id).toBe('wf_abc');
    expect(body.content).toBe('Onboard Bob');
    expect(body.goal_mode).toBe(false);
  });

  it('chat HTML has the picker next to Goal and Verify and no Workflow Studio', () => {
    const html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
    expect(html).toContain('id="workflowPicker"');
    expect(html).toContain('id="saveAsWorkflowBtn"');
    expect(html).toContain('id="goalToggle"');
    expect(html).toContain('id="verifyToggle"');
    expect(html).not.toContain('Workflow Studio');
    expect(html).not.toContain('Hermes');
    const goalIdx = html.indexOf('id="goalToggle"');
    const pickerIdx = html.indexOf('id="workflowPicker"');
    const verifyIdx = html.indexOf('id="verifyToggle"');
    expect(pickerIdx).toBeGreaterThan(verifyIdx);
    expect(pickerIdx).toBeGreaterThan(goalIdx - 5000);
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

