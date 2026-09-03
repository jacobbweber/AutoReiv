/**
 * Prompts Studio Controller [CARD-152, REQ-PROMPT-STUDIO-002, REQ-PROMPT-STUDIO-003].
 * Dedicated management workspace for prompt catalog recipes, templates, and 1-click execution.
 */

import { $ } from '../dom.js';
import { escapeHtml } from '../utils/formatters.js';
import { showToast } from '../ui/toast.js';

export function initPromptsStudio() {
  const promptsStudioList = $('promptsStudioList');
  const promptsStudioSearch = $('promptsStudioSearch');
  const promptsStudioCategoryPills = $('promptsStudioCategoryPills');
  const promptsStudioRefreshBtn = $('promptsStudioRefreshBtn');
  const promptsStudioNewBtn = $('promptsStudioNewBtn');
  const promptsStudioForm = $('promptsStudioForm');
  const promptsEditorId = $('promptsEditorId');
  const promptsEditorTitle = $('promptsEditorTitle');
  const promptsEditorCategory = $('promptsEditorCategory');
  const promptsEditorDescription = $('promptsEditorDescription');
  const promptsEditorTags = $('promptsEditorTags');
  const promptsEditorTemplate = $('promptsEditorTemplate');
  const promptsEditorDeleteBtn = $('promptsEditorDeleteBtn');
  const promptsEditorTestChatBtn = $('promptsEditorTestChatBtn');
  const promptsEditorBuiltinBadge = $('promptsEditorBuiltinBadge');
  const promptsEditorHeaderTitle = $('promptsEditorHeaderTitle');

  let promptsList = [];
  let selectedCategory = 'all';
  let selectedPromptId = null;

  async function loadPrompts() {
    if (!promptsStudioList) return;
    try {
      const res = await fetch('/api/prompts');
      if (!res.ok) throw new Error('Failed to load prompts');
      promptsList = await res.json();
      renderPromptsList();
      if (!selectedPromptId && promptsList.length > 0) {
        selectPrompt(promptsList[0]);
      } else if (selectedPromptId) {
        const current = promptsList.find(p => p.id === selectedPromptId);
        if (current) selectPrompt(current);
        else if (promptsList.length > 0) selectPrompt(promptsList[0]);
      }
    } catch (err) {
      console.error('[Prompts Studio] Error:', err);
      promptsStudioList.innerHTML = `<div class="p-4 text-center text-slate-500 text-xs">Failed to load prompt catalog: ${escapeHtml(err.message)}</div>`;
    }
  }

  function renderPromptsList() {
    if (!promptsStudioList) return;
    const q = (promptsStudioSearch?.value || '').toLowerCase().trim();
    const cat = selectedCategory.toLowerCase();

    const filtered = promptsList.filter(p => {
      const matchCat = cat === 'all' || (p.category || '').toLowerCase() === cat;
      if (!matchCat) return false;
      if (!q) return true;
      const titleMatch = (p.title || '').toLowerCase().includes(q);
      const descMatch = (p.description || '').toLowerCase().includes(q);
      const textMatch = (p.template_text || '').toLowerCase().includes(q);
      const tagsMatch = Array.isArray(p.tags) && p.tags.some(t => t.toLowerCase().includes(q));
      return titleMatch || descMatch || textMatch || tagsMatch;
    });

    if (filtered.length === 0) {
      promptsStudioList.innerHTML = `
        <div class="p-6 text-center text-slate-500 space-y-1">
          <p class="text-xs font-medium">No prompts found</p>
          <p class="text-[11px] text-slate-600">Try another search or create a new prompt template.</p>
        </div>
      `;
      return;
    }

    const catColors = {
      system: 'bg-purple-950/80 text-purple-300 border-purple-800/60',
      productivity: 'bg-emerald-950/80 text-emerald-300 border-emerald-800/60',
      coding: 'bg-amber-950/80 text-amber-300 border-amber-800/60',
      analysis: 'bg-cyan-950/80 text-cyan-300 border-cyan-800/60',
      general: 'bg-slate-800 text-slate-300 border-slate-700',
    };

    promptsStudioList.innerHTML = filtered.map(item => {
      const isSelected = item.id === selectedPromptId;
      const colorClass = catColors[(item.category || 'general').toLowerCase()] || catColors.general;
      const activeClass = isSelected
        ? 'bg-slate-800/95 border-brand-500/80 shadow-md shadow-brand-500/10'
        : 'bg-slate-900/60 border-slate-800/80 hover:bg-slate-800/60 hover:border-slate-700';

      return `
        <div data-prompt-id="${escapeHtml(item.id)}" class="prompt-card cursor-pointer p-3 rounded-xl border transition flex flex-col space-y-1.5 ${activeClass}">
          <div class="flex items-center justify-between gap-1.5">
            <span class="text-[9px] uppercase font-mono px-2 py-0.5 rounded border ${colorClass}">${escapeHtml(item.category || 'general')}</span>
            ${item.is_builtin ? '<span class="text-[10px] text-amber-400 font-mono">★ Builtin</span>' : ''}
          </div>
          <h4 class="font-bold text-xs text-white truncate">${escapeHtml(item.title)}</h4>
          ${item.description ? `<p class="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">${escapeHtml(item.description)}</p>` : ''}
        </div>
      `;
    }).join('');

    promptsStudioList.querySelectorAll('.prompt-card').forEach(el => {
      el.addEventListener('click', () => {
        const id = el.getAttribute('data-prompt-id');
        const target = promptsList.find(p => p.id === id);
        if (target) {
          selectPrompt(target);
          renderPromptsList();
        }
      });
    });
  }

  function selectPrompt(item) {
    if (!item) return;
    selectedPromptId = item.id;
    if (promptsEditorId) promptsEditorId.value = item.id;
    if (promptsEditorTitle) promptsEditorTitle.value = item.title || '';
    if (promptsEditorCategory) promptsEditorCategory.value = (item.category || 'general').toLowerCase();
    if (promptsEditorDescription) promptsEditorDescription.value = item.description || '';
    if (promptsEditorTags) promptsEditorTags.value = (item.tags || []).join(', ');
    if (promptsEditorTemplate) promptsEditorTemplate.value = item.template_text || '';

    if (promptsEditorHeaderTitle) {
      promptsEditorHeaderTitle.textContent = item.title;
    }
    if (promptsEditorBuiltinBadge) {
      promptsEditorBuiltinBadge.classList.toggle('hidden', !item.is_builtin);
    }
    if (promptsEditorDeleteBtn) {
      promptsEditorDeleteBtn.classList.toggle('hidden', Boolean(item.is_builtin));
    }
  }

  function resetEditor() {
    selectedPromptId = null;
    if (promptsEditorId) promptsEditorId.value = '';
    if (promptsEditorTitle) {
      promptsEditorTitle.value = '';
      promptsEditorTitle.focus();
    }
    if (promptsEditorCategory) promptsEditorCategory.value = selectedCategory !== 'all' ? selectedCategory : 'general';
    if (promptsEditorDescription) promptsEditorDescription.value = '';
    if (promptsEditorTags) promptsEditorTags.value = '';
    if (promptsEditorTemplate) promptsEditorTemplate.value = '';
    if (promptsEditorHeaderTitle) promptsEditorHeaderTitle.textContent = 'Create New Prompt Template';
    if (promptsEditorBuiltinBadge) promptsEditorBuiltinBadge.classList.add('hidden');
    if (promptsEditorDeleteBtn) promptsEditorDeleteBtn.classList.add('hidden');
  }

  if (promptsStudioCategoryPills) {
    promptsStudioCategoryPills.querySelectorAll('.studio-cat-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        promptsStudioCategoryPills.querySelectorAll('.studio-cat-pill').forEach(p => {
          p.classList.remove('active', 'bg-brand-600', 'text-white');
          p.classList.add('bg-slate-800', 'text-slate-300');
        });
        pill.classList.add('active', 'bg-brand-600', 'text-white');
        pill.classList.remove('bg-slate-800', 'text-slate-300');
        selectedCategory = pill.getAttribute('data-category') || 'all';
        renderPromptsList();
      });
    });
  }

  if (promptsStudioSearch) {
    promptsStudioSearch.addEventListener('input', () => {
      renderPromptsList();
    });
  }

  if (promptsStudioRefreshBtn) {
    promptsStudioRefreshBtn.addEventListener('click', () => {
      loadPrompts();
      showToast('Prompts refreshed', 'info');
    });
  }

  if (promptsStudioNewBtn) {
    promptsStudioNewBtn.addEventListener('click', () => {
      resetEditor();
      renderPromptsList();
    });
  }

  if (promptsStudioForm) {
    promptsStudioForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const id = (promptsEditorId?.value || '').trim();
      const title = (promptsEditorTitle?.value || '').trim();
      const category = promptsEditorCategory?.value || 'general';
      const description = (promptsEditorDescription?.value || '').trim();
      const templateText = (promptsEditorTemplate?.value || '').trim();
      const tags = (promptsEditorTags?.value || '').split(',').map(t => t.trim()).filter(Boolean);

      if (!title || !templateText) {
        showToast('Title and Template Text are required', 'error');
        return;
      }

      try {
        const isUpdate = id && !id.startsWith('builtin_');
        let res;
        if (isUpdate) {
          res = await fetch(`/api/prompts/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, category, description, template_text: templateText, tags }),
          });
        } else {
          res = await fetch('/api/prompts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, category, description, template_text: templateText, tags }),
          });
        }

        if (!res.ok) throw new Error('Failed to save prompt');
        const saved = await res.json();
        showToast(isUpdate ? 'Prompt updated' : 'Prompt created', 'info');
        selectedPromptId = saved.id;
        await loadPrompts();
      } catch (err) {
        console.error('[Prompts Studio] Error saving:', err);
        showToast(err.message, 'error');
      }
    });
  }

  if (promptsEditorDeleteBtn) {
    promptsEditorDeleteBtn.addEventListener('click', async () => {
      const id = promptsEditorId?.value;
      if (!id || id.startsWith('builtin_')) return;
      if (!confirm('Are you sure you want to delete this prompt template?')) return;

      try {
        const res = await fetch(`/api/prompts/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Failed to delete prompt');
        showToast('Prompt deleted', 'info');
        selectedPromptId = null;
        await loadPrompts();
      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }

  if (promptsEditorTestChatBtn) {
    promptsEditorTestChatBtn.addEventListener('click', () => {
      const text = promptsEditorTemplate?.value || '';
      if (!text) {
        showToast('Prompt template is empty', 'error');
        return;
      }
      const chatTab = $('tab-chat');
      if (chatTab) chatTab.click();
      const promptInput = $('promptInput');
      if (promptInput) {
        promptInput.value = text;
        promptInput.dispatchEvent(new Event('input'));
        promptInput.focus();
        showToast('Prompt loaded into Chat Studio', 'info');
      }
    });
  }

  return {
    loadPrompts,
    selectPrompt,
  };
}
