/** CARD-630: formatHitlArgs hides _tool_call_id and other _ keys. */
import { describe, it, expect } from 'vitest';
import { formatHitlArgs } from '../../../src/web/static/modules/studios/chat/hitl.js';

describe('CARD-630 formatHitlArgs hides internal keys', () => {
  it('drops _tool_call_id from an object and keeps other keys', () => {
    const text = formatHitlArgs({ text: 'buy milk', _tool_call_id: 'chatcmpl-tool-abc' });
    expect(text).toContain('buy milk');
    expect(text).not.toContain('_tool_call_id');
    expect(text).not.toContain('chatcmpl-tool-abc');
  });

  it('drops _tool_call_id from a JSON string', () => {
    const text = formatHitlArgs(JSON.stringify({ text: 'buy milk', _tool_call_id: 'x' }));
    expect(text).toContain('buy milk');
    expect(text).not.toContain('_tool_call_id');
  });

  it('keeps a primary code/command layout without leaking _ keys', () => {
    const text = formatHitlArgs({ code: 'print(1)', _tool_call_id: 'hideme', note: 'n' });
    expect(text).toContain('print(1)');
    expect(text).toContain('note:');
    expect(text).not.toContain('_tool_call_id');
    expect(text).not.toContain('hideme');
  });

  it('arguments that are only _tool_call_id give an empty box', () => {
    expect(formatHitlArgs({ _tool_call_id: 'only' }).trim()).toBe('');
  });

  it('negative: a user key tool_call_id without leading underscore is still shown', () => {
    const text = formatHitlArgs({ tool_call_id: 'user-visible', text: 'hi' });
    expect(text).toContain('tool_call_id');
    expect(text).toContain('user-visible');
  });
});
