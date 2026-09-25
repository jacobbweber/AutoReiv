/**
 * Chat Studio: Quick Prompts picker [CARD-152, CARD-469]
 * Toggle, filter and pick from /api/prompts inside the Chat options drawer. Restores the pre-CARD-397
 * behaviour on the real template IDs (#chatPromptsBtn, #chatPromptsQuickPicker, #chatPromptsQuickSearch,
 * #chatPromptsQuickList, #chatManagePromptsBtn).
 */

import { escapeHtml } from '../../utils/formatters.js';
import { setComposerText } from './composer.js';

export function promptText(item) {
  return (item && (item.template_text ?? item.prompt ?? item.content)) || '';
}

export function filterQuickPrompts(prompts, query = '') {
  const q = String(query || '').toLowerCase().trim();
  const list = Array.isArray(prompts) ? prompts : [];
  if (!q) return list;
  return list.filter((p) => [p.title, p.category, p.description, promptText(p)]
    .some((v) => String(v || '').toLowerCase().includes(q)));
}

export function renderQuickPromptItems(items) {
  if (!items.length) {
    return '<div class="p-3 text-center text-slate-500 text-[11px]">No matching prompts</div>';
  }
  return items.map((item, idx) => `
    <div data-quick-idx="${idx}" class="quick-prompt-item p-2 rounded-xl bg-slate-950/70 hover:bg-slate-800/80 border border-slate-800/80 hover:border-slate-700 cursor-pointer transition flex items-center justify-between gap-2 group">
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-1.5">
          <span class="text-[9px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">${escapeHtml(item.category || 'general')}</span>
          <span class="text-xs font-semibold text-slate-200 truncate">${escapeHtml(item.title || 'Quick Prompt')}</span>
        </div>
        ${item.description ? `<p class="text-[10px] text-slate-400 truncate mt-0.5">${escapeHtml(item.description)}</p>` : ''}
      </div>
      <span class="px-2 py-1 bg-brand-600/80 group-hover:bg-brand-600 text-white rounded-lg text-[10px] font-semibold flex-shrink-0 transition">Insert</span>
    </div>
  `).join('');
}

export function setupQuickPromptPicker({
  chatPromptsBtn,
  chatPromptsQuickPicker,
  chatPromptsQuickSearch = null,
  chatPromptsQuickList = null,
  chatManagePromptsBtn = null,
  promptInput = null,
  showToastFn = null,
  onPicked = null,
  onManage = null,
  doc = typeof document !== 'undefined' ? document : null,
  fetchFn = null,
  setTimeoutFn = (fn, ms) => setTimeout(fn, ms),
} = {}) {
  if (!chatPromptsBtn || !chatPromptsQuickPicker) return null;
  let prompts = [];
  let rendered = [];

  const isOpen = () => !chatPromptsQuickPicker.classList.contains('hidden');
  const close = () => chatPromptsQuickPicker.classList.add('hidden');

  function render() {
    if (!chatPromptsQuickList) return;
    rendered = filterQuickPrompts(prompts, chatPromptsQuickSearch ? chatPromptsQuickSearch.value : '');
    chatPromptsQuickList.innerHTML = renderQuickPromptItems(rendered);
  }

  async function load() {
    const fn = fetchFn || globalThis.fetch;
    try {
      const res = await fn('/api/prompts');
      if (!res.ok) return;
      const data = await res.json();
      prompts = Array.isArray(data) ? data : (data?.prompts || []);
      render();
    } catch (err) {
      console.warn('[AutoReiv UI] Failed to load quick prompts:', err);
    }
  }

  chatPromptsBtn.addEventListener('click', (e) => {
    if (e && typeof e.stopPropagation === 'function') e.stopPropagation();
    if (isOpen()) {
      close();
      return undefined;
    }
    chatPromptsQuickPicker.classList.remove('hidden');
    if (chatPromptsQuickSearch) {
      chatPromptsQuickSearch.value = '';
      setTimeoutFn(() => chatPromptsQuickSearch.focus(), 50);
    }
    return load();
  });

  if (chatPromptsQuickSearch) chatPromptsQuickSearch.addEventListener('input', render);

  if (chatPromptsQuickList) {
    chatPromptsQuickList.addEventListener('click', (e) => {
      const row = e.target && typeof e.target.closest === 'function' ? e.target.closest('[data-quick-idx]') : null;
      if (!row) return;
      const item = rendered[parseInt(row.getAttribute('data-quick-idx'), 10)];
      if (!item || !promptInput) return;
      setComposerText(promptInput, promptText(item), { focus: true });
      close();
      if (typeof onPicked === 'function') onPicked(item);
      if (typeof showToastFn === 'function') showToastFn(`Loaded "${item.title || 'prompt'}"`, 'info');
    });
  }

  if (chatManagePromptsBtn) {
    chatManagePromptsBtn.addEventListener('click', () => {
      close();
      if (typeof onManage === 'function') onManage();
    });
  }

  if (doc) {
    doc.addEventListener('click', (e) => {
      if (!isOpen()) return;
      const t = e.target;
      if (chatPromptsQuickPicker.contains(t) || t === chatPromptsBtn || chatPromptsBtn.contains?.(t)) return;
      close();
    });
    doc.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && isOpen()) close();
    });
  }

  return { load, close, isOpen };
}
