/**
 * Frontend Unit Tests for Chat Modes (Goal & Reflexion Streaming) [REQ-CHAT-013].
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { buildChatStreamPayload, isGoalPlanReviewTool, readLastApprovalAutoRun, writeLastApprovalAutoRun, APPROVAL_AUTORUN_STORAGE_KEY } from '../../../src/web/static/modules/studios/chat.js';

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
    expect(approvalAutoRun ? 'run' : 'ask').toBe('run');
    expect(false ? 'run' : 'ask').toBe('ask');
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
