import { describe, it, expect, vi, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';

import {
  setupComposerSizing,
  setComposerText,
} from '../../../src/web/static/modules/studios/chat/composer.js';
import {
  appendMessageBubble,
  openArtifactModal,
} from '../../../src/web/static/modules/studios/chat/render.js';
import { updateAvatarPreview } from '../../../src/web/static/modules/studios/forge/config.js';
import { setupAllowedOrigins } from '../../../src/web/static/modules/studios/settings_allowed_origins.js';
import { enhanceHitlDialogs } from '../../../src/web/static/modules/ui/agent_desktop/chrome.js';
import { showToast } from '../../../src/web/static/modules/ui/toast.js';

const repoRoot = path.resolve(__dirname, '../../..');
const read = (rel) => fs.readFileSync(path.join(repoRoot, rel), 'utf-8');

const LINE = 20;

class FakeTarget {
  constructor() {
    this.listeners = {};
    this.dataset = {};
    this.style = {};
    this.children = [];
    this.innerHTML = '';
    this.textContent = '';
    this.className = '';
    this.nodeType = 1;
    this.classList = {
      _set: new Set(),
      add(...cls) { cls.forEach((c) => this._set.add(c)); },
      remove(...cls) { cls.forEach((c) => this._set.delete(c)); },
      contains(c) { return this._set.has(c); },
      toggle(c, force) {
        const shouldAdd = force === undefined ? !this._set.has(c) : Boolean(force);
        if (shouldAdd) this._set.add(c);
        else this._set.delete(c);
        return shouldAdd;
      },
    };
  }
  addEventListener(type, fn) {
    (this.listeners[type] ||= []).push(fn);
  }
  removeEventListener(type, fn) {
    this.listeners[type] = (this.listeners[type] || []).filter((f) => f !== fn);
  }
  dispatchEvent(evt) {
    (this.listeners[evt.type] || []).slice().forEach((fn) => fn(evt));
    return true;
  }
  fire(type, extra = {}) {
    return this.dispatchEvent({ type, ...extra });
  }
  appendChild(child) {
    this.children.push(child);
    return child;
  }
  setAttribute(k, v) {
    this[k] = v;
  }
  getAttribute(k) {
    return this[k] ?? null;
  }
  querySelector() {
    return null;
  }
  querySelectorAll() {
    return [];
  }
}

describe('CARD-720: Chat reply copy button & composer post-send sizing', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('shrinks the focused composer back to 1 line immediately when cleared on send so reply clicks never miss', () => {
    const doc = new FakeTarget();
    doc.activeElement = null;
    const win = new FakeTarget();
    win.getComputedStyle = () => ({ lineHeight: `${LINE}px`, fontSize: '14px', paddingTop: '0px', paddingBottom: '0px' });
    win.setTimeout = (fn) => fn();

    const promptInput = new FakeTarget();
    promptInput.value = '';
    promptInput._lines = () => (promptInput.value ? promptInput.value.split('\n').length : 1);
    Object.defineProperty(promptInput, 'scrollHeight', { get: () => promptInput._lines() * LINE });
    promptInput.focus = () => {
      doc.activeElement = promptInput;
      promptInput.fire('focus');
    };

    setupComposerSizing({
      promptInput,
      columnEl: { clientHeight: 800 },
      messagesContainer: { scrollTop: 0, scrollHeight: 1000, clientHeight: 400 },
      composerRegion: new FakeTarget(),
      isStickToBottom: () => false,
      doc,
      win,
    });

    // User clicks into composer and types a prompt -> grows to 8 lines
    promptInput.fire('pointerdown');
    promptInput.focus();
    promptInput.value = 'Hello AutoReiv';
    promptInput.fire('input');
    expect(parseFloat(promptInput.style.height)).toBe(8 * LINE);

    // User sends the message -> setComposerText(promptInput, '') clears it while still focused
    setComposerText(promptInput, '');
    expect(parseFloat(promptInput.style.height)).toBe(LINE);
  });

  it('shows Copied! label and toast when clicking .copy-msg-btn on an assistant reply', async () => {
    const copyBtn = new FakeTarget();
    copyBtn.dataset = { content: 'Assistant reply markdown' };
    const span = { textContent: 'Copy' };
    copyBtn.querySelector = (sel) => (sel === 'span' ? span : null);

    const bubble = new FakeTarget();
    bubble.querySelector = (sel) => (sel === '.msg-body' ? new FakeTarget() : null);
    bubble.querySelectorAll = (sel) => (sel === '.copy-msg-btn' ? [copyBtn] : []);

    vi.stubGlobal('document', {
      createElement: () => bubble,
      getElementById: () => null,
    });

    const copyFn = vi.fn(async () => true);
    const toastFn = vi.fn();
    const container = new FakeTarget();

    appendMessageBubble('assistant', 'Assistant reply markdown', {
      messagesContainer: container,
      copyToClipboardFn: copyFn,
      showToastFn: toastFn,
      renderMarkdownFn: () => {},
    });

    expect(bubble.innerHTML).toContain('type="button"');
    expect(copyBtn.listeners.click?.length).toBe(1);
    await copyBtn.listeners.click[0]();

    expect(copyFn).toHaveBeenCalledWith('Assistant reply markdown');
    expect(span.textContent).toBe('Copied!');
    expect(toastFn).toHaveBeenCalledWith('Copied to clipboard', 'success');
  });

  it('passes (message, type) in the right order in openArtifactModal', async () => {
    const modal = new FakeTarget();
    vi.stubGlobal('document', {
      getElementById: (id) => (id === 'artifactModal' ? modal : null),
    });
    const toastFn = vi.fn();
    const fetchFn = vi.fn(async () => ({ ok: false, status: 500 }));

    await openArtifactModal('art-1', { fetchFn, showToastFn: toastFn });
    expect(toastFn).toHaveBeenCalledWith(expect.stringContaining('Failed to load artifact art-1'), 'error');
  });
});

describe('CARD-720: Single canonical #toggleSidebarBtn listener & desktop presets/modals', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('binds #toggleSidebarBtn only in chat/scroll.js, not in app.js or agent-desktop.js', () => {
    const appSrc = read('src/web/static/app.js');
    const desktopSrc = read('src/web/static/modules/ui/agent-desktop.js');
    const scrollSrc = read('src/web/static/modules/studios/chat/scroll.js');

    expect(appSrc).not.toContain("const toggleSidebarBtn = $('toggleSidebarBtn')");
    expect(desktopSrc).not.toContain("const toggleSidebarBtn = $('toggleSidebarBtn')");
    expect(scrollSrc).toContain('toggleSidebarBtn.addEventListener');
    expect(scrollSrc).not.toContain("classList.contains('radical-desktop-demo')");
  });

  it('replaces retired skill-studio and tools-studio in presets.js PRIORITY_TABS with capabilities', () => {
    const presetsSrc = read('src/web/static/modules/ui/agent_desktop/presets.js');
    expect(presetsSrc).toContain("'capabilities'");
    expect(presetsSrc).not.toContain("'skill-studio'");
    expect(presetsSrc).not.toContain("'tools-studio'");
  });

  it('elevates all studio modals with desktop-dialog-host in enhanceHitlDialogs', () => {
    const ids = [
      'chatToolsModal',
      'routineModal',
      'forgeNewAgentModal',
      'teachAgentModal',
      'manageTonesModal',
      'deleteAgentModal',
      'agentBrainDrawer',
      'wikiNewNoteModal',
      'wikiMindMapModal',
      'artifactModal',
    ];
    const map = {};
    ids.forEach((id) => {
      const m = new FakeTarget();
      m.firstElementChild = new FakeTarget();
      map[id] = m;
    });
    vi.stubGlobal('document', {
      getElementById: (id) => map[id] || null,
    });

    enhanceHitlDialogs();
    ids.forEach((id) => {
      expect(map[id].classList.contains('desktop-dialog-host'), id).toBe(true);
      expect(map[id].firstElementChild.classList.contains('desktop-dialog-window'), id).toBe(true);
    });
  });
});

describe('CARD-720: Wiki folder overview delete, Agent avatar preview, Allowed Origins & Toast warn alias', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('wires #wikiOverviewDeleteFolderBtn to onReloadVault instead of calling onNoteSelect(undefined)', () => {
    const folderSrc = read('src/web/static/modules/studios/wiki/folder.js');
    expect(folderSrc).not.toMatch(/onReloadVault:\s*typeof onNoteSelect/);
    expect(folderSrc).toMatch(/onReloadVault/);
  });

  it('updates #forgeAvatarPreview without nesting an <svg> inside <svg id="forgeAvatarIcon">', () => {
    const previewContainer = new FakeTarget();
    const existingSvg = new FakeTarget();
    vi.stubGlobal('document', {
      getElementById: (id) => {
        if (id === 'forgeAvatarPreview') return previewContainer;
        if (id === 'forgeAvatarIcon') return existingSvg;
        return null;
      },
    });

    updateAvatarPreview('sparkles');
    expect(previewContainer.innerHTML).toContain('id="forgeAvatarIcon"');
    expect(previewContainer.innerHTML).toContain('data-lucide="sparkles"');
    expect(existingSvg.innerHTML).toBe('');
  });

  it('guards #allowedOriginsSaveBtn against duplicate click listeners across repeated setupAllowedOrigins calls', () => {
    const input = new FakeTarget();
    const saveBtn = new FakeTarget();
    const status = new FakeTarget();
    const doc = {
      getElementById: (id) => {
        if (id === 'allowedOriginsInput') return input;
        if (id === 'allowedOriginsSaveBtn') return saveBtn;
        if (id === 'allowedOriginsStatus') return status;
        return null;
      },
    };
    const fetchFn = vi.fn(async () => ({ ok: true, status: 200, json: async () => ({ origins: [] }) }));

    setupAllowedOrigins({ doc, fetchFn });
    setupAllowedOrigins({ doc, fetchFn });
    expect(saveBtn.listeners.click?.length).toBe(1);
  });

  it('maps warn toast type to warning styling in showToast', () => {
    const container = new FakeTarget();
    const created = [];
    vi.stubGlobal('document', {
      getElementById: (id) => (id === 'toastContainer' ? container : null),
      createElement: () => {
        const el = new FakeTarget();
        created.push(el);
        return el;
      },
      body: new FakeTarget(),
    });

    const toastEl = showToast('Soft warning', 'warn', 0);
    expect(toastEl.className).toContain('border-amber-500/40');
    expect(toastEl.innerHTML).toContain('alert-triangle');
  });
});
