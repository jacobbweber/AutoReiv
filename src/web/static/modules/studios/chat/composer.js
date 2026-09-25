/**
 * Chat Studio: Composer & Attachments Submodule [CARD-143, CARD-235, CARD-397]
 * Manages textarea keybindings [CARD-469], sizing [CARD-465], staged attachments, and send/stop controls.
 */

import { escapeHtml, formatBytes } from '../../utils/formatters.js';
import { isScrolledNearBottom } from './scroll.js';

// CARD-465: composer grows on focus up to an adaptive cap.
export const COMPOSER_MAX_LINES = 8;
export const COMPOSER_MAX_COLUMN_FRACTION = 0.4;

/**
 * Pure composer height rule [CARD-465 REQ-465-001/002/004/008].
 * focused (engaged) -> cap; otherwise with text -> fit content up to cap; empty -> 1 line.
 * cap = min(8 lines, 40% of the visible chat column), never below 1 line.
 */
export function computeComposerHeight({
  contentHeight = 0,
  lineHeight = 20,
  paddingY = 0,
  focused = false,
  hasText = false,
  columnHeight = 0,
} = {}) {
  const line = Math.max(1, Number(lineHeight) || 20);
  const pad = Math.max(0, Number(paddingY) || 0);
  const oneLine = line + pad;
  const linesCap = COMPOSER_MAX_LINES * line + pad;
  const col = Number(columnHeight) || 0;
  const columnCap = col > 0 ? Math.floor(col * COMPOSER_MAX_COLUMN_FRACTION) : Infinity;
  const cap = Math.max(oneLine, Math.min(linesCap, columnCap));
  const content = Math.max(oneLine, Number(contentHeight) || 0);
  let height;
  if (focused) height = cap;
  else if (!hasText) height = oneLine;
  else height = Math.min(content, cap);
  return { height, cap, oneLine, overflow: content > height };
}

/** Visible chat column height: the column, further limited by visualViewport (iOS keyboard). */
export function getVisibleColumnHeight(columnEl, win = typeof window !== 'undefined' ? window : null) {
  const col = Number(columnEl?.clientHeight) || 0;
  const vv = Number(win?.visualViewport?.height) || 0;
  if (col > 0 && vv > 0) return Math.min(col, vv);
  return col || 0;
}

function readComposerMetrics(el, win) {
  let lineHeight = 20;
  let paddingY = 0;
  try {
    const cs = win && typeof win.getComputedStyle === 'function' ? win.getComputedStyle(el) : null;
    if (cs) {
      const fontSize = parseFloat(cs.fontSize) || 14;
      const lh = parseFloat(cs.lineHeight);
      lineHeight = Number.isFinite(lh) && lh > 0 ? lh : fontSize * 1.625;
      paddingY = (parseFloat(cs.paddingTop) || 0) + (parseFloat(cs.paddingBottom) || 0);
    }
  } catch {
    /* keep defaults */
  }
  return { lineHeight, paddingY };
}

/**
 * Size the composer, pin a stuck-to-bottom list, and wire focus/blur/input/viewport listeners.
 * Returns { fit } so callers can force a re-measure. Null-safe.
 */
export function setupComposerSizing({
  promptInput,
  columnEl = null,
  messagesContainer = null,
  composerRegion = null,
  pressRegions = [], // CARD-470: e.g. #pendingHitlHost, so Approve/Reject is not lost to the shrink
  isStickToBottom = null,
  win = typeof window !== 'undefined' ? window : null,
  doc = typeof document !== 'undefined' ? document : null,
} = {}) {
  if (!promptInput || !promptInput.style) return { fit: () => null };
  let pressing = false;
  // Grow only when Jacob engages the box (click/tap or typing), not on the auto-focus when Chat opens.
  let engaged = false;

  const listPinned = () => {
    if (!messagesContainer) return false;
    if (typeof isStickToBottom === 'function') return Boolean(isStickToBottom());
    return isScrolledNearBottom(messagesContainer);
  };

  const pin = (pinned) => {
    if (pinned && messagesContainer) messagesContainer.scrollTop = messagesContainer.scrollHeight;
  };

  function fit() {
    const pinned = listPinned();
    const { lineHeight, paddingY } = readComposerMetrics(promptInput, win);
    promptInput.style.height = 'auto';
    const result = computeComposerHeight({
      contentHeight: Number(promptInput.scrollHeight) || 0,
      lineHeight,
      paddingY,
      focused: engaged && Boolean(doc && doc.activeElement === promptInput),
      hasText: String(promptInput.value || '').length > 0,
      columnHeight: getVisibleColumnHeight(columnEl, win),
    });
    promptInput.style.height = `${result.height}px`;
    promptInput.style.overflowY = result.overflow ? 'auto' : 'hidden';
    pin(pinned);
    return result;
  }

  const engage = () => {
    if (engaged) return;
    engaged = true;
    fit();
  };
  promptInput.addEventListener('pointerdown', engage);
  promptInput.addEventListener('keydown', engage);
  promptInput.addEventListener('focus', fit);
  promptInput.addEventListener('input', fit);
  promptInput.addEventListener('blur', () => {
    engaged = false;
    // A click inside the composer (Options drawer, send, toolbar) must land before we shrink.
    if (!pressing) fit();
  });

  [composerRegion, ...(pressRegions || [])].forEach((region) => {
    if (region && typeof region.addEventListener === 'function') {
      region.addEventListener('pointerdown', () => {
        pressing = true;
      });
    }
  });
  const release = () => {
    if (!pressing) return;
    pressing = false;
    const defer = win && typeof win.setTimeout === 'function' ? win.setTimeout.bind(win) : (fn) => fn();
    defer(fit, 0);
  };
  if (doc && typeof doc.addEventListener === 'function') {
    doc.addEventListener('pointerup', release, true);
    doc.addEventListener('pointercancel', release, true);
  }

  const onViewport = () => fit();
  if (win && typeof win.addEventListener === 'function') win.addEventListener('resize', onViewport);
  if (win?.visualViewport && typeof win.visualViewport.addEventListener === 'function') {
    win.visualViewport.addEventListener('resize', onViewport);
  }

  // Options drawer / attachments / HITL change the space below the list: keep a pinned list pinned.
  if (composerRegion && win && typeof win.ResizeObserver === 'function') {
    try {
      const ro = new win.ResizeObserver(() => pin(listPinned()));
      ro.observe(composerRegion);
    } catch {
      /* ResizeObserver optional */
    }
  }

  fit();
  return { fit };
}

/**
 * Shared composer setter [CARD-465 REQ-465-009]: every programmatic write goes through here
 * so the composer resizes (the input event drives setupComposerSizing).
 */
export function setComposerText(el, text, { focus = false } = {}) {
  if (!el) return false;
  el.value = text == null ? '' : String(text);
  try {
    const evt = typeof Event === 'function' ? new Event('input', { bubbles: true }) : { type: 'input' };
    if (typeof el.dispatchEvent === 'function') el.dispatchEvent(evt);
  } catch {
    /* ignore */
  }
  if (focus && typeof el.focus === 'function') el.focus();
  return true;
}

export function renderStagedAttachments({
  chatAttachmentsPreviewList,
  stagedAttachments,
  onRemove = null,
} = {}) {
  if (!chatAttachmentsPreviewList) return;
  if (!Array.isArray(stagedAttachments) || stagedAttachments.length === 0) {
    chatAttachmentsPreviewList.innerHTML = '';
    chatAttachmentsPreviewList.classList.add('hidden');
    return;
  }
  chatAttachmentsPreviewList.classList.remove('hidden');
  chatAttachmentsPreviewList.innerHTML = stagedAttachments
    .map((att, idx) => {
      const isImg = att.content_type?.startsWith('image/') || /\.(png|jpe?g|gif|webp|svg)$/i.test(att.filename || '');
      const icon = isImg ? '🖼️' : '📄';
      return `
        <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-slate-800/90 border border-slate-700 text-xs text-slate-200 flex-shrink-0 shadow-sm" data-att-idx="${idx}">
          <span class="text-xs">${icon}</span>
          <span class="font-medium max-w-[120px] truncate text-[11px]" title="${escapeHtml(att.filename || 'file')}">${escapeHtml(att.filename || 'file')}</span>
          <span class="text-[10px] text-slate-400 font-mono">(${formatBytes(att.size_bytes || 0)})</span>
          <button type="button" class="remove-attachment-btn text-slate-400 hover:text-rose-400 p-0.5 rounded transition" data-att-idx="${idx}" title="Remove file">
            <svg class="w-3 h-3 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
          </button>
        </div>
      `;
    })
    .join('');

  chatAttachmentsPreviewList.querySelectorAll('.remove-attachment-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const idx = parseInt(btn.getAttribute('data-att-idx'), 10);
      if (!isNaN(idx) && idx >= 0 && idx < stagedAttachments.length) {
        stagedAttachments.splice(idx, 1);
        renderStagedAttachments({ chatAttachmentsPreviewList, stagedAttachments, onRemove });
        if (typeof onRemove === 'function') onRemove(idx);
      }
    });
  });
}

export async function uploadStagedFile(file, sessionId = null, fetchFn = null) {
  const fn = fetchFn || (typeof window !== 'undefined' ? window.fetch : globalThis.fetch);
  const formData = new FormData();
  formData.append('file', file);
  if (sessionId) {
    formData.append('session_id', sessionId);
  }
  const res = await fn('/api/chat/upload', {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error('Failed to upload file');
  return await res.json();
}

export function setupComposerAttachments({
  chatAttachBtn,
  chatFileInput,
  chatAttachmentsPreviewList,
  stagedAttachments = null,
  getStagedAttachments = null,
  getSessionId = () => null,
  showToastFn = null,
  onBeforeAttach = null,
  fetchFn = null,
} = {}) {
  if (!chatAttachBtn || !chatFileInput) return;
  // Resolve the list on every use so a caller that clears/replaces it never strands uploads [CARD-469].
  const staged = () => (typeof getStagedAttachments === 'function' ? getStagedAttachments() : stagedAttachments);

  chatAttachBtn.addEventListener('click', () => {
    chatFileInput.click();
  });

  chatFileInput.addEventListener('change', async (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    // Awaited so a session made here (CARD-476) is used for the upload, not attachments/global.
    if (typeof onBeforeAttach === 'function') await onBeforeAttach();

    for (const file of files) {
      try {
        const uploaded = await uploadStagedFile(file, getSessionId(), fetchFn);
        const stagedAttachments = staged();
        stagedAttachments.push({
          id: uploaded.id,
          filename: uploaded.filename,
          size_bytes: uploaded.size_bytes,
          content_type: uploaded.content_type,
          url: uploaded.url,
          path: uploaded.path,
        });
        renderStagedAttachments({ chatAttachmentsPreviewList, stagedAttachments });
        if (typeof showToastFn === 'function') {
          showToastFn(`Attached ${uploaded.filename}`, 'info');
        }
      } catch (err) {
        console.error('[AutoReiv UI] Failed to attach file:', err);
        if (typeof showToastFn === 'function') {
          showToastFn(`Failed to upload ${file.name}: ${err.message}`, 'error');
        }
      }
    }
    chatFileInput.value = '';
  });
}

/**
 * Enter sends, Shift+Enter is a newline, on every device including phones [CARD-469 D1].
 * Enter that confirms an IME composition is left alone; Enter mid-stream is swallowed [D2].
 */
export function setupComposerKeyboard({
  promptInput,
  chatForm,
  isStreaming = () => false,
} = {}) {
  if (!promptInput) return;
  promptInput.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' || e.shiftKey) return;
    if (e.isComposing || e.keyCode === 229) return;
    e.preventDefault();
    if (isStreaming() || !chatForm) return;
    if (typeof chatForm.requestSubmit === 'function') {
      chatForm.requestSubmit();
    } else {
      const evt = typeof Event === 'function' ? new Event('submit', { cancelable: true }) : { type: 'submit' };
      chatForm.dispatchEvent(evt);
    }
  });
}

/** Clear staged attachments in place (keeps the array identity the upload handler reads) [CARD-469]. */
export function clearStagedAttachments(state, chatAttachmentsPreviewList = null) {
  if (!state) return;
  if (Array.isArray(state.stagedAttachments)) state.stagedAttachments.length = 0;
  else state.stagedAttachments = [];
  renderStagedAttachments({ chatAttachmentsPreviewList, stagedAttachments: state.stagedAttachments });
}

/**
 * Wire the composer's paperclip and Enter-to-send from the real template IDs [CARD-469].
 * Replaces the positional calls the CARD-397 split left in chat.js, which wired nothing.
 */
export function wireComposer(state, {
  getEl = (id) => (typeof document !== 'undefined' ? document.getElementById(id) : null),
  chatForm = null,
  promptInput = null,
  showToastFn = null,
  onBeforeAttach = null,
  fetchFn = null,
} = {}) {
  if (!Array.isArray(state.stagedAttachments)) state.stagedAttachments = [];
  setupComposerAttachments({
    chatAttachBtn: getEl('chatAttachBtn'),
    chatFileInput: getEl('chatFileInput'),
    chatAttachmentsPreviewList: getEl('chatAttachmentsPreviewList'),
    getStagedAttachments: () => state.stagedAttachments,
    getSessionId: () => state.activeSessionId || null,
    showToastFn,
    onBeforeAttach,
    fetchFn,
  });
  setupComposerKeyboard({ promptInput, chatForm, isStreaming: () => !!state.isStreaming });
}

export function setupComposerControls({
  chatForm,
  promptInput,
  _sendBtn,
  stopBtn,
  state,
  onExecuteTurn,
  onOpenTeachAgent,
  onCancelStream,
  ensureSession = null,
} = {}) {
  let preparing = false; // CARD-476: a second Enter while the session is being made is ignored
  if (chatForm) {
    chatForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!promptInput || state.isStreaming || state.sessionBusy || preparing) return; // CARD-485: busy elsewhere
      const text = promptInput.value.trim();
      if (!text && (!state.stagedAttachments || state.stagedAttachments.length === 0)) return;

      if (text.startsWith('/learn')) {
        setComposerText(promptInput, '');
        const guidance = text.replace(/^\/learn\s*/, '');
        // CARD-500 REQ-500-004: /learn teaches from the latest reply in this chat.
        const latest = [...(state.messages || [])].reverse().find((m) => m && m.role === 'assistant' && m.id);
        if (typeof onOpenTeachAgent === 'function') {
          onOpenTeachAgent({ targetAgentId: state.selectedAgentId, guidance, messageId: latest ? latest.id : null });
        }
        return;
      }

      // CARD-476: never send with no session; if one can't be made, keep the typed text.
      if ((!state.activeSessionId || state.sessionsLoading) && typeof ensureSession === 'function') {
        preparing = true;
        const sessionId = await Promise.resolve(ensureSession()).finally(() => { preparing = false; });
        if (!sessionId) return;
      }

      setComposerText(promptInput, '');
      if (typeof onExecuteTurn === 'function') {
        await onExecuteTurn(text);
      }
    });
  }

  if (stopBtn) {
    stopBtn.addEventListener('click', () => {
      if (typeof onCancelStream === 'function') {
        onCancelStream();
      }
    });
  }
}

