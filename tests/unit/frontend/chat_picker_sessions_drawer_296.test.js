/**
 * CARD-296 — Chat picker / sessions drawer / jump-to-latest (TDD)
 */
import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');
const indexPath = path.join(repoRoot, 'src/web/templates/index.html');
const chatJsPath = path.join(repoRoot, 'src/web/static/modules/studios/chat.js');
const desktopJsPath = path.join(repoRoot, 'src/web/static/modules/ui/agent-desktop.js');

function read(p) {
  return fs.readFileSync(p, 'utf-8');
}

describe('CARD-296 DOM contract — one agent picker + in-studio sessions drawer', () => {
  let html;
  let chatJs;
  let desktopJs;

  beforeEach(() => {
    html = read(indexPath);
    chatJs = read(chatJsPath) + read(path.join(repoRoot, 'src/web/static/modules/studios/chat/render.js'));
    desktopJs = read(desktopJsPath);
  });

  it('keeps a single left agent picker (agentSelect) and removes chatTopBarAgentSelect', () => {
    expect(html).toContain('id="agentSelect"');
    expect(html).not.toContain('id="chatTopBarAgentSelect"');
    // Picker lives in Chat top bar (left), not in the sessions drawer
    const drawerSlice = html.slice(
      html.indexOf('id="chatSessionsDrawer"'),
      html.indexOf('id="messagesContainer"'),
    );
    expect(drawerSlice).toContain('id="chatSessionsDrawer"');
    expect(drawerSlice).not.toContain('id="agentSelect"');
    expect(drawerSlice).not.toMatch(/Active Agent/i);
  });

  it('sessions control is an in-studio left drawer with New Conversation + recent only', () => {
    expect(html).toContain('id="chatSessionsDrawer"');
    expect(html).toContain('id="newChatBtn"');
    expect(html).toContain('New Conversation');
    expect(html).toContain('id="sessionList"');
    expect(html).toContain('id="toggleSidebarBtn"');
    expect(html).toContain('id="chatSessionsDrawerCloseBtn"');
  });

  it('removes Sessions as a dedicated dock launcher', () => {
    expect(desktopJs).not.toMatch(/id:\s*'dock-sessions'/);
    expect(desktopJs).not.toMatch(/\{\s*id:\s*'dock-sessions'[\s\S]*?tab:\s*'sessions'/);
    expect(desktopJs).toMatch(/Sessions is (Chat in-studio drawer only|an in-studio Chat drawer)/);
  });

  it('exposes Jump to latest control near the message stream', () => {
    expect(html).toContain('id="chatJumpToLatestBtn"');
    expect(html).toMatch(/Jump to latest/i);
  });

  it('labels both Wiki entry points Save to Wiki', () => {
    expect(html).toContain('id="exportThreadWikiBtn"');
    const wikiBtn = html.slice(
      html.indexOf('id="exportThreadWikiBtn"'),
      html.indexOf('id="exportThreadWikiBtn"') + 500,
    );
    expect(wikiBtn).toMatch(/Save to Wiki/);
    expect(chatJs).toContain('Save to Wiki');
    expect(chatJs).not.toMatch(/train-lab-msg-btn/);
    expect(chatJs).not.toMatch(/>Train in Lab</);
  });

  it('keeps Train Agent checkbox (durable Factory path) and Workbench shelf', () => {
    expect(html).toContain('id="trainAgentToggle"');
    expect(html).toContain('id="chatWorkbenchPane"');
    expect(html).toContain('id="workbenchSaveWikiBtn"');
    expect(html).toContain('id="chatShowJourneyBtn"');
    expect(html).toContain('id="chatDebugToggleBtn"');
  });
});

describe('CARD-296 smart autoscroll helpers', () => {
  it('detects near-bottom and jump visibility', async () => {
    const {
      isScrolledNearBottom,
      shouldAutoscrollOnStream,
      shouldShowJumpToLatest,
      CHAT_SCROLL_BOTTOM_THRESHOLD_PX,
    } = await import('../../../src/web/static/modules/studios/chat.js');

    expect(CHAT_SCROLL_BOTTOM_THRESHOLD_PX).toBeGreaterThan(0);

    const nearBottom = {
      scrollHeight: 1000,
      scrollTop: 920,
      clientHeight: 80,
    };
    const scrolledUp = {
      scrollHeight: 1000,
      scrollTop: 100,
      clientHeight: 80,
    };
    expect(isScrolledNearBottom(nearBottom)).toBe(true);
    expect(isScrolledNearBottom(scrolledUp)).toBe(false);
    expect(shouldAutoscrollOnStream(true)).toBe(true);
    expect(shouldAutoscrollOnStream(false)).toBe(false);
    expect(shouldShowJumpToLatest({ stickToBottom: false, hasOverflow: true })).toBe(true);
    expect(shouldShowJumpToLatest({ stickToBottom: true, hasOverflow: true })).toBe(false);
    expect(shouldShowJumpToLatest({ stickToBottom: false, hasOverflow: false })).toBe(false);
  });

  it('exports sessions drawer open/collapse helpers', async () => {
    const {
      isChatSessionsDrawerOpen,
      openChatSessionsDrawer,
      collapseChatSessionsDrawer,
    } = await import('../../../src/web/static/modules/studios/chat.js');

    const drawer = { classList: { _s: new Set(['hidden']), contains(c) { return this._s.has(c); }, add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); }, toggle(c, force) {
      if (force === true) this._s.add(c); else if (force === false) this._s.delete(c); else if (this._s.has(c)) this._s.delete(c); else this._s.add(c);
    } } };
    const view = { classList: { _s: new Set(), contains(c) { return this._s.has(c); }, add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); }, toggle(c, force) {
      if (force === true) this._s.add(c); else if (force === false) this._s.delete(c); else if (this._s.has(c)) this._s.delete(c); else this._s.add(c);
    } } };

    expect(isChatSessionsDrawerOpen(drawer)).toBe(false);
    openChatSessionsDrawer(drawer, view);
    expect(isChatSessionsDrawerOpen(drawer)).toBe(true);
    expect(view.classList.contains('sessions-drawer-open')).toBe(true);
    collapseChatSessionsDrawer(drawer, view);
    expect(isChatSessionsDrawerOpen(drawer)).toBe(false);
    expect(view.classList.contains('sessions-drawer-open')).toBe(false);
  });
});

describe('CARD-296 dock launchers no longer include sessions', () => {
  it('DOCK_LAUNCHERS excludes sessions tab', async () => {
    const { DOCK_LAUNCHERS } = await import('../../../src/web/static/modules/ui/agent-desktop.js');
    const tabs = DOCK_LAUNCHERS.map((d) => d.tab);
    expect(tabs).not.toContain('sessions');
    expect(tabs).toEqual(
      expect.arrayContaining([
        'chat', 'wiki', 'projects', 'agents', 'factory', 'routines',
        'observability', 'settings', 'prompts', 'education',
      ]),
    );
  });
});
