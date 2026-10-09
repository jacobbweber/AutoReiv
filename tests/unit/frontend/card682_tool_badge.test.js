/**
 * CARD-682: the chat tool badge shows why a tool call was refused, and reacts to the events the server sends.
 */
import { describe, it, expect } from 'vitest';
import { toolBadgeView } from '../../../src/web/static/modules/studios/chat/stream.js';

describe('toolBadgeView [CARD-682]', () => {
  it('shows a running tool for tool_start', () => {
    expect(toolBadgeView('tool_start', { tool_name: 'wiki_note_read' })).toEqual({ state: 'running', name: 'wiki_note_read', reason: '' });
  });

  it('shows a refused call with its reason', () => {
    const v = toolBadgeView('tool_output', {
      tool_name: 'wiki_template_search',
      success: false,
      error: "tool_not_offered:Tool 'wiki_template_search' was not in the tools sent on this call. Did you mean wiki_template_list?",
      result: 'Tool Error: ...',
    });
    expect(v.state).toBe('refused');
    expect(v.name).toBe('wiki_template_search');
    expect(v.reason).toContain('Did you mean wiki_template_list?');
    expect(v.reason.startsWith('tool_not_offered:')).toBe(false);
  });

  it('shows a finished call for a successful tool_output', () => {
    expect(toolBadgeView('tool_output', { tool_name: 'wiki_template_list', success: true, result: [] })).toEqual({
      state: 'done', name: 'wiki_template_list', reason: '',
    });
  });

  it('keeps the older event names working and ignores others', () => {
    expect(toolBadgeView('tool_execution_start', { tool_name: 't' }).state).toBe('running');
    expect(toolBadgeView('tool_execution_complete', { tool_name: 't' }).state).toBe('done');
    expect(toolBadgeView('token', {})).toBeNull();
  });
});
