/**
 * Chat Studio: Message & Artifact DOM Rendering Submodule [CARD-135, CARD-352, CARD-358, CARD-397]
 * Manages Markdown rendering, Mermaid diagrams, artifact reports, and message bubbles.
 */

import { $, safeCreateIcons } from '../../dom.js';
import { escapeHtml, formatBytes, formatJsonDeliverableToMarkdown } from '../../utils/formatters.js';
import { copyToClipboard } from '../../utils/clipboard.js';
import { renderAgentHandoffCardHtml } from './stream.js';

export * from './journey.js';

export async function renderMarkdown(targetEl, rawMarkdown, {
  onOpenArtifact = null,
  onRefreshWorkbench = null,
} = {}) {
  if (!targetEl) return;
  const formattedText = formatJsonDeliverableToMarkdown(rawMarkdown || '');
  if (!window.marked) {
    targetEl.innerHTML = `<pre class="whitespace-pre-wrap font-mono text-xs text-slate-200">${escapeHtml(formattedText)}</pre>`;
    return;
  }

  try {
    const parsedHtml = window.marked.parse(formattedText || '');
    targetEl.innerHTML = parsedHtml;

    const mermaidBlocks = targetEl.querySelectorAll(
      'pre code.language-mermaid, pre code.lang-mermaid, pre code.mermaid'
    );
    if (mermaidBlocks.length > 0 && window.mermaid) {
      for (let i = 0; i < mermaidBlocks.length; i++) {
        const codeEl = mermaidBlocks[i];
        const preEl = codeEl.closest('pre');
        const graphCode = codeEl.textContent.trim();
        const graphId = `mermaid-svg-${Date.now()}-${i}-${Math.floor(Math.random() * 10000)}`;

        try {
          const { svg } = await window.mermaid.render(graphId, graphCode);

          const wrapper = document.createElement('div');
          wrapper.className = 'mermaid-wrapper relative group my-4 overflow-x-auto';

          const containerDiv = document.createElement('div');
          containerDiv.className = 'mermaid flex justify-center py-2';
          containerDiv.innerHTML = svg;

          wrapper.appendChild(containerDiv);

          if (preEl && preEl.parentNode) {
            preEl.parentNode.replaceChild(wrapper, preEl);
          }
        } catch (mErr) {
          console.warn('[AutoReiv UI] Mermaid rendering error:', mErr);
          if (preEl) preEl.classList.add('border-amber-700/60');
        }
      }
    }

    // Convert artifact:// links to rich interactive cards [REQ-ART-005]
    const artifactLinks = targetEl.querySelectorAll('a[href^="artifact://"]');
    artifactLinks.forEach((a) => {
      const artId = a.getAttribute('href').replace('artifact://', '').trim();
      const linkText = a.textContent || artId;
      const card = document.createElement('div');
      card.className = 'my-2.5 p-3 rounded-xl bg-slate-900 border border-slate-800 hover:border-brand-500/50 transition flex items-center justify-between gap-3 shadow-sm group not-prose';
      card.innerHTML = `
        <div class="flex items-center space-x-2.5 min-w-0">
          <div class="w-8 h-8 rounded-lg bg-brand-600/30 border border-brand-500/50 flex items-center justify-center text-brand-400 shrink-0">
            <i data-lucide="file-text" class="w-4 h-4"></i>
          </div>
          <div class="truncate">
            <div class="text-xs font-bold text-white truncate">${escapeHtml(linkText)}</div>
            <div class="text-[10px] text-slate-400 font-mono">${escapeHtml(artId)} • Session Artifact</div>
          </div>
        </div>
        <button type="button" class="open-artifact-btn px-2.5 py-1.5 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition shrink-0 shadow-sm" data-artifact-id="${escapeHtml(artId)}">
          <i data-lucide="eye" class="w-3.5 h-3.5"></i>
          <span>View Full Report</span>
        </button>
      `;
      a.parentNode.replaceChild(card, a);
      card.querySelector('.open-artifact-btn')?.addEventListener('click', (e) => {
        e.stopPropagation();
        if (typeof onOpenArtifact === 'function') {
          onOpenArtifact(artId);
        } else {
          openArtifactModal(artId);
        }
      });
    });
    if (artifactLinks.length && typeof onRefreshWorkbench === 'function') {
      onRefreshWorkbench();
    }

    safeCreateIcons();
  } catch (err) {
    console.warn('[AutoReiv UI] Markdown rendering error:', err);
  }
}

export async function openArtifactModal(artifactId, { fetchFn = null, showToastFn = null } = {}) {
  if (!artifactId) return;
  const fn = fetchFn || (typeof window !== 'undefined' ? window.fetch : globalThis.fetch);
  const modal = $('artifactModal');
  const titleEl = $('artifactModalTitle');
  const subtitleEl = $('artifactModalSubtitle');
  const summaryBox = $('artifactSummaryBox');
  const bodyContent = $('artifactBodyContent');
  const itemCountBadge = $('artifactItemCountBadge');
  const statusBadge = $('artifactStatusBadge');
  const promoteBtn = $('artifactPromoteBtn');
  const pinBtn = $('artifactPinBtn');
  const pinText = $('artifactPinText');
  const deleteBtn = $('artifactDeleteBtn');
  const closeBtn = $('artifactCloseBtn');

  if (!modal) return;

  try {
    const res = await fn(`/api/artifacts/${encodeURIComponent(artifactId)}`);
    if (!res.ok) {
      if (typeof showToastFn === 'function') showToastFn('error', `Failed to load artifact ${artifactId}`);
      return;
    }
    const data = await res.json();
    const art = data.artifact;
    if (!art) return;

    if (titleEl) titleEl.textContent = art.title || 'Session Artifact Report';
    if (subtitleEl) subtitleEl.textContent = `ID: ${art.id} | Session: ${art.session_id}`;
    if (summaryBox) summaryBox.textContent = art.summary || 'No summary available.';
    if (bodyContent) bodyContent.textContent = art.content || '';
    if (itemCountBadge) itemCountBadge.textContent = `${art.item_count || 0} items scanned`;

    const updatePinUI = (isPinned) => {
      if (statusBadge) {
        if (isPinned) {
          statusBadge.textContent = 'Pinned (Permanent)';
          statusBadge.className = 'font-mono text-emerald-400 font-semibold';
        } else {
          statusBadge.textContent = 'Ephemeral (7-Day TTL)';
          statusBadge.className = 'font-mono text-amber-400';
        }
      }
      if (pinText) pinText.textContent = isPinned ? 'Unpin' : 'Pin';
    };

    updatePinUI(art.is_pinned);

    modal.classList.remove('hidden');
    modal.classList.add('flex');
    safeCreateIcons();

    const closeModal = () => {
      modal.classList.add('hidden');
      modal.classList.remove('flex');
    };

    if (closeBtn) closeBtn.onclick = closeModal;
    modal.onclick = (e) => {
      if (e.target === modal) closeModal();
    };

    if (pinBtn) {
      pinBtn.onclick = async () => {
        try {
          const nextPinned = !art.is_pinned;
          const pRes = await fn(`/api/artifacts/${encodeURIComponent(art.id)}/pin`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_pinned: nextPinned }),
          });
          if (pRes.ok) {
            art.is_pinned = nextPinned;
            updatePinUI(nextPinned);
            if (typeof showToastFn === 'function') {
              showToastFn('success', nextPinned ? 'Artifact pinned (immune to TTL cleanup)' : 'Artifact unpinned (7-day TTL active)');
            }
          }
        } catch (err) {
          if (typeof showToastFn === 'function') showToastFn('error', `Failed to toggle pin: ${err.message}`);
        }
      };
    }

    if (promoteBtn) {
      promoteBtn.onclick = async () => {
        try {
          const cleanSlug = `reports/${art.id.replace(/[^a-zA-Z0-9_-]/g, '_')}`;
          const promRes = await fn(`/api/artifacts/${encodeURIComponent(art.id)}/promote`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              wiki_slug: cleanSlug,
              title: art.title,
              category: 'reports',
            }),
          });
          if (promRes.ok) {
            if (typeof showToastFn === 'function') showToastFn('success', `Promoted artifact to Wiki Vault at '${cleanSlug}'!`);
            closeModal();
          } else {
            const errData = await promRes.json();
            if (typeof showToastFn === 'function') showToastFn('error', `Promotion failed: ${errData.detail || 'Unknown error'}`);
          }
        } catch (err) {
          if (typeof showToastFn === 'function') showToastFn('error', `Promotion failed: ${err.message}`);
        }
      };
    }

    if (deleteBtn) {
      deleteBtn.onclick = async () => {
        if (!confirm(`Are you sure you want to delete artifact ${art.id}?`)) return;
        try {
          const dRes = await fn(`/api/artifacts/${encodeURIComponent(art.id)}`, { method: 'DELETE' });
          if (dRes.ok) {
            if (typeof showToastFn === 'function') showToastFn('success', 'Artifact deleted.');
            closeModal();
          } else {
            if (typeof showToastFn === 'function') showToastFn('error', 'Deletion failed.');
          }
        } catch (err) {
          if (typeof showToastFn === 'function') showToastFn('error', `Deletion failed: ${err.message}`);
        }
      };
    }
  } catch (err) {
    if (typeof showToastFn === 'function') showToastFn('error', `Error opening artifact: ${err.message}`);
  }
}

export function renderSkillProposalCard(proposal, {
  container = null,
  activeAgentId = 'autoreiv',
  sessionId = null,
  showToastFn = null,
  onAdoptSuccess = null,
  onEscalate = null,
} = {}) {
  const targetContainer = container || $('messagesContainer');
  if (!targetContainer || !proposal) return null;

  const targetAgent = proposal.target_agent_id || activeAgentId || 'autoreiv';
  const skillName = proposal.skill_name || 'Synthesized Skill';
  const skillId = proposal.skill_id || skillName.toLowerCase().replace(/[^a-z0-9]+/g, '-');
  const slip = proposal.observed_slip || 'Operational friction detected during turn.';
  const remedy = proposal.remedy || 'Standardized procedure defined in runbook.';
  const runbookMarkdown = proposal.runbook_markdown || '';
  const messageId = proposal.message_id || null;
  const isAdopted = proposal.adoption_state === 'adopted';
  const needsTool = Boolean(proposal.needs_tool);

  const el = document.createElement('div');
  el.className = 'flex justify-start w-full my-3';
  el.dataset.messageId = messageId || '';
  el.dataset.skillId = skillId || '';
  el.dataset.targetAgentId = targetAgent || '';

  el.innerHTML = `
    <div class="skill-proposal-card max-w-2xl w-full rounded-2xl bg-amber-950/30 border border-amber-500/40 p-4 text-xs text-amber-100 space-y-3 shadow-md"
         data-skill-id="${escapeHtml(skillId)}"
         data-target-agent-id="${escapeHtml(targetAgent)}"
         data-runbook-markdown="${escapeHtml(runbookMarkdown)}"
         data-message-id="${escapeHtml(messageId || '')}"
         data-factory-escalation="${escapeHtml(JSON.stringify(proposal.factory_escalation || {}))}">
      <div class="flex items-center justify-between border-b border-amber-500/20 pb-2.5">
        <div class="flex items-center space-x-2">
          <span class="text-base">💡</span>
          <span class="font-bold text-amber-300 text-sm">Skill Proposal: ${escapeHtml(skillName)}</span>
          <span class="px-2 py-0.5 rounded-full bg-amber-500/20 border border-amber-500/40 text-[10px] text-amber-300 font-mono">In-Situ Distillation</span>
        </div>
        <span class="text-[11px] text-amber-400 font-mono">Target: <strong>${escapeHtml(targetAgent)}</strong></span>
      </div>

      <div class="space-y-1.5 bg-amber-950/40 p-2.5 rounded-xl border border-amber-900/40">
        <div><strong class="text-amber-300">Observed Slip:</strong> <span class="text-amber-200/90">${escapeHtml(slip)}</span></div>
        <div><strong class="text-amber-300">Remedy:</strong> <span class="text-amber-200/90">${escapeHtml(remedy)}</span></div>
      </div>

      <details class="group rounded-xl bg-slate-950/60 border border-amber-900/30 p-2 text-[11px]">
        <summary class="cursor-pointer font-medium text-amber-400 hover:text-amber-300 select-none list-none flex items-center justify-between">
          <span>View Raw Runbook (SKILL.md)</span>
          <span class="text-xs group-open:rotate-180 transition">&darr;</span>
        </summary>
        <pre class="mt-2 pt-2 border-t border-slate-800 font-mono text-[10px] text-slate-300 whitespace-pre-wrap max-h-60 overflow-y-auto leading-relaxed">${escapeHtml(runbookMarkdown)}</pre>
      </details>

      <div class="card-actions flex items-center justify-between gap-2 pt-1">
        ${isAdopted
          ? `
          <div class="p-2.5 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-xs text-emerald-300 font-medium flex items-center space-x-2 w-full">
            <span>✓</span>
            <span>Skill mounted to <strong>${escapeHtml(targetAgent)}</strong>. Active for your next message.</span>
          </div>
          `
          : `
          <div class="flex items-center space-x-2">
            <button type="button" class="btn-adopt-skill px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition shadow-sm flex items-center space-x-1.5">
              <span>✓</span>
              <span>Adopt Skill to ${escapeHtml(targetAgent)}</span>
            </button>
            ${needsTool
              ? `
              <button type="button" class="btn-escalate-factory px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition shadow-sm flex items-center space-x-1.5" title="Runbook requires missing tools — generate tool & agent pack in Factory Studio">
                <span>🚀</span>
                <span>Send to Factory Studio</span>
              </button>
              `
              : ''}
          </div>
          <button type="button" class="btn-dismiss-proposal text-slate-400 hover:text-slate-200 text-xs font-medium px-2 py-1 transition">
            Dismiss
          </button>
          `
        }
      </div>
    </div>
  `;

  targetContainer.appendChild(el);
  safeCreateIcons();

  const cardEl = el.querySelector('.skill-proposal-card');
  if (cardEl && !isAdopted) {
    const adoptBtn = cardEl.querySelector('.btn-adopt-skill');
    if (adoptBtn) {
      adoptBtn.addEventListener('click', async () => {
        adoptBtn.disabled = true;
        const originalText = adoptBtn.innerHTML;
        adoptBtn.innerHTML = '<span>⏳ Adopting...</span>';

        try {
          const res = await fetch('/api/skills/adopt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              target_agent_id: targetAgent,
              skill_id: skillId,
              runbook_markdown: runbookMarkdown,
              message_id: messageId,
              session_id: sessionId,
            }),
          });
          if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${res.status}`);
          }
          cardEl.dataset.adopted = 'true';
          const actionsContainer = cardEl.querySelector('.card-actions');
          if (actionsContainer) {
            actionsContainer.innerHTML = `
              <div class="p-2.5 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-xs text-emerald-300 font-medium flex items-center space-x-2">
                <span>✓</span>
                <span>Skill mounted to <strong>${escapeHtml(targetAgent)}</strong>. Active for your next message.</span>
              </div>
            `;
          }
          if (typeof showToastFn === 'function') {
            showToastFn(`Skill mounted to ${targetAgent}. Active for your next message.`, 'success');
          }
          if (typeof onAdoptSuccess === 'function') {
            await onAdoptSuccess(targetAgent);
          }
        } catch (err) {
          adoptBtn.disabled = false;
          adoptBtn.innerHTML = originalText;
          if (typeof showToastFn === 'function') {
            showToastFn(`Adoption failed: ${err.message}`, 'error');
          }
        }
      });
    }

    const escalateBtn = cardEl.querySelector('.btn-escalate-factory');
    if (escalateBtn && typeof onEscalate === 'function') {
      escalateBtn.addEventListener('click', () => {
        onEscalate(proposal.factory_escalation || {});
      });
    }

    const dismissBtn = cardEl.querySelector('.btn-dismiss-proposal');
    if (dismissBtn) {
      dismissBtn.addEventListener('click', () => {
        el.remove();
      });
    }
  }

  return el;
}


/** Thinking Process drawer HTML for durable assistant rows [CARD-415]. */
export function buildReasoningDrawerHtml(reasoning) {
  const text = (reasoning || '').trim();
  if (!text) return '';
  return `
    <div class="reasoning-drawer rounded-xl border border-amber-500/30 bg-amber-950/20 overflow-hidden text-xs mb-2" data-reasoning-drawer="true">
      <button type="button" class="reasoning-toggle flex items-center justify-between w-full px-3 py-2 bg-amber-900/20 text-amber-300 font-semibold cursor-pointer">
        <span class="flex items-center gap-1.5">
          <i data-lucide="brain" class="w-3.5 h-3.5"></i>
          <span>Thinking Process</span>
        </span>
        <span class="reasoning-indicator text-[10px] uppercase font-mono">Show</span>
      </button>
      <div class="reasoning-content hidden p-3 font-mono text-[11px] text-amber-100 whitespace-pre-wrap max-h-60 overflow-y-auto"></div>
    </div>
  `;
}

export function wireReasoningDrawer(rootEl, reasoning) {
  if (!rootEl) return;
  const drawer = rootEl.querySelector?.('.reasoning-drawer') || rootEl;
  const contentEl = drawer.querySelector?.('.reasoning-content');
  const toggle = drawer.querySelector?.('.reasoning-toggle');
  const indicator = drawer.querySelector?.('.reasoning-indicator');
  if (contentEl && reasoning) contentEl.textContent = reasoning;
  if (toggle && contentEl && indicator) {
    toggle.addEventListener('click', () => {
      const isHidden = contentEl.classList.toggle('hidden');
      indicator.textContent = isHidden ? 'Show' : 'Hide';
    });
  }
}

export function appendMessageBubble(role, content, options = null, extraOptions = {}) {
  const isEl = (el) => Boolean(el && ((typeof HTMLElement !== 'undefined' && el instanceof HTMLElement) || el.nodeType === 1));
  const messagesContainer = isEl(options) ? options : (extraOptions?.messagesContainer || options?.messagesContainer || null);
  if (!messagesContainer) return null;

  const actualOptions = isEl(options) ? (extraOptions || {}) : (options || {});
  const activeAgentTitle = extraOptions?.activeAgentTitle || actualOptions?.activeAgentTitle;
  const renderMarkdownFn = extraOptions?.renderMarkdownFn || actualOptions?.renderMarkdownFn || renderMarkdown;
  const openWorkbenchFn = extraOptions?.openWorkbenchFn || actualOptions?.openWorkbenchFn || null;
  const copyToClipboardFn = extraOptions?.copyToClipboardFn || actualOptions?.copyToClipboardFn || copyToClipboard;
  const exportMessageToWikiFn = extraOptions?.exportMessageToWikiFn || actualOptions?.exportMessageToWikiFn || null;
  const onTeachAgent = extraOptions?.onTeachAgent || actualOptions?.onTeachAgent || null;

  const isUser = (role || '').toLowerCase() === 'user';
  const bubble = document.createElement('div');
  bubble.className = `flex ${isUser ? 'justify-end' : 'justify-start'} w-full`;

  const copyBtnHtml = !isUser
    ? `
    <div class="mt-2 pt-2 border-t border-white/10 flex flex-wrap gap-1.5 items-center">
      <button class="msg-teach-agent-btn flex items-center space-x-1.5 px-2 py-0.5 rounded-md bg-amber-950/60 hover:bg-amber-900/80 text-amber-300 border border-amber-800/50 transition shadow-sm" data-message-id="${escapeHtml(actualOptions?.messageId || '')}" data-content="${escapeHtml(content)}" title="Teach agent a runbook skill from this turn [CARD-352]">
        <i data-lucide="lightbulb" class="w-3 h-3 text-amber-400"></i>
        <span>Teach Agent</span>
      </button>
      <button class="workbench-msg-btn flex items-center space-x-1.5 px-2 py-0.5 rounded-md bg-slate-800/70 hover:bg-slate-700/80 text-brand-300 border border-slate-700/50 transition" data-content="${escapeHtml(content)}" title="Open message artifact in Dual-Pane Workbench">
        <i data-lucide="layout" class="w-3 h-3"></i>
        <span>Workbench</span>
      </button>
      <button class="copy-msg-btn flex items-center space-x-1.5 px-2 py-0.5 rounded-md bg-slate-800/70 hover:bg-slate-700/80 text-slate-300 border border-slate-700/50 transition" data-content="${escapeHtml(content)}">
        <i data-lucide="copy" class="w-3 h-3"></i>
        <span>Copy</span>
      </button>
      <button class="wiki-msg-btn flex items-center space-x-1.5 px-2 py-0.5 rounded-md bg-indigo-950/60 hover:bg-indigo-900/80 text-indigo-300 border border-indigo-800/50 transition" data-content="${escapeHtml(content)}">
        <i data-lucide="book-open" class="w-3 h-3"></i>
        <span>Save to Wiki</span>
      </button>
    </div>
  `
    : '';

  let attachmentsHtml = '';
  const attachments = (actualOptions && actualOptions.attachments) || [];
  if (Array.isArray(attachments) && attachments.length > 0) {
    attachmentsHtml = `
      <div class="attachments-grid flex flex-wrap gap-2 mt-2 pt-2 border-t border-white/20">
        ${attachments
          .map((att) => {
            const isImg = att.content_type?.startsWith('image/') || /\.(png|jpe?g|gif|webp|svg)$/i.test(att.filename || '');
            if (isImg && att.url) {
              return `
                <a href="${escapeHtml(att.url)}" target="_blank" rel="noopener noreferrer" class="block rounded-lg overflow-hidden border border-white/30 hover:opacity-90 transition">
                  <img src="${escapeHtml(att.url)}" alt="${escapeHtml(att.filename)}" class="max-w-[140px] max-h-[100px] object-cover rounded-md">
                </a>
              `;
            }
            return `
              <a href="${escapeHtml(att.url || '#')}" target="_blank" rel="noopener noreferrer" class="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-black/20 hover:bg-black/40 border border-white/30 text-xs text-white transition">
                <span>📄</span>
                <span class="font-medium truncate max-w-[120px]">${escapeHtml(att.filename || 'file')}</span>
                <span class="text-[10px] opacity-80">(${formatBytes(att.size_bytes || 0)})</span>
              </a>
            `;
          })
          .join('')}
      </div>
    `;
  }

  const reasoningText = !isUser
    ? (actualOptions?.reasoning || extraOptions?.reasoning || '')
    : '';
  const reasoningHtml = !isUser ? buildReasoningDrawerHtml(reasoningText) : '';

  bubble.innerHTML = `
    <div class="${
      isUser
        ? 'max-w-3xl rounded-2xl p-3.5 md:p-4 shadow-md bg-brand-600 text-white rounded-br-sm border border-brand-500/40'
        : 'max-w-4xl w-full rounded-2xl p-4 shadow-md bg-slate-900/90 border border-slate-800/80 text-slate-100 rounded-bl-sm'
    }">
      <div class="text-xs font-bold uppercase tracking-wider mb-1 opacity-70">
        ${isUser ? 'You' : escapeHtml(activeAgentTitle ? activeAgentTitle.textContent : 'Agent')}
      </div>
      ${reasoningHtml}
      <div class="msg-body prose prose-invert text-sm break-words leading-relaxed">
      </div>
      ${attachmentsHtml}
      ${copyBtnHtml}
    </div>
  `;

  messagesContainer.appendChild(bubble);
  if (reasoningText) {
    wireReasoningDrawer(bubble, reasoningText);
  }
  const bodyEl = bubble.querySelector('.msg-body');
  if (typeof renderMarkdownFn === 'function') {
    renderMarkdownFn(bodyEl, content || '');
  }

  bubble.querySelectorAll('.msg-teach-agent-btn').forEach((b) => {
    b.addEventListener('click', () => {
      if (typeof onTeachAgent === 'function') {
        onTeachAgent({
          messageId: b.getAttribute('data-message-id') || null,
          content: b.getAttribute('data-content') || '',
        });
      }
    });
  });

  bubble.querySelectorAll('.workbench-msg-btn').forEach((b) => {
    b.addEventListener('click', () => {
      if (typeof openWorkbenchFn === 'function') {
        openWorkbenchFn({
          title: `${activeAgentTitle ? activeAgentTitle.textContent : 'Agent'} Output`,
          meta: 'Turn Artifact',
          content: b.dataset.content || '',
        });
      }
    });
  });

  bubble.querySelectorAll('.copy-msg-btn').forEach((b) => {
    b.addEventListener('click', () => {
      if (typeof copyToClipboardFn === 'function') {
        copyToClipboardFn(b.dataset.content || '');
      }
    });
  });

  bubble.querySelectorAll('.wiki-msg-btn').forEach((b) => {
    b.addEventListener('click', () => {
      if (typeof exportMessageToWikiFn === 'function') {
        exportMessageToWikiFn(b.dataset.content || '');
      }
    });
  });

  return bubble;
}

export function renderMessageItem(msg, _idx, _allMessages, {
  messagesContainer,
  activeAgentTitle,
  appendMessageBubbleFn = appendMessageBubble,
  renderSkillProposalCardFn = renderSkillProposalCard,
  renderMarkdownFn = renderMarkdown,
  openWorkbenchFn = null,
  exportMessageToWikiFn = null,
  onTeachAgent = null,
} = {}) {
  if (!messagesContainer || !msg) return;

  const role = (msg.role || '').toLowerCase();

  // 1. User Message
  if (role === 'user') {
    if (msg.content && msg.content.trim()) {
      appendMessageBubbleFn('user', msg.content, null, {
        messagesContainer,
        activeAgentTitle,
        renderMarkdownFn,
        openWorkbenchFn,
        exportMessageToWikiFn,
        onTeachAgent,
      });
    }
    return;
  }

  // 2. Tool Execution Result
  if (role === 'tool') {
    const isDelegation = msg.name === 'handoff_to_agent';
    if (isDelegation) {
      let data;
      try {
        data = JSON.parse(msg.content);
      } catch {
        data = { status: 'success', output: msg.content };
      }

      const isOk = data.status === 'success' || !data.error;
      const recipient = data.recipient_agent_id || data.recipient || 'Specialist Agent';
      const recipientName = recipient.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
      const el = document.createElement('div');
      el.className = 'flex justify-start w-full my-1.5';
      el.innerHTML = `
        <div class="max-w-2xl w-full rounded-xl bg-indigo-950/40 border border-indigo-500/30 p-3 text-xs text-indigo-200 space-y-1.5 shadow-sm">
          <div class="flex items-center justify-between font-semibold ${isOk ? 'text-indigo-300' : 'text-rose-300'}">
            <span class="flex items-center space-x-1.5">
              <span>🤝</span>
              <span>Delegation to <strong>${escapeHtml(recipientName)}</strong> ${isOk ? 'Completed' : 'Failed'}</span>
            </span>
            <span class="font-mono text-[10px] ${isOk ? 'text-emerald-400' : 'text-rose-400'} font-bold">${isOk ? '✓ Done' : '✗ Error'}</span>
          </div>
          ${data.directive || data.task_intent ? `<div class="text-[11px] text-slate-300 font-mono bg-indigo-950/60 p-1.5 rounded border border-indigo-900/50">"${escapeHtml(data.directive || data.task_intent)}"</div>` : ''}
          ${data.error ? `<div class="text-[11px] text-rose-300 font-mono bg-rose-950/40 p-1.5 rounded border border-rose-900/50">${escapeHtml(data.error)}</div>` : ''}
        </div>
      `;
      messagesContainer.appendChild(el);
      return;
    }

    // Agent Pack Creation Result [CARD-197, REQ-FACT-048]
    if (msg.name === 'scaffold_agent_pack') {
      let data;
      try {
        data = typeof msg.content === 'object' ? msg.content : JSON.parse(msg.content);
      } catch {
        data = {};
      }
      if (data.success && data.agent_id) {
        const el = document.createElement('div');
        el.className = 'flex justify-start w-full my-1.5';
        el.innerHTML = renderAgentHandoffCardHtml({
          agentId: data.agent_id,
          agentName: data.name || data.agent_id,
          folder: data.folder || `packs/${data.agent_id}`,
        });
        messagesContainer.appendChild(el);
        return;
      }
    }

    // Generic Tool Execution Result (collapsible)
    const el = document.createElement('div');
    el.className = 'flex justify-start w-full my-1';
    el.innerHTML = `
      <details class="max-w-2xl w-full rounded-xl bg-slate-900/90 border border-slate-800 p-2.5 text-xs text-slate-300 group transition hover:border-slate-700 shadow-sm">
        <summary class="cursor-pointer font-medium flex items-center justify-between select-none list-none">
          <span class="flex items-center space-x-1.5">
            <span class="text-brand-400">🔧</span>
            <span>Tool: <strong class="text-slate-200">${escapeHtml(msg.name || 'tool')}</strong></span>
          </span>
          <span class="text-[10px] text-emerald-400 font-mono">✓ Complete</span>
        </summary>
        <div class="mt-2 pt-2 border-t border-slate-800/80 font-mono text-[11px] text-slate-400 whitespace-pre-wrap max-h-48 overflow-y-auto bg-slate-950/60 p-2 rounded">
          ${escapeHtml(msg.content)}
        </div>
      </details>
    `;
    messagesContainer.appendChild(el);
    return;
  }

  // 3. Assistant Message
  if (role === 'assistant') {
    const content = (msg.content || '').trim();
    // Allow reasoning-only rows to still surface Thinking drawer [CARD-415]
    if (!content && !(msg.reasoning || '').trim()) return;
    appendMessageBubbleFn('assistant', content || '', { messageId: msg.id || null, reasoning: msg.reasoning || '' }, {
      messagesContainer,
      activeAgentTitle,
      renderMarkdownFn,
      openWorkbenchFn,
      exportMessageToWikiFn,
      onTeachAgent,
    });
    return;
  }

  // 4. Skill Proposal Message [CARD-358, REQ-SKIL-016]
  if (role === 'skill_proposal') {
    let proposalData;
    try {
      proposalData = typeof msg.content === 'string' ? JSON.parse(msg.content) : msg.content;
    } catch {
      proposalData = null;
    }
    if (proposalData && typeof proposalData === 'object') {
      proposalData.message_id = msg.id || proposalData.message_id || null;
      renderSkillProposalCardFn(proposalData, { container: messagesContainer });
    }
    return;
  }

  // 5. Fallback for other message types
  if (msg.content && msg.content.trim()) {
    appendMessageBubbleFn(role, msg.content, null, {
      messagesContainer,
      activeAgentTitle,
      renderMarkdownFn,
      openWorkbenchFn,
      exportMessageToWikiFn,
      onTeachAgent,
    });
  }
}

export function renderMessages(opts = {}, legacyContainer, legacyOpts = {}) {
  const messagesContainer = opts && typeof opts === 'object' && !Array.isArray(opts) ? opts.messagesContainer : legacyContainer;
  const messages = opts && typeof opts === 'object' && !Array.isArray(opts) ? opts.messages : opts;
  const config = opts && typeof opts === 'object' && !Array.isArray(opts) ? opts : (legacyOpts || {});

  if (!messagesContainer) return;
  if (config.isStreaming) return;
  messagesContainer.innerHTML = '';
  if (!Array.isArray(messages) || messages.length === 0) {
    const title = config.activeAgentTitle ? config.activeAgentTitle.textContent : 'Agent';
    messagesContainer.innerHTML = `
      <div class="text-center py-12 text-slate-400 space-y-2">
        <div class="w-12 h-12 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto text-brand-400">
          <i data-lucide="bot" class="w-6 h-6"></i>
        </div>
        <p class="text-sm font-medium">Start a new conversation with ${escapeHtml(title)}.</p>
      </div>
    `;
    safeCreateIcons();
    return;
  }

  const renderItem = config.renderMessageItemFn || renderMessageItem;
  messages.forEach((msg, idx) => {
    renderItem(msg, idx, messages, {
      messagesContainer,
      activeAgentTitle: config.activeAgentTitle,
      renderMarkdownFn: config.renderMarkdownFn || renderMarkdown,
      openWorkbenchFn: config.openWorkbenchFn,
      exportMessageToWikiFn: config.exportMessageToWikiFn,
      onTeachAgent: config.onTeachAgent,
    });
  });

  if (typeof config.maybeAutoscrollMessagesFn === 'function') {
    config.maybeAutoscrollMessagesFn();
  }
  safeCreateIcons();
}

export function setupMessagesContainerDelegation(messagesContainer, callbacks = {}) {
  if (!messagesContainer) return;
  messagesContainer.addEventListener('click', async (e) => {
    const launchFactoryBtn = e.target.closest('[data-action="launch-factory"]');
    if (launchFactoryBtn) {
      const agentId = launchFactoryBtn.getAttribute('data-agent-id');
      if (typeof callbacks.openFactoryStudio === 'function') {
        callbacks.openFactoryStudio(agentId);
      } else if (typeof window.openFactoryStudioForAgent === 'function') {
        window.openFactoryStudioForAgent(agentId);
      }
      return;
    }
    const openStudioBtn = e.target.closest('[data-action="open-studio"]');
    if (openStudioBtn) {
      const agentId = openStudioBtn.getAttribute('data-agent-id');
      if (typeof callbacks.openAgentForge === 'function') {
        callbacks.openAgentForge(agentId);
      } else if (typeof window.openForgeStudioForAgent === 'function') {
        window.openForgeStudioForAgent(agentId);
      }
      return;
    }
    const openLabBtn = e.target.closest('.open-lab-drawer-btn');
    if (openLabBtn) {
      const jobId = openLabBtn.getAttribute('data-job-id');
      if (typeof window.openLabMonitorDrawer === 'function') {
        window.openLabMonitorDrawer(jobId);
      } else {
        const labDrawer = $('labMonitorDrawer');
        if (labDrawer) {
          labDrawer.classList.remove('hidden');
          const jobSelect = $('labJobSelect');
          if (jobSelect && jobId) {
            jobSelect.value = jobId;
            jobSelect.dispatchEvent(new Event('change'));
          }
        }
      }
      return;
    }
    const approveBtn = e.target.closest('.approve-factory-btn');
    if (approveBtn) {
      const jobId = approveBtn.getAttribute('data-job-id');
      if (!jobId) return;
      approveBtn.disabled = true;
      approveBtn.textContent = 'Deploying...';
      try {
        const res = await fetch(`/api/agent_training_factory/jobs/${encodeURIComponent(jobId)}/promote`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || err.error || `HTTP ${res.status}`);
        }
        if (typeof callbacks.showToast === 'function') {
          callbacks.showToast('Agent Pack approved and deployed to platform!', 'success');
        }
        approveBtn.textContent = 'Deployed';
        approveBtn.classList.remove('bg-emerald-600', 'hover:bg-emerald-500');
        approveBtn.classList.add('bg-slate-700', 'cursor-default');
        if (typeof callbacks.loadAgents === 'function') await callbacks.loadAgents();
      } catch (err) {
        approveBtn.disabled = false;
        approveBtn.textContent = 'Approve & Deploy';
        if (typeof callbacks.showToast === 'function') {
          callbacks.showToast(`Promotion failed: ${err.message}`, 'error');
        }
      }
      return;
    }
    const rejectBtn = e.target.closest('.reject-factory-btn');
    if (rejectBtn) {
      const card = rejectBtn.closest('.factory-promotion-card');
      if (card) card.remove();
      return;
    }
  });
}
