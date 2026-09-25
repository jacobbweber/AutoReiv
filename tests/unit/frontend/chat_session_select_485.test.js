import { describe, it, expect, vi, afterEach } from 'vitest';

/**
 * CARD-485 - picking a chat moves the highlight, closes the drawer on a user pick, restores the
 * job strip from the journey, and shows a busy state (2 s re-check) while its reply is still
 * running elsewhere. D1-D5 accepted as recommended.
 */

async function mod() {
  try {
    return await import('../../../src/web/static/modules/studios/chat/session_select.js');
  } catch {
    return {};
  }
}

async function need(name) {
  const m = await mod();
  expect(typeof m[name], `session_select.js must export ${name}`).toBe('function');
  return m[name];
}

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms));
const json = (body, ok = true) => ({ ok, status: ok ? 200 : 500, json: async () => body });

const JOURNEY = {
  jobs: [
    { id: 'job-old', status: 'done', phases: [{ id: 'x', name: 'Old', index: 0, status: 'done' }] },
    {
      id: 'job-485',
      status: 'waiting_approval',
      phases: [
        { id: 'p2', name: 'Build', index: 1, status: 'waiting_approval', assigned_agent_id: 'developer' },
        { id: 'p1', name: 'Plan', index: 0, status: 'done', assigned_agent_id: 'autoreiv' },
      ],
    },
  ],
};

function fakeClassList(initial = []) {
  const set = new Set(initial);
  return {
    add: (c) => set.add(c),
    remove: (c) => set.delete(c),
    contains: (c) => set.has(c),
    toggle: (c, on) => { if (on === undefined ? !set.has(c) : on) set.add(c); else set.delete(c); },
  };
}

function baseDeps(state, extra = {}) {
  return {
    loadMessages: vi.fn(async () => {}),
    refreshPendingHitl: vi.fn(async () => {}),
    refreshWorkbenchArtifactCount: vi.fn(async () => {}),
    setJobPhaseState: vi.fn(),
    setInlineJobChromeModel: vi.fn(),
    jumpToLatest: vi.fn(),
    fetchFn: vi.fn(async () => json({ jobs: [] })),
    queryStatusFn: vi.fn(async (id) => ({ session_id: id, is_running: false })),
    getEl: () => null,
    ...extra,
  };
}

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('CARD-485 job strip from the journey', () => {
  it('1. a job waiting for approval restores the strip and the inline phases (REQ-485-003)', async () => {
    const hydrate = await need('hydrateJobChromeFromSession');
    const state = { activeSessionId: 's1' };
    const setJobPhaseState = vi.fn();
    const setInlineJobChromeModel = vi.fn();
    const fetchFn = vi.fn(async () => json(JOURNEY));
    expect(await hydrate(state, 's1', { fetchFn, setJobPhaseState, setInlineJobChromeModel })).toBe(true);
    expect(fetchFn).toHaveBeenCalledWith('/api/chat/sessions/s1/journey');
    expect(setJobPhaseState.mock.calls[0][0]).toMatchObject({ jobId: 'job-485', reactState: 'PARKED' });
    expect(setInlineJobChromeModel.mock.calls[0][0].phaseOrder).toEqual(['Plan', 'Build']);
  });

  it('2. no job keeps the strip hidden, and a journey error soft-fails (REQ-485-004)', async () => {
    const hydrate = await need('hydrateJobChromeFromSession');
    const state = { activeSessionId: 's1' };
    const setJobPhaseState = vi.fn();
    expect(await hydrate(state, 's1', { fetchFn: async () => json({ jobs: [] }), setJobPhaseState })).toBe(false);
    expect(await hydrate(state, 's1', { fetchFn: async () => { throw new Error('down'); }, setJobPhaseState })).toBe(false);
    expect(await hydrate(state, 's1', { fetchFn: async () => json({}, false), setJobPhaseState })).toBe(false);
    expect(setJobPhaseState).not.toHaveBeenCalled();
  });

  it('3. a late journey for a chat that is no longer open is ignored (REQ-485-007)', async () => {
    const hydrate = await need('hydrateJobChromeFromSession');
    const state = { activeSessionId: 's1' };
    const setJobPhaseState = vi.fn();
    const fetchFn = async () => { await tick(20); return json(JOURNEY); };
    const p = hydrate(state, 's1', { fetchFn, setJobPhaseState, setInlineJobChromeModel: vi.fn() });
    state.activeSessionId = 's2';
    expect(await p).toBe(false);
    expect(setJobPhaseState).not.toHaveBeenCalled();
  });
});

describe('CARD-485 running reply status', () => {
  it('4. a running chat shows busy and re-checks every 2 s (REQ-485-005)', async () => {
    vi.useFakeTimers();
    const create = await need('createSessionStatusWatcher');
    const state = { activeSessionId: 'a' };
    const setBusy = vi.fn();
    const queryStatusFn = vi.fn(async () => ({ is_running: true }));
    const w = create(state, { queryStatusFn, setBusy, onFinished: vi.fn(), isPageVisible: () => true });
    await w.watch('a');
    expect(setBusy).toHaveBeenCalledWith(true);
    expect(queryStatusFn).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(2000);
    expect(queryStatusFn).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(2000);
    expect(queryStatusFn).toHaveBeenCalledTimes(3);
    w.stop();
  });

  it('5. when it finishes: Send returns, the reply reloads, and polling stops (REQ-485-006)', async () => {
    vi.useFakeTimers();
    const create = await need('createSessionStatusWatcher');
    const state = { activeSessionId: 'a' };
    const setBusy = vi.fn();
    const onFinished = vi.fn(async () => {});
    let running = true;
    const queryStatusFn = vi.fn(async () => ({ is_running: running }));
    const w = create(state, { queryStatusFn, setBusy, onFinished, isPageVisible: () => true });
    await w.watch('a');
    running = false;
    await vi.advanceTimersByTimeAsync(2000);
    expect(setBusy).toHaveBeenLastCalledWith(false);
    expect(onFinished).toHaveBeenCalledWith('a');
    const calls = queryStatusFn.mock.calls.length;
    await vi.advanceTimersByTimeAsync(6000);
    expect(queryStatusFn.mock.calls.length).toBe(calls);
  });

  it('6. switching chats stops the old poll; one check in flight; hidden page skips checks (REQ-485-007, D3)', async () => {
    vi.useFakeTimers();
    const create = await need('createSessionStatusWatcher');
    const state = { activeSessionId: 'a' };
    let visible = true;
    const queryStatusFn = vi.fn(async (id) => ({ is_running: id === 'a' }));
    const setBusy = vi.fn();
    const w = create(state, { queryStatusFn, setBusy, onFinished: vi.fn(), isPageVisible: () => visible });
    await Promise.all([w.check('a'), w.watch('a')]);
    expect(queryStatusFn.mock.calls.filter((c) => c[0] === 'a')).toHaveLength(1);
    visible = false;
    await vi.advanceTimersByTimeAsync(4000);
    expect(queryStatusFn.mock.calls.filter((c) => c[0] === 'a')).toHaveLength(1);
    visible = true;
    state.activeSessionId = 'b';
    await w.watch('b');
    expect(setBusy).toHaveBeenLastCalledWith(false);
    await vi.advanceTimersByTimeAsync(6000);
    expect(queryStatusFn.mock.calls.filter((c) => c[0] === 'a')).toHaveLength(1);
  });
});

describe('CARD-485 select', () => {
  it('7. selecting re-renders the list with the chosen chat active (REQ-485-001)', async () => {
    const create = await need('createSessionSelect');
    vi.stubGlobal('document', { createElement: () => ({ className: '', innerHTML: '', addEventListener() {} }) });
    const sessionList = { innerHTML: '', items: [], appendChild(el) { this.items.push(el); } };
    const state = { activeSessionId: 'b', sessions: [{ id: 'a', title: 'A' }, { id: 'b', title: 'B' }] };
    const sel = create(state, baseDeps(state, { sessionList, onSelectSession: vi.fn() }));
    await sel.afterSelect('b');
    const active = sessionList.items.map((el) => el.className.includes('bg-slate-800 text-white'));
    expect(active).toEqual([false, true]);
  });

  it('8. a user pick closes the drawer, an automatic select does not; Options open refreshes context (REQ-485-002/008)', async () => {
    const create = await need('createSessionSelect');
    const drawer = { classList: fakeClassList([]) };
    const viewChat = { classList: fakeClassList(['sessions-drawer-open']) };
    const options = { classList: fakeClassList([]) }; // open (no 'hidden')
    const refreshContext = vi.fn(async () => {});
    const state = { activeSessionId: 's1', sessions: [] };
    const deps = baseDeps(state, {
      chatSessionsDrawer: drawer,
      viewChat,
      refreshContext,
      getEl: (id) => (id === 'chatOptionsDrawer' ? options : null),
    });
    const sel = create(state, deps);
    await sel.afterSelect('s1');
    expect(drawer.classList.contains('hidden')).toBe(false);
    await sel.afterSelect('s1', { userPick: true });
    expect(drawer.classList.contains('hidden')).toBe(true);
    expect(viewChat.classList.contains('sessions-drawer-open')).toBe(false);
    expect(refreshContext).toHaveBeenCalled();
    expect(deps.jumpToLatest).toHaveBeenCalled();
  });

  it('9. selecting a chat that is running shows busy through the default setter and blocks sending', async () => {
    const create = await need('createSessionSelect');
    const sendBtn = { disabled: false, classList: fakeClassList([]) };
    const stopBtn = { disabled: true, classList: fakeClassList(['hidden']) };
    const state = { activeSessionId: 's1', sessions: [] };
    const sel = create(state, baseDeps(state, {
      sendBtn,
      stopBtn,
      queryStatusFn: async () => ({ is_running: true }),
      isPageVisible: () => false,
    }));
    await sel.afterSelect('s1');
    expect(state.sessionBusy).toBe(true);
    expect(sendBtn.classList.contains('hidden')).toBe(true);
    expect(stopBtn.classList.contains('hidden')).toBe(false);
    sel.stopWatching();
    expect(state.sessionBusy).toBe(false);
    expect(sendBtn.classList.contains('hidden')).toBe(false);
  });
});
