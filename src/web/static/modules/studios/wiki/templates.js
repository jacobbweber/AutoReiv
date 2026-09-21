/**
 * Wiki Studio: Templates & Note Authoring Submodule [CARD-178, CARD-298, CARD-308, CARD-399]
 * Manages structured templates discovery, new note modal, dynamic template prefilling,
 * and rule-based inbox graduation.
 */

import { $, safeCreateIcons } from '../../dom.js';
import { showToast } from '../../ui/toast.js';

let cachedWikiTemplates = [];

/**
 * Returns cached wiki templates array.
 */
export function getCachedWikiTemplates() {
  return cachedWikiTemplates;
}

/**
 * Fetches and populates template options in the new note modal [CARD-178, REQ-WIKI-035].
 */
export async function loadWikiTemplates() {
  const newNoteTemplateSelect = $('newNoteTemplateSelect');
  if (!newNoteTemplateSelect) return [];
  try {
    const res = await fetch('/api/wiki/templates');
    if (!res.ok) return [];
    cachedWikiTemplates = await res.json();
    const currentVal = newNoteTemplateSelect.value;
    newNoteTemplateSelect.innerHTML = '<option value="">None (Freeform Topic Synthesis)</option>';
    for (const tmpl of cachedWikiTemplates) {
      const opt = document.createElement('option');
      opt.value = tmpl.slug;
      opt.textContent = tmpl.title;
      newNoteTemplateSelect.appendChild(opt);
    }
    newNoteTemplateSelect.value = currentVal || '';
    return cachedWikiTemplates;
  } catch (e) {
    console.warn('[AutoReiv UI] Failed to load wiki templates:', e);
    return [];
  }
}

/**
 * Sets up rule-based inbox curation / graduation listeners [CARD-298, CARD-308].
 */
export function setupWikiCuration({ onReloadVault = null } = {}) {
  const wikiCurateInboxBtn = $('wikiCurateInboxBtn');
  if (!wikiCurateInboxBtn) return;

  wikiCurateInboxBtn.addEventListener('click', async () => {
    try {
      wikiCurateInboxBtn.disabled = true;
      wikiCurateInboxBtn.classList.add('opacity-50', 'pointer-events-none');
      const res = await fetch('/api/wiki/curate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const count = data.curated_count || 0;
      const heldCount = data.held_count || 0;
      let gradMsg;
      if (count > 0 && heldCount > 0) {
        gradMsg = `Graduated ${count}, held ${heldCount} in Inbox (see graduate_errors)`;
      } else if (count > 0) {
        gradMsg = `Rule-based graduate filed ${count} note${count === 1 ? '' : 's'} (not agent review)`;
      } else if (heldCount > 0) {
        gradMsg = `Held ${heldCount} note${heldCount === 1 ? '' : 's'} in Inbox — fix graduate_errors then retry`;
      } else {
        gradMsg = 'Inbox is clean (0 notes to graduate)';
      }
      showToast(gradMsg, 'success');
      if (typeof onReloadVault === 'function') {
        await onReloadVault();
      }
    } catch (err) {
      console.error('[AutoReiv UI] Failed to curate wiki inbox:', err);
      showToast('Failed to graduate wiki inbox (rule-based): ' + err.message, 'error');
    } finally {
      wikiCurateInboxBtn.disabled = false;
      wikiCurateInboxBtn.classList.remove('opacity-50', 'pointer-events-none');
    }
  });
}

/**
 * Sets up New Note modal controls, category toggling, template body prefill, and note creation.
 */
export function setupNewNoteModal({ onNoteCreated = null, onReloadVault = null } = {}) {
  const wikiNewNoteBtn = $('wikiNewNoteBtn');
  const wikiNewNoteModal = $('wikiNewNoteModal');
  const wikiNewNoteCloseBtn = $('wikiNewNoteCloseBtn');
  const wikiNewNoteCancelBtn = $('wikiNewNoteCancelBtn');
  const wikiNewNoteSubmitBtn = $('wikiNewNoteSubmitBtn');

  const newNoteTitleInput = $('newNoteTitleInput');
  const newNoteCategorySelect = $('newNoteCategorySelect');
  const newNoteTemplateSelect = $('newNoteTemplateSelect');
  const newNoteDomainGroup = $('newNoteDomainGroup');
  const newNoteDomainInput = $('newNoteDomainInput');
  const newNoteTopicInput = $('newNoteTopicInput');
  const newNoteTypeGroup = $('newNoteTypeGroup');
  const newNoteTypeSelect = $('newNoteTypeSelect');
  const newNoteTagsInput = $('newNoteTagsInput');
  const newNoteSummaryInput = $('newNoteSummaryInput');
  const newNoteBodyInput = $('newNoteBodyInput');

  if (wikiNewNoteBtn) {
    wikiNewNoteBtn.addEventListener('click', () => {
      if (wikiNewNoteModal) {
        wikiNewNoteModal.classList.remove('hidden');
        if (newNoteTitleInput) newNoteTitleInput.value = '';
        if (newNoteSummaryInput) newNoteSummaryInput.value = '';
        if (newNoteTagsInput) newNoteTagsInput.value = '';
        if (newNoteBodyInput) newNoteBodyInput.value = '';
        if (newNoteTemplateSelect) newNoteTemplateSelect.value = '';
        if (newNoteCategorySelect) {
          newNoteCategorySelect.value = 'inbox';
          newNoteCategorySelect.dispatchEvent(new Event('change'));
        }
        loadWikiTemplates();
        safeCreateIcons();
      }
    });
  }

  if (wikiNewNoteCloseBtn) {
    wikiNewNoteCloseBtn.addEventListener('click', () => wikiNewNoteModal?.classList.add('hidden'));
  }
  if (wikiNewNoteCancelBtn) {
    wikiNewNoteCancelBtn.addEventListener('click', () => wikiNewNoteModal?.classList.add('hidden'));
  }

  if (newNoteCategorySelect) {
    newNoteCategorySelect.addEventListener('change', () => {
      const val = newNoteCategorySelect.value;
      if (newNoteDomainGroup) newNoteDomainGroup.classList.toggle('hidden', val === 'resources');
      if (newNoteTypeGroup) newNoteTypeGroup.classList.toggle('hidden', val === 'inbox');
    });
  }

  if (newNoteTemplateSelect) {
    newNoteTemplateSelect.addEventListener('change', () => {
      const slug = newNoteTemplateSelect.value;
      if (!slug) return;
      const tmpl = cachedWikiTemplates.find((t) => t.slug === slug);
      if (tmpl && newNoteBodyInput) {
        const title = newNoteTitleInput?.value.trim() || 'Untitled Note';
        newNoteBodyInput.value = (tmpl.content || '').replace(/\${TITLE}/g, title);
        if (tmpl.description && newNoteSummaryInput && !newNoteSummaryInput.value) {
          newNoteSummaryInput.value = tmpl.description;
        }
      }
    });
  }

  if (wikiNewNoteSubmitBtn) {
    wikiNewNoteSubmitBtn.addEventListener('click', async () => {
      const title = newNoteTitleInput?.value.trim();
      if (!title) {
        showToast('Please enter a note title.', 'warning');
        return;
      }
      const category = newNoteCategorySelect?.value || 'inbox';
      const domain = newNoteDomainInput?.value.trim() || 'general';
      const topic = newNoteTopicInput?.value.trim() || 'general';
      const document_type = newNoteTypeSelect?.value || 'note';
      const tags = (newNoteTagsInput?.value || '')
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);
      const summary = newNoteSummaryInput?.value.trim() || '';
      const content = newNoteBodyInput?.value.trim() || '';
      const template = newNoteTemplateSelect?.value || undefined;

      try {
        const res = await fetch('/api/wiki/note', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title,
            category,
            domain,
            topic,
            document_type,
            tags,
            summary,
            content,
            template,
          }),
        });
        if (!res.ok) throw new Error('Failed to create note');
        const data = await res.json();
        if (wikiNewNoteModal) wikiNewNoteModal.classList.add('hidden');
        showToast(`Note '${title}' created successfully!`, 'success');
        if (typeof onReloadVault === 'function') {
          await onReloadVault();
        }
        if (data.path && typeof onNoteCreated === 'function') {
          await onNoteCreated(data.path);
        }
      } catch (err) {
        console.error('[AutoReiv UI] Failed to create note:', err);
        showToast('Failed to create note: ' + err.message, 'error');
      }
    });
  }
}
