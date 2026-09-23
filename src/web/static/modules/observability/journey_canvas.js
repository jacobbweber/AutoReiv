/**
 * Observability Journey Canvas Submodule [CARD-428].
 *
 * Implements:
 * 1. 4 Architectural Swimlanes (UI/Browser, API Gateway, Orchestrator ReAct Loop, Storage & Policy).
 * 2. Visual flow graph with dynamic bezier SVG connectors.
 * 3. Step timeline scrubber & autoplay controls.
 * 4. Synchronized Code Inspector (repository source snippet with active line highlight).
 * 5. Runtime State Transition badge & formatted Payload Inspector.
 */

import { $ } from '../dom.js';
import { escapeHtml } from '../utils/formatters.js';

const SWIMLANE_MAP = Object.freeze({
  ui: { id: 'journeyLaneUi', label: '1. UI / Browser', color: 'border-cyan-500/30' },
  api: { id: 'journeyLaneApi', label: '2. API Gateway (FastAPI)', color: 'border-indigo-500/30' },
  orchestrator: { id: 'journeyLaneOrchestrator', label: '3. Orchestrator State Machine (ReAct Loop)', color: 'border-purple-500/30' },
  storage: { id: 'journeyLaneStorage', label: '4. Storage & Policy', color: 'border-emerald-500/30' },
});

const SWIMLANE_ORDER = ['ui', 'api', 'orchestrator', 'storage'];

export function clampStepIndex(index, max) {
  const m = Math.max(1, Number(max) || 1);
  return Math.min(Math.max(1, Number(index) || 1), m);
}

export function calculateStepCoordinates(step, stepSpacing = 220) {
  const lane = String(step?.swimlane || 'ui').toLowerCase();
  const laneIndex = Math.max(0, SWIMLANE_ORDER.indexOf(lane));
  const idx = Math.max(1, Number(step?.step_index) || 1);
  return {
    laneIndex,
    x: (idx - 1) * stepSpacing + 20,
    lane,
  };
}

export function buildSvgConnectorPath(p1, p2) {
  const x1 = Math.round(p1.x);
  const y1 = Math.round(p1.y);
  const x2 = Math.round(p2.x);
  const y2 = Math.round(p2.y);
  const dx = (x2 - x1) * 0.5;
  return `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
}

export function formatStateTransitionBadge(transition) {
  const text = String(transition || 'IDLE').trim();
  const upper = text.toUpperCase();
  const isWarning = upper.includes('AWAITING') || upper.includes('APPROVAL') || upper.includes('PAUSED') || upper.includes('HITL');
  const isSuccess = upper.includes('COMPLETE') || upper.includes('IDLE') || upper.includes('DONE');
  return { text, isWarning, isSuccess };
}

export function initJourneyCanvas(_state, _callbacks = {}) {
  const scenarioSelect = $('journeyScenarioSelect');
  const prevBtn = $('journeyPrevStepBtn');
  const playBtn = $('journeyPlayPauseBtn');
  const nextBtn = $('journeyNextStepBtn');
  const scrubber = $('journeyStepScrubber');
  const stepBadge = $('journeyStepBadge');

  const nodesContainer = $('journeyNodesContainer');
  const svgOverlay = $('journeySvgOverlay');

  const inspectorFileBadge = $('journeyInspectorFileBadge');
  const inspectorIdeLink = $('journeyInspectorIdeLink');
  const inspectorStateBadge = $('journeyInspectorStateBadge');
  const codeLinesContainer = $('journeyCodeLines');
  const payloadCodeContainer = $('journeyPayloadCode');
  const copyPayloadBtn = $('journeyCopyPayloadBtn');

  let activeScenario = null;
  let currentStepIndex = 1;
  let isPlaying = false;
  let playInterval = null;
  const sourceCache = new Map();

  async function loadScenarios() {
    try {
      const res = await fetch('/api/observability/journey-canvas/scenarios');
      if (!res.ok) return;
      const scenarios = await res.json();
      if (!scenarioSelect) return;

      scenarioSelect.innerHTML = scenarios
        .map(
          (s) =>
            `<option value="${escapeHtml(s.id)}" ${s.default ? 'selected' : ''}>${escapeHtml(s.title)} (${s.step_count} steps)</option>`
        )
        .join('');

      const defaultScenario = scenarios.find((s) => s.default) || scenarios[0];
      if (defaultScenario) {
        await selectScenario(defaultScenario.id);
      }
    } catch (err) {
      console.error('[Journey Canvas] Failed to load scenarios:', err);
    }
  }

  async function selectScenario(scenarioId) {
    pause();
    try {
      const res = await fetch(`/api/observability/journey-canvas/scenarios/${encodeURIComponent(scenarioId)}`);
      if (!res.ok) return;
      activeScenario = await res.json();
      currentStepIndex = 1;

      if (scrubber) {
        scrubber.min = 1;
        scrubber.max = activeScenario.steps.length;
        scrubber.value = 1;
      }

      renderCanvas(activeScenario);
      await selectStep(1);
    } catch (err) {
      console.error('[Journey Canvas] Failed to select scenario:', err);
    }
  }

  function renderCanvas(scenario) {
    if (!nodesContainer) return;
    const steps = scenario.steps || [];

    // Clear existing nodes inside each swimlane
    SWIMLANE_ORDER.forEach((laneKey) => {
      const laneEl = $(SWIMLANE_MAP[laneKey].id);
      if (laneEl) {
        const laneTrack = laneEl.querySelector('.journey-lane-track');
        if (laneTrack) laneTrack.innerHTML = '';
      }
    });

    // Populate step nodes inside their designated swimlane
    steps.forEach((step) => {
      const laneKey = String(step.swimlane || 'ui').toLowerCase();
      const laneConfig = SWIMLANE_MAP[laneKey] || SWIMLANE_MAP.ui;
      const laneEl = $(laneConfig.id);
      if (!laneEl) return;

      const laneTrack = laneEl.querySelector('.journey-lane-track');
      if (!laneTrack) return;

      const isHitl = step.status === 'hitl_paused' || step.state_transition.includes('AWAITING_APPROVAL');
      const statusClass = isHitl
        ? 'border-amber-500/50 bg-amber-950/20 text-amber-200'
        : 'border-white/[0.08] bg-[#0c0e14]/90 text-slate-200';

      const card = document.createElement('div');
      card.className = `journey-step-card relative flex-shrink-0 cursor-pointer p-3 rounded-xl border ${statusClass} hover:border-cyan-500/40 transition-all duration-200 shadow-sm w-56 select-none`;
      card.setAttribute('data-step-index', step.step_index);
      card.setAttribute('data-step-id', step.id);

      card.innerHTML = `
        <div class="flex items-center justify-between gap-1 mb-1">
          <span class="text-[10px] font-bold font-mono px-1.5 py-0.5 rounded bg-white/[0.06] text-cyan-400">Step ${step.step_index}</span>
          <span class="text-[9px] font-mono text-slate-400">${step.duration_ms ? step.duration_ms.toFixed(1) + 'ms' : ''}</span>
        </div>
        <div class="text-xs font-semibold text-white line-clamp-1 mb-1">${escapeHtml(step.title)}</div>
        <div class="text-[10px] text-slate-400 font-mono line-clamp-1">${escapeHtml(step.source_file ? step.source_file.split('/').pop() : '')}${step.source_line ? ':' + step.source_line : ''}</div>
      `;

      card.addEventListener('click', () => {
        pause();
        selectStep(step.step_index);
      });

      laneTrack.appendChild(card);
    });

    drawSvgConnectors(steps);
  }

  function drawSvgConnectors(_steps) {
    if (!svgOverlay || !nodesContainer) return;
    // We defer connector paths calculation until layout completes
    setTimeout(() => {
      const cards = Array.from(nodesContainer.querySelectorAll('.journey-step-card'));
      if (cards.length < 2) {
        svgOverlay.innerHTML = '';
        return;
      }

      const containerRect = nodesContainer.getBoundingClientRect();
      const pathSegments = [];

      for (let i = 0; i < cards.length - 1; i++) {
        const c1 = cards[i];
        const c2 = cards[i + 1];
        const r1 = c1.getBoundingClientRect();
        const r2 = c2.getBoundingClientRect();

        const p1 = {
          x: r1.right - containerRect.left,
          y: r1.top + r1.height / 2 - containerRect.top + nodesContainer.scrollTop,
        };
        const p2 = {
          x: r2.left - containerRect.left,
          y: r2.top + r2.height / 2 - containerRect.top + nodesContainer.scrollTop,
        };

        const d = buildSvgConnectorPath(p1, p2);
        const isActive = i + 1 < currentStepIndex;
        const strokeColor = isActive ? '#06b6d4' : 'rgba(255, 255, 255, 0.12)';
        const strokeWidth = isActive ? '2' : '1.5';
        pathSegments.push(`<path d="${d}" fill="none" stroke="${strokeColor}" stroke-width="${strokeWidth}" stroke-dasharray="${isActive ? 'none' : '4 3'}" />`);
      }

      svgOverlay.innerHTML = pathSegments.join('');
    }, 40);
  }

  async function selectStep(index) {
    if (!activeScenario || !activeScenario.steps) return;
    const steps = activeScenario.steps;
    currentStepIndex = clampStepIndex(index, steps.length);

    if (scrubber) scrubber.value = currentStepIndex;
    if (stepBadge) stepBadge.textContent = `Step ${currentStepIndex} of ${steps.length}`;

    // Highlight active card
    const allCards = nodesContainer ? nodesContainer.querySelectorAll('.journey-step-card') : [];
    allCards.forEach((c) => {
      const cIdx = Number(c.getAttribute('data-step-index'));
      if (cIdx === currentStepIndex) {
        c.classList.add('ring-2', 'ring-cyan-400', 'shadow-cyan-500/20', 'bg-cyan-950/30');
        c.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
      } else {
        c.classList.remove('ring-2', 'ring-cyan-400', 'shadow-cyan-500/20', 'bg-cyan-950/30');
      }
    });

    const activeStep = steps[currentStepIndex - 1];
    if (activeStep) {
      updateInspector(activeStep);
    }

    drawSvgConnectors(steps);
  }

  async function updateInspector(step) {
    // 1. Update State Badge
    if (inspectorStateBadge) {
      const badge = formatStateTransitionBadge(step.state_transition);
      let colorClasses = 'bg-cyan-950/80 text-cyan-300 border-cyan-800';
      if (badge.isWarning) {
        colorClasses = 'bg-amber-950/80 text-amber-300 border-amber-700 animate-pulse';
      } else if (badge.isSuccess) {
        colorClasses = 'bg-emerald-950/80 text-emerald-300 border-emerald-700';
      }
      inspectorStateBadge.className = `px-2 py-0.5 rounded text-[11px] font-mono font-bold uppercase border ${colorClasses}`;
      inspectorStateBadge.textContent = badge.text;
    }

    // 2. Update File Badge & IDE Link
    const fileName = step.source_file ? step.source_file.split('/').pop() : 'source';
    if (inspectorFileBadge) {
      inspectorFileBadge.textContent = `${fileName}:${step.source_line || 1}`;
    }
    if (inspectorIdeLink) {
      inspectorIdeLink.href = `vscode://file/${encodeURI(step.source_file || '')}:${step.source_line || 1}`;
    }

    // 3. Update Payload Inspector
    if (payloadCodeContainer) {
      payloadCodeContainer.textContent = JSON.stringify(step.payload || {}, null, 2);
    }

    // 4. Fetch and render Code Inspector
    if (codeLinesContainer && step.source_file) {
      codeLinesContainer.innerHTML = '<div class="text-slate-500 italic p-2 text-xs">Loading code snippet...</div>';
      const snippet = await fetchSourceSnippet(step.source_file, step.source_line || 1);
      renderSourceSnippet(snippet, step.source_line);
    }
  }

  async function fetchSourceSnippet(filePath, line) {
    const key = `${filePath}:${line}`;
    if (sourceCache.has(key)) return sourceCache.get(key);

    try {
      const res = await fetch(`/api/observability/journey-canvas/source?file_path=${encodeURIComponent(filePath)}&line=${line}&range_lines=10`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      sourceCache.set(key, data);
      return data;
    } catch {
      return { exists: false, lines: [], file_path: filePath, highlight_line: line };
    }
  }

  function renderSourceSnippet(snippet, targetLine) {
    if (!codeLinesContainer) return;
    if (!snippet || !snippet.exists || !snippet.lines || !snippet.lines.length) {
      codeLinesContainer.innerHTML = `<div class="text-slate-500 italic p-3 text-xs">Source file not found or line inaccessible (${escapeHtml(snippet?.file_path || '')}).</div>`;
      return;
    }

    const linesHtml = snippet.lines
      .map((l) => {
        const isHighlight = l.line_number === targetLine || l.is_highlight;
        const lineBg = isHighlight ? 'bg-cyan-500/15 border-l-2 border-cyan-400 font-semibold text-cyan-200' : 'text-slate-300';
        return `
          <div class="flex items-start font-mono text-[11px] leading-5 hover:bg-white/[0.04] transition-colors ${lineBg} px-2 py-0.5">
            <span class="w-8 flex-shrink-0 text-slate-500 select-none text-right pr-3">${l.line_number}</span>
            <span class="flex-1 whitespace-pre overflow-x-auto">${escapeHtml(l.content)}</span>
          </div>
        `;
      })
      .join('');

    codeLinesContainer.innerHTML = `<div class="py-1">${linesHtml}</div>`;
  }

  function togglePlay() {
    if (isPlaying) {
      pause();
    } else {
      play();
    }
  }

  function play() {
    if (!activeScenario || !activeScenario.steps) return;
    isPlaying = true;
    if (playBtn) playBtn.innerHTML = '<i data-lucide="pause" class="w-3.5 h-3.5"></i><span>Pause</span>';

    playInterval = setInterval(() => {
      const total = activeScenario.steps.length;
      if (currentStepIndex >= total) {
        currentStepIndex = 1;
      } else {
        currentStepIndex++;
      }
      selectStep(currentStepIndex);
    }, 1600);
  }

  function pause() {
    isPlaying = false;
    if (playInterval) {
      clearInterval(playInterval);
      playInterval = null;
    }
    if (playBtn) playBtn.innerHTML = '<i data-lucide="play" class="w-3.5 h-3.5"></i><span>Play</span>';
  }

  function stepNext() {
    pause();
    if (!activeScenario || !activeScenario.steps) return;
    if (currentStepIndex < activeScenario.steps.length) {
      selectStep(currentStepIndex + 1);
    }
  }

  function stepPrev() {
    pause();
    if (currentStepIndex > 1) {
      selectStep(currentStepIndex - 1);
    }
  }

  // Event Listeners Wiring
  if (scenarioSelect) {
    scenarioSelect.addEventListener('change', (ev) => {
      selectScenario(ev.target.value);
    });
  }

  if (prevBtn) prevBtn.addEventListener('click', stepPrev);
  if (nextBtn) nextBtn.addEventListener('click', stepNext);
  if (playBtn) playBtn.addEventListener('click', togglePlay);

  if (scrubber) {
    scrubber.addEventListener('input', (ev) => {
      pause();
      selectStep(Number(ev.target.value));
    });
  }

  if (copyPayloadBtn && payloadCodeContainer) {
    copyPayloadBtn.addEventListener('click', async () => {
      const text = payloadCodeContainer.textContent || '';
      try {
        await navigator.clipboard.writeText(text);
        const orig = copyPayloadBtn.innerHTML;
        copyPayloadBtn.innerHTML = '<span class="text-emerald-400">Copied!</span>';
        setTimeout(() => {
          copyPayloadBtn.innerHTML = orig;
        }, 1800);
      } catch (err) {
        console.warn('Failed to copy payload:', err);
      }
    });
  }

  window.addEventListener('resize', () => {
    if (activeScenario && activeScenario.steps) {
      drawSvgConnectors(activeScenario.steps);
    }
  });

  // Initial load
  loadScenarios();

  return {
    loadScenarios,
    selectScenario,
    selectStep,
    play,
    pause,
  };
}
