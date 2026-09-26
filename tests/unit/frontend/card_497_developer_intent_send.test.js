/**
 * CARD-497 REQ-497-016: Ask Developer is a real send.
 * The gap Ask Developer, Tools Studio Talk and Teach "Ask Developer to build this tool" all go through
 * chat.openDeveloperSession. It must start one Developer turn right away (as if typed + Enter),
 * never twice, not while the chat is busy, and not again when the session is reopened.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');
const read = (rel) => fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
const MOD = '../../../src/web/static/modules/studios/chat/developer_intent.js';

const PROMPT = 'Tools Studio tool intent (create)\n\nTool name: get_tc49_tool\nBehavior: Look up TC49 things';

async function load() {
  vi.resetModules();
  return import(MOD);
}

describe('REQ-497-016: sendDeveloperIntent starts a real Developer turn', () => {
  let mod;
  beforeEach(async () => { mod = await load(); });

  it('sends the intent once, as a real turn, when the chat is idle and the prompt is not in history', async () => {
    const send = vi.fn(async () => {});
    const fillComposer = vi.fn();
    const toast = vi.fn();
    const state = { messages: [], isStreaming: false, sessionBusy: false };
    const out = mod.sendDeveloperIntent({ sessionId: 'dev1', prompt: PROMPT, state, send, fillComposer, toast });
    expect(out.status).toBe('sent');
    expect(send).toHaveBeenCalledTimes(1);
    expect(send).toHaveBeenCalledWith(PROMPT);
    expect(fillComposer).not.toHaveBeenCalled();
    await out.done;
  });

  it('does not send a second time while the first send is still in flight (double click)', async () => {
    let finish;
    const send = vi.fn(() => new Promise((r) => { finish = r; }));
    const state = { messages: [], isStreaming: false, sessionBusy: false };
    const a = mod.sendDeveloperIntent({ sessionId: 'dev1', prompt: PROMPT, state, send, fillComposer: vi.fn() });
    const b = mod.sendDeveloperIntent({ sessionId: 'dev1', prompt: PROMPT, state, send, fillComposer: vi.fn() });
    expect(a.status).toBe('sent');
    expect(b.status).toBe('already-sent');
    expect(send).toHaveBeenCalledTimes(1);
    finish();
    await a.done;
  });

  it('does not resend when the session is reopened and the prompt is already in history (or on another device)', () => {
    const send = vi.fn();
    const state = { messages: [{ role: 'user', content: PROMPT }], isStreaming: false, sessionBusy: false };
    const out = mod.sendDeveloperIntent({ sessionId: 'dev1', prompt: PROMPT, state, send, fillComposer: vi.fn() });
    expect(out.status).toBe('already-sent');
    expect(send).not.toHaveBeenCalled();
  });

  it('when the chat is busy it puts the intent in the composer and says so, without sending', () => {
    for (const busy of [{ isStreaming: true, sessionBusy: false }, { isStreaming: false, sessionBusy: true }]) {
      const send = vi.fn();
      const fillComposer = vi.fn();
      const toast = vi.fn();
      const state = { messages: [], ...busy };
      const out = mod.sendDeveloperIntent({ sessionId: 'dev2', prompt: PROMPT, state, send, fillComposer, toast });
      expect(out.status).toBe('busy');
      expect(send).not.toHaveBeenCalled();
      expect(fillComposer).toHaveBeenCalledWith(PROMPT);
      expect(toast).toHaveBeenCalledTimes(1);
    }
  });

  it('an empty prompt or session id does nothing', () => {
    const send = vi.fn();
    const state = { messages: [], isStreaming: false, sessionBusy: false };
    expect(mod.sendDeveloperIntent({ sessionId: '', prompt: PROMPT, state, send }).status).toBe('none');
    expect(mod.sendDeveloperIntent({ sessionId: 'dev3', prompt: '  ', state, send }).status).toBe('none');
    expect(send).not.toHaveBeenCalled();
  });
});

describe('REQ-497-016: every Ask Developer entry point shares the real send', () => {
  const chat = read('src/web/static/modules/studios/chat.js');
  const body = chat.slice(chat.indexOf('async function openDeveloperSession'), chat.indexOf('async function resumeParkedJob'));

  it('openDeveloperSession sends through executeChatTurn via sendDeveloperIntent, not by prefilling the composer', () => {
    expect(chat).toMatch(/import\s*\{[^}]*sendDeveloperIntent[^}]*\}\s*from\s*'\.\/chat\/developer_intent\.js'/);
    expect(body).toContain('sendDeveloperIntent(');
    expect(body).toContain('executeChatTurn(');
    expect(body).not.toMatch(/if\s*\(\s*!visible\s*&&\s*composerText\s*\)/);
  });

  it('gap Ask Developer, Tools Studio Talk and Teach Ask Developer all call openDeveloperSession', () => {
    // CARD-520 REQ-520-011: gap and Teach go through the shared askDeveloperWithDraft helper.
    expect(read('src/web/static/modules/studios/forge/tools.js')).toContain('askDeveloperWithDraft(');
    expect(read('src/web/static/modules/studios/tools_studio.js')).toContain('chat.openDeveloperSession(plan.sessionId, plan.prompt)');
    expect(read('src/web/static/modules/studios/chat/teach_modal.js')).toMatch(/askDeveloperWithDraft\(draft, \{[^}]*openDeveloperSessionFn/);
    const auth = read('src/web/static/modules/studios/tools_studio_authoring.js');
    expect(auth).toContain('chat.openDeveloperSession(');
    expect(auth).toContain('await open(plan.sessionId, plan.prompt)');
    expect(chat).toMatch(/openDeveloperSessionFn:\s*openDeveloperSession/);
  });
});
