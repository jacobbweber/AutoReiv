/**
 * Agent Studio: Lab Training Monitor Drawer Submodule [CARD-164, CARD-171, CARD-182, CARD-398]
 * Manages autonomous factory training runs, packet telemetry, live activity feeds,
 * stepper status visuals, artifact preview modal, and training retry modal integration.
 */

import { $, safeCreateIcons } from '../../dom.js';
import { escapeHtml } from '../../utils/formatters.js';
import { showToast } from '../../ui/toast.js';
import { copyToClipboard } from '../../utils/clipboard.js';

let currentLabJobData = null;
let labPollTimer = null;

export function getCurrentLabJobData() {
  return currentLabJobData;
}

export function setCurrentLabJobData(data) {
  currentLabJobData = data;
}

/** Build expected on-disk pack paths after promote (CARD-171). */
export function buildExpectedPackPaths(agentId, relativeFiles = []) {
  const root = `%LOCALAPPDATA%\\AutoReiv\\packs\\${agentId || 'agent'}`;
  return (relativeFiles || []).map((rel) => {
    const clean = String(rel || '').replace(/\//g, '\\').replace(/^\\+/, '');
    return `${root}\\${clean}`;
  });
}

/** Collect unique artifacts from factory packets (files_map + wiki_paths). */
export function collectPacketArtifacts(packets = []) {
  const out = [];
  const seen = new Set();
  for (const p of packets || []) {
    const payload = (p && p.payload) || {};
    const filesMap = payload.files_map || {};
    for (const [rel, content] of Object.entries(filesMap)) {
      const key = `file:${rel}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push({
        kind: 'file',
        path: rel,
        content: content == null ? '' : String(content),
        source: p.sender_role || 'packet',
      });
    }
    const wikiPaths = payload.wiki_paths || [];
    for (const wp of wikiPaths) {
      const key = `wiki:${wp}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push({
        kind: 'wiki',
        path: wp,
        content: '',
        source: p.sender_role || 'packet',
      });
    }
  }
  return out;
}

export function formatLabPacketFeedLines(packet) {
  const payload = (packet && packet.payload) || {};
  const msg = payload.message || payload.goal || '';
  const notes = (payload.critic_notes || '').trim();
  const passed = payload.passed;
  const lines = [];
  if (msg) lines.push(String(msg));
  const looksFailed =
    passed === false ||
    /FAILED/i.test(String(msg)) ||
    payload.terminal_fail === true;
  if (looksFailed) {
    const rinseKind = payload.rinse_kind || '';
    const fclass = payload.failure_class || '';
    if (rinseKind || fclass) {
      const bits = [];
      if (rinseKind) bits.push(`${rinseKind} rinse`);
      if (fclass) bits.push(fclass);
      lines.push(`Rinse: ${bits.join(' / ')}`);
    }
    if (notes) {
      const short = notes.length > 160 ? `${notes.slice(0, 157)}...` : notes;
      lines.push(`Reason: ${short}`);
    }
  }
  if (!lines.length && payload && typeof payload === 'object') {
    lines.push(JSON.stringify(payload));
  }
  return lines;
}

export function formatLabActivityFeedText(packets) {
  if (!packets || !Array.isArray(packets) || packets.length === 0) return '';
  const lines = [];
  packets.forEach((p) => {
    const timeStr = p.created_at ? new Date(p.created_at).toLocaleTimeString() : '';
    const role = (p.sender_role || 'system').toUpperCase();
    const feedLines = formatLabPacketFeedLines(p);
    feedLines.forEach((line) => {
      lines.push(`[${timeStr}] [${role}] ${line}`);
    });
  });
  return lines.join('\n');
}

export function populateTrainModalForRetry(jobData, elements = {}) {
  if (!jobData) return false;
  const job = jobData.job || jobData;
  const inputs = jobData.inputs || {};

  const agentId = inputs.target_agent_id || job.target_agent_id || '';
  const seedIntent = inputs.seed_intent || job.seed_intent || '';
  const objectives = inputs.objectives || job.objectives || [];
  const deliverableType = inputs.deliverable_type || 'auto';
  const constraints = inputs.constraints || '';
  const prerequisites = inputs.prerequisites || '';
  const referenceDocs = inputs.reference_docs || '';
  const targetLocation = inputs.target_directory || '';

  const modal = elements.modal || $('trainAgentHandshakeModal');
  if (modal) {
    modal.dataset.agentId = agentId;
  }

  const targetSelect = elements.trainAgentTargetSelect || $('trainAgentTargetSelect');
  if (targetSelect) {
    targetSelect.value = agentId || '__new__';
  }

  const nameInput = elements.nameInput || $('trainAgentNameInput');
  const nameGroup = elements.nameGroup || $('trainAgentNameGroup');
  if (nameGroup && nameGroup.classList) {
    if (!agentId || agentId === '__new__') {
      nameGroup.classList.remove('hidden');
    } else {
      nameGroup.classList.add('hidden');
    }
  }
  if (nameInput) nameInput.value = agentId;

  const targetLoc = elements.targetLocation || $('trainTargetLocation');
  if (targetLoc) targetLoc.value = targetLocation;

  const seedObj = elements.seedObjectives || $('trainSeedObjectives');
  if (seedObj) {
    if (objectives && objectives.length > 0) {
      seedObj.value = objectives.join('\n');
    } else {
      seedObj.value = seedIntent;
    }
  }

  const intentInput = elements.seedIntentInput || $('trainSeedIntentInput');
  if (intentInput) {
    intentInput.value = seedIntent || '';
  }

  const promptInput = elements.promptInput || $('promptInput');
  if (promptInput && seedIntent) {
    promptInput.value = seedIntent;
  }

  const deliverableSelect = elements.deliverableType || $('trainDeliverableType');
  if (deliverableSelect) deliverableSelect.value = deliverableType;

  const constraintsInput = elements.constraints || $('trainConstraintsInput');
  if (constraintsInput) constraintsInput.value = constraints;

  const prereqsInput = elements.prerequisites || $('trainPrerequisitesInput');
  if (prereqsInput) prereqsInput.value = prerequisites;

  const refDocsInput = elements.referenceDocs || $('trainReferenceDocsInput');
  if (refDocsInput) refDocsInput.value = referenceDocs;

  const advContent = elements.advancedContent || $('trainAdvancedReqsContent');
  const advChevron = elements.advancedChevron || $('trainAdvancedChevron');
  const hasAdvanced = Boolean(constraints || prerequisites || referenceDocs);
  if (advContent) {
    advContent.classList.toggle('hidden', !hasAdvanced);
    if (advChevron) advChevron.classList.toggle('rotate-180', hasAdvanced);
  }

  return true;
}

export function setStepVisual(el, state) {
  if (!el) return;
  el.classList.remove('border-emerald-500', 'bg-emerald-950/40', 'border-brand-500', 'bg-brand-950/40', 'border-slate-800', 'bg-slate-950/50');
  const num = el.querySelector('.step-num');
  const name = el.querySelector('.step-name');
  const icon = el.querySelector('.step-icon');

  if (state === 'done') {
    el.classList.add('border-emerald-500', 'bg-emerald-950/40');
    if (num) num.className = 'step-num text-[10px] font-mono text-emerald-400';
    if (name) name.className = 'step-name font-semibold text-emerald-300';
    if (icon) icon.className = 'step-icon text-emerald-400';
  } else if (state === 'active') {
    el.classList.add('border-brand-500', 'bg-brand-950/40');
    if (num) num.className = 'step-num text-[10px] font-mono text-brand-400';
    if (name) name.className = 'step-name font-semibold text-brand-300';
    if (icon) icon.className = 'step-icon text-brand-400';
  } else {
    el.classList.add('border-slate-800', 'bg-slate-950/50');
    if (num) num.className = 'step-num text-[10px] font-mono text-slate-500';
    if (name) name.className = 'step-name font-semibold text-slate-400';
    if (icon) icon.className = 'step-icon text-slate-500';
  }
}

export async function updateLabRunsBadge(badgeEl = null) {
  const el = badgeEl || $('forgeLabRunsBadge');
  try {
    const res = await fetch('/api/agent_training_factory/jobs');
    if (!res.ok) return;
    const data = await res.json();
    const jobs = data.jobs || [];
    const activeJobs = jobs.filter((j) => ['queued', 'running', 'waiting_approval'].includes(j.status));
    if (el) {
      if (activeJobs.length > 0) {
        el.textContent = String(activeJobs.length);
        el.classList.remove('hidden');
      } else {
        el.classList.add('hidden');
      }
    }
  } catch {
    // quiet fail
  }
}

export function openLabArtifactPreview(art, agentId) {
  const modal = $('labArtifactPreviewModal');
  const titleEl = $('labArtifactPreviewTitle');
  const bodyEl = $('labArtifactPreviewBody');
  const pathsEl = $('labArtifactPreviewPaths');
  const noteEl = $('labArtifactPreviewNote');
  if (!modal || !art) return;
  if (titleEl) titleEl.textContent = art.path || 'Artifact';
  if (bodyEl) {
    const content = art.content || '(No inline content in packet; wiki path listed for human review.)';
    bodyEl.textContent = content;
  }
  if (noteEl) {
    noteEl.textContent = art.kind === 'wiki'
      ? 'Pre-promote: Wiki path from Grounding packet (may already exist under the Wiki vault).'
      : 'Pre-promote: content is from the job packet (not yet written under packs/).';
  }
  if (pathsEl) {
    const expected = art.kind === 'file'
      ? buildExpectedPackPaths(agentId, [art.path])
      : [art.path];
    pathsEl.innerHTML = '';
    expected.forEach((p) => {
      const li = document.createElement('li');
      li.className = 'font-mono text-[11px] text-emerald-300 break-all';
      li.setAttribute('data-testid', 'lab-artifact-expected-path');
      li.textContent = p;
      pathsEl.appendChild(li);
    });
  }
  modal.classList.remove('hidden');
  safeCreateIcons();
}

export function closeLabArtifactPreview() {
  const modal = $('labArtifactPreviewModal');
  if (modal) modal.classList.add('hidden');
}

export async function loadLabJobDetails(jobId) {
  if (!jobId) return;
  const labRetryJobBtn = $('labRetryJobBtn');
  const labMonitorJobBadge = $('labMonitorJobBadge');
  const labJobStatusPill = $('labJobStatusPill');
  const labHitlCard = $('labHitlCard');
  const labHitlToolsList = $('labHitlToolsList');
  const labPacketsCount = $('labPacketsCount');
  const labPacketsFeed = $('labPacketsFeed');
  const labArtifactPills = $('labArtifactPills');

  try {
    const res = await fetch(`/api/agent_training_factory/jobs/${encodeURIComponent(jobId)}`);
    if (!res.ok) return;
    const data = await res.json();
    currentLabJobData = data;
    if (labRetryJobBtn) {
      labRetryJobBtn.classList.remove('hidden');
    }
    const job = data.job;
    const packets = data.packets || [];
    const evals = data.eval_runs || [];

    if (labMonitorJobBadge) {
      labMonitorJobBadge.textContent = `${job.target_agent_id} (${job.id})`;
    }

    // Status Pill
    if (labJobStatusPill) {
      const dot = labJobStatusPill.querySelector('span:first-child');
      const txt = labJobStatusPill.querySelector('.status-text');
      if (txt) txt.textContent = job.status.toUpperCase();
      labJobStatusPill.className = 'px-2.5 py-1 rounded-full text-xs font-semibold border flex items-center space-x-1.5';
      if (dot) dot.className = 'w-2 h-2 rounded-full';

      if (job.status === 'done') {
        labJobStatusPill.classList.add('border-emerald-500/50', 'bg-emerald-950/40', 'text-emerald-300');
        if (dot) dot.classList.add('bg-emerald-400');
      } else if (job.status === 'waiting_approval') {
        labJobStatusPill.classList.add('border-amber-500/50', 'bg-amber-950/40', 'text-amber-300');
        if (dot) dot.classList.add('bg-amber-400');
      } else if (job.status === 'running') {
        labJobStatusPill.classList.add('border-brand-500/50', 'bg-brand-950/40', 'text-brand-300');
        if (dot) dot.classList.add('bg-brand-400');
      } else if (job.status === 'failed') {
        labJobStatusPill.classList.add('border-rose-500/50', 'bg-rose-950/40', 'text-rose-300');
        if (dot) dot.classList.add('bg-rose-400');
      } else {
        labJobStatusPill.classList.add('border-slate-700', 'bg-slate-800', 'text-slate-300');
        if (dot) dot.classList.add('bg-slate-400');
      }
    }

    // Stepper logic - Agent Training Factory phases (CARD-171)
    const node = job.current_node_id;
    const status = job.status;
    const phaseOrder = [
      'intent_distill',
      'ground',
      'blueprint',
      'author',
      'scenario_verify',
      'verify',
      'optimize',
      'promote',
    ];
    const legacyMap = {
      socratic_handshake: 'intent_distill',
      discovery_probe: 'ground',
      architecture_blueprint: 'blueprint',
      attempt_node: 'author',
      conduct_node: 'author',
      coder_node: 'author',
      sandbox_battery_node: 'verify',
      critic_signoff_node: 'optimize',
      hitl_deploy_gate_node: 'promote',
      pack_finalized_node: 'done',
    };
    const phase = legacyMap[node] || node;
    let activeIdx = phaseOrder.indexOf(phase);
    if (phase === 'done' || status === 'done') activeIdx = phaseOrder.length;
    if (status === 'waiting_approval') activeIdx = phaseOrder.indexOf('promote');

    const stepEls = [
      'labStep1',
      'labStep2',
      'labStep3',
      'labStep4',
      'labStep5',
      'labStep6',
      'labStep7',
      'labStep8',
    ];
    stepEls.forEach((id, idx) => {
      const el = $(id);
      if (!el) return;
      if (activeIdx < 0) {
        setStepVisual(el, 'idle');
      } else if (idx < activeIdx) {
        setStepVisual(el, 'done');
      } else if (idx === activeIdx) {
        setStepVisual(el, 'active');
      } else {
        setStepVisual(el, 'idle');
      }
    });

    // HITL Card
    if (labHitlCard) {
      if (status === 'waiting_approval') {
        labHitlCard.classList.remove('hidden');
        if (labHitlToolsList) {
          labHitlToolsList.innerHTML = '';
          const toolNames = new Set();
          packets.forEach((p) => {
            if (p.payload && p.payload.tool_name) toolNames.add(p.payload.tool_name);
            if (p.payload && p.payload.authored_files) {
              p.payload.authored_files.forEach((f) => toolNames.add(f));
            }
          });
          evals.forEach((e) => toolNames.add(e.tool_name));
          if (toolNames.size === 0) toolNames.add(`manage_${job.target_agent_id.replace(/-/g, '_')}`);

          toolNames.forEach((t) => {
            const chip = document.createElement('span');
            chip.className = 'px-2 py-0.5 rounded-lg bg-emerald-900/40 border border-emerald-700/50 text-emerald-300 font-mono text-[11px]';
            chip.textContent = t;
            labHitlToolsList.appendChild(chip);
          });
        }
      } else {
        labHitlCard.classList.add('hidden');
      }
    }

    // Live Activity Feed
    if (labPacketsCount) {
      labPacketsCount.textContent = `${packets.length} packet${packets.length === 1 ? '' : 's'}`;
    }
    if (labPacketsFeed) {
      if (packets.length === 0) {
        labPacketsFeed.innerHTML = '<div class="text-slate-500 italic py-2">No activity recorded for this job yet.</div>';
      } else {
        labPacketsFeed.innerHTML = '';
        packets.forEach((p) => {
          const timeStr = p.created_at ? new Date(p.created_at).toLocaleTimeString() : '';
          const role = p.sender_role || 'system';
          const feedLines = formatLabPacketFeedLines(p);
          let roleColor = 'text-slate-400';
          if (role === 'intent_distill') roleColor = 'text-sky-400';
          else if (role === 'ground' || role === 'inspector') roleColor = 'text-cyan-400';
          else if (role === 'blueprint' || role === 'conductor') roleColor = 'text-brand-400';
          else if (role === 'author' || role === 'coder') roleColor = 'text-amber-400';
          else if (role === 'scenario_verify') roleColor = 'text-fuchsia-400';
          else if (role === 'verify' || role === 'sandbox_runner') roleColor = 'text-purple-400';
          else if (role === 'optimize' || role === 'critic') roleColor = 'text-emerald-400';
          else if (role === 'promote') roleColor = 'text-rose-400';

          feedLines.forEach((line, lineIdx) => {
            const row = document.createElement('div');
            row.className = 'flex items-start space-x-2 py-0.5';
            const bodyClass = lineIdx === 0 ? 'text-slate-200' : 'text-rose-300 text-[11px]';
            row.innerHTML = `
            <span class="text-slate-500 text-[10px] flex-shrink-0">[${escapeHtml(lineIdx === 0 ? timeStr : '')}]</span>
            <span class="${roleColor} font-semibold flex-shrink-0">[${escapeHtml(lineIdx === 0 ? role.toUpperCase() : '')}]</span>
            <span class="${bodyClass}">${escapeHtml(line)}</span>
          `;
            labPacketsFeed.appendChild(row);
          });
        });
        labPacketsFeed.scrollTop = labPacketsFeed.scrollHeight;
      }
    }

    // Artifact review pills (CARD-171)
    if (labArtifactPills) {
      labArtifactPills.innerHTML = '';
      const artifacts = collectPacketArtifacts(packets);
      if (artifacts.length === 0) {
        labArtifactPills.innerHTML = '<span class="text-slate-500 text-[11px] italic">No authored artifacts yet.</span>';
      } else {
        artifacts.forEach((art, idx) => {
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'lab-artifact-pill px-2 py-0.5 rounded-lg bg-slate-800 hover:bg-brand-900/40 border border-slate-700 hover:border-brand-500/50 text-slate-200 hover:text-brand-200 font-mono text-[11px] transition';
          btn.setAttribute('data-testid', `lab-artifact-pill-${idx}`);
          btn.setAttribute('data-artifact-path', art.path);
          btn.title = 'Preview artifact from job packet';
          btn.textContent = art.path;
          btn.addEventListener('click', () => openLabArtifactPreview(art, job.target_agent_id));
          labArtifactPills.appendChild(btn);
        });
      }
    }

    safeCreateIcons();
  } catch (e) {
    console.error('Failed to load lab job details:', e);
  }
}

export async function openLabMonitorDrawer(preferredJobId = null) {
  const labMonitorDrawer = $('labMonitorDrawer');
  const labJobSelect = $('labJobSelect');
  const labRetryJobBtn = $('labRetryJobBtn');
  if (!labMonitorDrawer) return;
  labMonitorDrawer.classList.remove('hidden');

  try {
    const res = await fetch('/api/agent_training_factory/jobs');
    if (!res.ok) throw new Error('Failed to list factory jobs');
    const data = await res.json();
    const jobs = data.jobs || [];

    if (labJobSelect) {
      labJobSelect.innerHTML = '';
      if (jobs.length === 0) {
        const opt = document.createElement('option');
        opt.value = '';
        opt.textContent = 'No training runs found';
        labJobSelect.appendChild(opt);
        if (labRetryJobBtn) {
          labRetryJobBtn.classList.add('hidden');
        }
        currentLabJobData = null;
      } else {
        jobs.forEach((j) => {
          const opt = document.createElement('option');
          opt.value = j.id;
          opt.textContent = `[${j.status.toUpperCase()}] ${j.target_agent_id} (${j.id.slice(0, 10)})`;
          labJobSelect.appendChild(opt);
        });

        const activeJob = jobs.find((j) => j.status === 'running' || j.status === 'waiting_approval');
        const targetJobId = preferredJobId || (activeJob ? activeJob.id : jobs[0].id);
        labJobSelect.value = targetJobId;
        await loadLabJobDetails(targetJobId);
      }
    }

    if (labPollTimer) clearInterval(labPollTimer);
    labPollTimer = setInterval(() => {
      if (labJobSelect && labJobSelect.value) {
        loadLabJobDetails(labJobSelect.value);
        updateLabRunsBadge();
      }
    }, 2500);

    safeCreateIcons();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

export function closeLabMonitorDrawer() {
  const labMonitorDrawer = $('labMonitorDrawer');
  if (labMonitorDrawer) labMonitorDrawer.classList.add('hidden');
  if (labPollTimer) {
    clearInterval(labPollTimer);
    labPollTimer = null;
  }
}

/**
 * Sets up and manages the Lab Monitor Drawer controller.
 */
export function setupLabMonitor({
  callbacks = {},
  onLoadAgent = null,
} = {}) {
  const forgeLabMonitorBtn = $('forgeLabMonitorBtn');
  const closeLabMonitorDrawerBtn = $('closeLabMonitorDrawerBtn');
  const closeLabMonitorDrawerFooterBtn = $('closeLabMonitorDrawerFooterBtn');
  const refreshLabMonitorBtn = $('refreshLabMonitorBtn');
  const labJobSelect = $('labJobSelect');
  const labApproveDeployBtn = $('labApproveDeployBtn');
  const labRejectDeployBtn = $('labRejectDeployBtn');
  const labCopyFeedBtn = $('labCopyFeedBtn');
  const labCopyFeedText = $('labCopyFeedText');
  const labRetryJobBtn = $('labRetryJobBtn');
  const forgeIdInput = $('forgeIdInput');

  if (typeof window !== 'undefined') {
    window.openLabMonitorDrawer = openLabMonitorDrawer;
    window.closeLabMonitorDrawer = closeLabMonitorDrawer;
  }

  if (forgeLabMonitorBtn) {
    forgeLabMonitorBtn.addEventListener('click', () => {
      const currentAgentId = forgeIdInput ? forgeIdInput.value.trim() : '';
      if (typeof callbacks.openFactoryStudio === 'function') {
        callbacks.openFactoryStudio(currentAgentId);
      } else if (typeof window !== 'undefined' && typeof window.openFactoryStudioForAgent === 'function') {
        window.openFactoryStudioForAgent(currentAgentId);
      } else {
        openLabMonitorDrawer();
      }
    });
  }

  if (closeLabMonitorDrawerBtn) {
    closeLabMonitorDrawerBtn.addEventListener('click', closeLabMonitorDrawer);
  }

  if (closeLabMonitorDrawerFooterBtn) {
    closeLabMonitorDrawerFooterBtn.addEventListener('click', closeLabMonitorDrawer);
  }

  if (refreshLabMonitorBtn) {
    refreshLabMonitorBtn.addEventListener('click', () => {
      if (labJobSelect && labJobSelect.value) {
        loadLabJobDetails(labJobSelect.value);
        updateLabRunsBadge();
      }
    });
  }

  if (labJobSelect) {
    labJobSelect.addEventListener('change', () => {
      if (labJobSelect.value) {
        loadLabJobDetails(labJobSelect.value);
      }
    });
  }

  if (labApproveDeployBtn) {
    labApproveDeployBtn.addEventListener('click', async () => {
      const jobId = labJobSelect ? labJobSelect.value : null;
      if (!jobId) return;
      labApproveDeployBtn.disabled = true;
      labApproveDeployBtn.textContent = 'Deploying...';
      try {
        const res = await fetch(`/api/agent_training_factory/jobs/${encodeURIComponent(jobId)}/promote`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision: 'approved' }),
        });
        if (!res.ok) throw new Error('Promotion deployment failed');
        const data = await res.json();
        showToast(`Successfully deployed ${data.agent_id} pack to live fleet!`, 'success');
        if (data.agent_id && typeof onLoadAgent === 'function') {
          await onLoadAgent(data.agent_id);
        }
        if (typeof callbacks.onReloadAgents === 'function') {
          callbacks.onReloadAgents(data.agent_id);
        }
        if (typeof callbacks.onAgentSaved === 'function') {
          callbacks.onAgentSaved();
        }
        await loadLabJobDetails(jobId);
        await updateLabRunsBadge();
      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        labApproveDeployBtn.disabled = false;
        labApproveDeployBtn.textContent = 'Approve & Deploy to Fleet';
      }
    });
  }

  if (labRejectDeployBtn) {
    labRejectDeployBtn.addEventListener('click', async () => {
      const jobId = labJobSelect ? labJobSelect.value : null;
      if (!jobId) return;
      try {
        const res = await fetch(`/api/agent_training_factory/jobs/${encodeURIComponent(jobId)}/promote`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision: 'rejected' }),
        });
        if (!res.ok) throw new Error('Rejection failed');
        showToast('Training run rejected and aborted.', 'info');
        await loadLabJobDetails(jobId);
        await updateLabRunsBadge();
      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }

  if (labCopyFeedBtn) {
    labCopyFeedBtn.addEventListener('click', async () => {
      const packets = currentLabJobData ? (currentLabJobData.packets || []) : [];
      if (packets.length === 0) {
        showToast('No activity feed logs to copy.', 'info');
        return;
      }
      const textToCopy = formatLabActivityFeedText(packets);
      try {
        await copyToClipboard(textToCopy);
        if (labCopyFeedText) {
          const originalText = labCopyFeedText.textContent;
          labCopyFeedText.textContent = 'Copied!';
          setTimeout(() => {
            if (labCopyFeedText) labCopyFeedText.textContent = originalText;
          }, 2000);
        }
        showToast('Activity feed copied to clipboard!', 'success');
      } catch (err) {
        console.error('Failed to copy feed:', err);
        showToast('Failed to copy feed to clipboard.', 'error');
      }
    });
  }

  if (labRetryJobBtn) {
    labRetryJobBtn.addEventListener('click', () => {
      if (!currentLabJobData) {
        showToast('No training run selected to retry.', 'warning');
        return;
      }
      closeLabMonitorDrawer();
      populateTrainModalForRetry(currentLabJobData);
      const modal = $('trainAgentHandshakeModal');
      if (modal) {
        modal.classList.remove('hidden');
        const modalTitle = $('trainAgentModalTitle');
        if (modalTitle) {
          const agentId = currentLabJobData?.job?.target_agent_id || currentLabJobData?.inputs?.target_agent_id || '';
          modalTitle.innerHTML = `
            <i data-lucide="rotate-ccw" class="w-4 h-4 text-emerald-400"></i>
            <span>Retry Training: ${escapeHtml(agentId || 'Specialist')}</span>
          `;
        }
        safeCreateIcons();
      }
    });
  }

  const closeLabArtifactPreviewBtn = $('closeLabArtifactPreviewBtn');
  const closeLabArtifactPreviewFooterBtn = $('closeLabArtifactPreviewFooterBtn');
  if (closeLabArtifactPreviewBtn) {
    closeLabArtifactPreviewBtn.addEventListener('click', closeLabArtifactPreview);
  }
  if (closeLabArtifactPreviewFooterBtn) {
    closeLabArtifactPreviewFooterBtn.addEventListener('click', closeLabArtifactPreview);
  }
  const labArtifactPreviewModal = $('labArtifactPreviewModal');
  if (labArtifactPreviewModal) {
    labArtifactPreviewModal.addEventListener('click', (e) => {
      if (e.target === labArtifactPreviewModal) closeLabArtifactPreview();
    });
  }

  return {
    openLabMonitorDrawer,
    closeLabMonitorDrawer,
    loadLabJobDetails,
    updateLabRunsBadge,
    openLabArtifactPreview,
    closeLabArtifactPreview,
  };
}
