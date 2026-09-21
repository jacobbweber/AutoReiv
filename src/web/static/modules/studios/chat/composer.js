/**
 * Chat Studio: Composer & Attachments Submodule [CARD-143, CARD-235, CARD-397]
 * Manages textarea keybindings, auto-resize, staged attachments, drop/paste, and send/stop controls.
 */

import { escapeHtml, formatBytes } from '../../utils/formatters.js';

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
  stagedAttachments,
  getSessionId = () => null,
  showToastFn = null,
  onBeforeAttach = null,
} = {}) {
  if (!chatAttachBtn || !chatFileInput) return;

  chatAttachBtn.addEventListener('click', () => {
    chatFileInput.click();
  });

  chatFileInput.addEventListener('change', async (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    if (typeof onBeforeAttach === 'function') onBeforeAttach();

    for (const file of files) {
      try {
        const uploaded = await uploadStagedFile(file, getSessionId());
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

export function setupComposerKeyboard({
  promptInput,
  chatForm,
} = {}) {
  if (!promptInput) return;
  promptInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (chatForm) {
        if (typeof chatForm.requestSubmit === 'function') {
          chatForm.requestSubmit();
        } else {
          chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
        }
      }
    }
  });
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
} = {}) {
  if (chatForm) {
    chatForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!promptInput) return;
      const text = promptInput.value.trim();
      if (!text && (!state.stagedAttachments || state.stagedAttachments.length === 0)) return;

      if (text.startsWith('/learn')) {
        promptInput.value = '';
        const guidance = text.replace(/^\/learn\s*/, '');
        if (typeof onOpenTeachAgent === 'function') {
          onOpenTeachAgent({
            targetAgentId: state.selectedAgentId,
            guidance,
          });
        }
        return;
      }

      promptInput.value = '';
      promptInput.style.height = 'auto';
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

