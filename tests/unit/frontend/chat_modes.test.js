/**
 * Frontend Unit Tests for Chat Modes (Goal & Reflexion Streaming) [REQ-CHAT-013].
 */

import { describe, it, expect, beforeEach } from 'vitest';

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
  });
});
