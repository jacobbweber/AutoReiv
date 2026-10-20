import { describe, it, expect } from 'vitest';
import { renderReflexionBadge } from '../../../src/web/static/modules/studios/chat/job_chrome.js';

function createMockBadge() {
  const classes = new Set([
    'reflexion-status-badge',
    'hidden',
    'p-2',
    'rounded-lg',
    'bg-amber-950/40',
    'border',
    'border-amber-500/30',
    'text-xs',
    'text-amber-300',
    'items-center',
    'space-x-2',
  ]);
  return {
    innerHTML: '',
    get className() {
      return Array.from(classes).join(' ');
    },
    set className(val) {
      classes.clear();
      String(val || '')
        .split(/\s+/)
        .filter(Boolean)
        .forEach((c) => classes.add(c));
    },
    classList: {
      add: (...tokens) => tokens.forEach((t) => classes.add(t)),
      remove: (...tokens) => tokens.forEach((t) => classes.delete(t)),
      contains: (t) => classes.has(t),
      toggle: (t) => {
        if (classes.has(t)) {
          classes.delete(t);
          return false;
        }
        classes.add(t);
        return true;
      },
    },
    querySelector: () => null,
  };
}

describe('CARD-734 renderReflexionBadge keeps badge hidden on non-reflexion events', () => {
  it('stays hidden and empty when non-reflexion SSE events stream through', () => {
    const badge = createMockBadge();

    renderReflexionBadge(badge, 'session', { session_id: 'sess-1' });
    renderReflexionBadge(badge, 'tool_start', { tool: 'web_search', id: 'tc-1' });
    renderReflexionBadge(badge, 'tool_end', { tool: 'web_search', id: 'tc-1' });
    renderReflexionBadge(badge, 'turn_end', { status: 'completed' });

    expect(badge.classList.contains('hidden')).toBe(true);
    expect(badge.classList.contains('flex')).toBe(false);
    expect(badge.innerHTML).toBe('');
  });

  it('unhides and renders content when a reflexion event arrives', () => {
    const badge = createMockBadge();

    renderReflexionBadge(badge, 'reflexion_attempt', {
      attempt: 1,
      max_attempts: 2,
      checker: 'verify_output',
    });

    expect(badge.classList.contains('hidden')).toBe(false);
    expect(badge.classList.contains('flex')).toBe(true);
    expect(badge.innerHTML).toContain('Reflexion Check');
    expect(badge.innerHTML).toContain('Attempt 1/2');
  });
});
