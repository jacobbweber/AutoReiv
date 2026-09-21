/**
 * Wiki Studio: Obsidian-Style Mind Map & Physics Engine Submodule [REQ-MIND-003, CARD-399]
 * Force-directed interactive canvas graph with node/edge clustering, zoom, pan,
 * physics simulation runner, search filtering, and node interaction tooltips.
 */

import { $, safeCreateIcons } from '../../dom.js';
import { escapeHtml } from '../../utils/formatters.js';
import { stepSimulation, createSimulationRunner } from '../../utils/physics.js';

let mmRawGraphData = null;
let mmNodes = [];
let mmEdges = [];
let mmTransform = { x: 0, y: 0, scale: 1 };
let mmDraggingNode = null;
let mmDragStartPos = { x: 0, y: 0 };
let mmIsPanning = false;
let mmPanStart = { x: 0, y: 0 };
let mmHoveredNode = null;
let mmRunner = null;
let mmNoteSelectCallback = null;

const mmPhysics = {
  repulsion: 250,
  spring: 0.035,
  linkDist: 100,
  damping: 0.88,
  centerGravity: 0.015,
};

/**
 * Opens the mind map modal, resizes canvas, fetches graph data, and starts physics simulation.
 * @param {object} options
 */
export async function openMindMap({ onNoteSelect = null } = {}) {
  const wikiMindMapModal = $('wikiMindMapModal');
  const wikiMindMapCanvas = $('wikiMindMapCanvas');
  if (typeof onNoteSelect === 'function') {
    mmNoteSelectCallback = onNoteSelect;
  }

  if (!wikiMindMapModal || !wikiMindMapCanvas) return;
  wikiMindMapModal.classList.remove('hidden');
  safeCreateIcons();

  requestAnimationFrame(() => {
    resizeMindMapCanvas();
  });
  mmTransform = { x: 0, y: 0, scale: 1 };

  try {
    const res = await fetch('/api/wiki/mindmap?include_tags=true&include_taxonomy=true');
    if (!res.ok) throw new Error('Failed to load mind map data');
    mmRawGraphData = await res.json();
    initMindMapGraph();
    startMindMapSimulation();
  } catch (err) {
    console.error('[AutoReiv UI] Failed to load mind map:', err);
  }
}

/**
 * Closes the mind map modal and stops simulation.
 */
export function closeMindMap() {
  const wikiMindMapModal = $('wikiMindMapModal');
  const mindMapTooltip = $('mindMapTooltip');
  if (wikiMindMapModal) wikiMindMapModal.classList.add('hidden');
  if (mindMapTooltip) mindMapTooltip.classList.add('hidden');
  if (mmRunner) mmRunner.stop();
}

/**
 * Resizes the mind map canvas taking DPR into account.
 */
export function resizeMindMapCanvas() {
  const wikiMindMapCanvas = $('wikiMindMapCanvas');
  const mindMapCanvasContainer = $('mindMapCanvasContainer');
  if (!wikiMindMapCanvas || !mindMapCanvasContainer) return;
  const rect = mindMapCanvasContainer.getBoundingClientRect();
  const w = rect.width > 50 ? rect.width : window.innerWidth > 600 ? window.innerWidth * 0.8 : window.innerWidth - 32;
  const h = rect.height > 50 ? rect.height : Math.max(300, window.innerHeight * 0.75);
  const dpr = window.devicePixelRatio || 1;
  wikiMindMapCanvas.width = w * dpr;
  wikiMindMapCanvas.height = h * dpr;
  wikiMindMapCanvas.style.width = `${w}px`;
  wikiMindMapCanvas.style.height = `${h}px`;
}

/**
 * Initializes nodes and edges from raw graph data based on current toggle filters and search query.
 */
export function initMindMapGraph() {
  if (!mmRawGraphData) return;
  const mindMapSearchInput = $('mindMapSearchInput');
  const mmToggleNotes = $('mmToggleNotes');
  const mmToggleTags = $('mmToggleTags');
  const mmToggleDomains = $('mmToggleDomains');
  const mmToggleTopics = $('mmToggleTopics');
  const mmStatsNodes = $('mmStatsNodes');
  const mmStatsEdges = $('mmStatsEdges');

  const searchFilter = (mindMapSearchInput ? mindMapSearchInput.value : '').toLowerCase().trim();
  const showNotes = mmToggleNotes ? mmToggleNotes.checked : true;
  const showTags = mmToggleTags ? mmToggleTags.checked : true;
  const showDomains = mmToggleDomains ? mmToggleDomains.checked : true;
  const showTopics = mmToggleTopics ? mmToggleTopics.checked : true;

  const rawNodes = mmRawGraphData.nodes || [];
  const filteredNodes = rawNodes.filter((n) => {
    if (n.type === 'note' && !showNotes) return false;
    if (n.type === 'tag' && !showTags) return false;
    if (n.type === 'domain' && !showDomains) return false;
    if (n.type === 'topic' && !showTopics) return false;
    return true;
  });

  const activeNodeIdSet = new Set(filteredNodes.map((n) => n.id));
  const rawEdges = mmRawGraphData.edges || [];
  const filteredEdges = rawEdges.filter((e) => activeNodeIdSet.has(e.source) && activeNodeIdSet.has(e.target));

  const existingNodeMap = new Map(mmNodes.map((n) => [n.id, n]));
  const total = filteredNodes.length;

  mmNodes = filteredNodes.map((n, idx) => {
    const existing = existingNodeMap.get(n.id);
    let x, y, vx, vy;

    if (existing) {
      x = existing.x;
      y = existing.y;
      vx = existing.vx;
      vy = existing.vy;
    } else {
      const angle = (idx / Math.max(1, total)) * Math.PI * 2;
      const radius = 100 + (idx % 4) * 60;
      x = Math.cos(angle) * radius + (Math.random() - 0.5) * 20;
      y = Math.sin(angle) * radius + (Math.random() - 0.5) * 20;
      vx = 0;
      vy = 0;
    }

    let r = 8;
    let color = '#6366f1';
    if (n.type === 'note') {
      r = Math.max(8, Math.min(18, 8 + Math.sqrt(n.words || 1)));
      color = '#6366f1';
    } else if (n.type === 'tag') {
      r = Math.max(6, Math.min(14, 6 + (n.count || 1) * 1.5));
      color = '#10b981';
    } else if (n.type === 'domain') {
      r = 16;
      color = '#f59e0b';
    } else if (n.type === 'topic') {
      r = 12;
      color = '#38bdf8';
    }

    const matchesSearch =
      !searchFilter ||
      n.label.toLowerCase().includes(searchFilter) ||
      (n.tags || []).some((t) => t.toLowerCase().includes(searchFilter));

    return {
      ...n,
      x,
      y,
      vx,
      vy,
      radius: r,
      color,
      matchesSearch,
    };
  });

  const nodeById = new Map(mmNodes.map((n) => [n.id, n]));
  mmEdges = filteredEdges
    .map((e) => ({
      ...e,
      sourceNode: nodeById.get(e.source),
      targetNode: nodeById.get(e.target),
    }))
    .filter((e) => e.sourceNode && e.targetNode);

  if (mmStatsNodes) mmStatsNodes.textContent = `${mmNodes.length} nodes`;
  if (mmStatsEdges) mmStatsEdges.textContent = `${mmEdges.length} edges`;
}

/**
 * Initializes physics simulation runner with energy threshold.
 */
export function initMindMapRunner() {
  if (!mmRunner) {
    mmRunner = createSimulationRunner({
      onTick: tickMindMapPhysics,
      onRender: renderMindMapCanvas,
      getNodes: () => mmNodes,
      energyThreshold: 0.005,
    });
  }
}

/**
 * Starts mind map physics simulation runner.
 */
export function startMindMapSimulation() {
  initMindMapRunner();
  mmRunner.start();
}

/**
 * Executes a single physics step.
 */
export function tickMindMapPhysics() {
  const mmRepulsionSlider = $('mmRepulsionSlider');
  if (mmRepulsionSlider) mmPhysics.repulsion = parseFloat(mmRepulsionSlider.value);
  stepSimulation(mmNodes, mmEdges, mmPhysics);
}

/**
 * Renders the mind map graph (edges, nodes, halo, labels) onto the HTML5 Canvas.
 */
export function renderMindMapCanvas() {
  const wikiMindMapCanvas = $('wikiMindMapCanvas');
  if (!wikiMindMapCanvas) return;
  const ctx = wikiMindMapCanvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const width = wikiMindMapCanvas.width / dpr;
  const height = wikiMindMapCanvas.height / dpr;

  ctx.save();
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, width, height);

  ctx.fillStyle = '#020617';
  ctx.fillRect(0, 0, width, height);

  ctx.translate(width / 2 + mmTransform.x, height / 2 + mmTransform.y);
  ctx.scale(mmTransform.scale, mmTransform.scale);

  // Draw Edges
  for (let i = 0; i < mmEdges.length; i++) {
    const edge = mmEdges[i];
    const s = edge.sourceNode;
    const t = edge.targetNode;
    if (!s || !t) continue;

    ctx.beginPath();
    ctx.moveTo(s.x, s.y);
    ctx.lineTo(t.x, t.y);

    if (edge.type === 'wikilink') {
      ctx.strokeStyle = 'rgba(129, 140, 248, 0.5)';
      ctx.lineWidth = 1.8;
    } else if (edge.type === 'has_tag') {
      ctx.strokeStyle = 'rgba(16, 185, 129, 0.3)';
      ctx.lineWidth = 1.2;
    } else if (edge.type === 'in_topic') {
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.35)';
      ctx.lineWidth = 1.2;
    } else {
      ctx.strokeStyle = 'rgba(245, 158, 11, 0.35)';
      ctx.lineWidth = 1.4;
    }
    ctx.stroke();
  }

  // Draw Nodes
  for (let i = 0; i < mmNodes.length; i++) {
    const n = mmNodes[i];
    const isHovered = mmHoveredNode && mmHoveredNode.id === n.id;
    const alpha = n.matchesSearch ? 1 : 0.2;

    ctx.save();
    ctx.globalAlpha = alpha;

    if (isHovered) {
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius + 8, 0, Math.PI * 2);
      ctx.fillStyle = n.color;
      ctx.globalAlpha = 0.25;
      ctx.fill();
      ctx.globalAlpha = alpha;
    }

    ctx.beginPath();
    ctx.arc(n.x, n.y, n.radius + 2, 0, Math.PI * 2);
    ctx.strokeStyle = isHovered ? '#ffffff' : n.color;
    ctx.lineWidth = isHovered ? 2.5 : 1.5;
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
    ctx.fillStyle = isHovered ? '#ffffff' : n.color;
    ctx.fill();

    ctx.font = isHovered ? 'bold 12px Inter, sans-serif' : '10px Inter, sans-serif';
    ctx.fillStyle = isHovered ? '#ffffff' : '#cbd5e1';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';

    const labelText = n.label.length > 24 ? n.label.slice(0, 22) + '...' : n.label;
    ctx.fillText(labelText, n.x, n.y + n.radius + 5);

    ctx.restore();
  }

  ctx.restore();
}

/**
 * Transforms screen client coordinates to world canvas coordinates.
 * @param {number} clientX
 * @param {number} clientY
 * @returns {{ x: number, y: number }}
 */
export function screenToWorld(clientX, clientY) {
  const wikiMindMapCanvas = $('wikiMindMapCanvas');
  if (!wikiMindMapCanvas) return { x: 0, y: 0 };
  const rect = wikiMindMapCanvas.getBoundingClientRect();
  const width = rect.width;
  const height = rect.height;

  const screenX = clientX - rect.left;
  const screenY = clientY - rect.top;

  const worldX = (screenX - width / 2 - mmTransform.x) / mmTransform.scale;
  const worldY = (screenY - height / 2 - mmTransform.y) / mmTransform.scale;

  return { x: worldX, y: worldY };
}

/**
 * Finds the node at given world coordinates.
 * @param {number} worldX
 * @param {number} worldY
 * @returns {object|null}
 */
export function findNodeAt(worldX, worldY) {
  for (let i = mmNodes.length - 1; i >= 0; i--) {
    const n = mmNodes[i];
    const dx = n.x - worldX;
    const dy = n.y - worldY;
    if (dx * dx + dy * dy <= (n.radius + 6) * (n.radius + 6)) {
      return n;
    }
  }
  return null;
}

/**
 * Wires mind map modal open/close, zoom, pan, drag, touch, and tooltip listeners.
 * @param {object} options
 */
export function setupMindMap({ onNoteSelect = null } = {}) {
  if (typeof onNoteSelect === 'function') {
    mmNoteSelectCallback = onNoteSelect;
  }

  const wikiMindMapViewBtn = $('wikiMindMapViewBtn');
  const wikiMindMapModal = $('wikiMindMapModal');
  const wikiMindMapCloseBtn = $('wikiMindMapCloseBtn');
  const wikiMindMapCanvas = $('wikiMindMapCanvas');
  const mindMapSearchInput = $('mindMapSearchInput');
  const mindMapTooltip = $('mindMapTooltip');

  const mmToggleNotes = $('mmToggleNotes');
  const mmToggleTags = $('mmToggleTags');
  const mmToggleDomains = $('mmToggleDomains');
  const mmToggleTopics = $('mmToggleTopics');

  const mmZoomInBtn = $('mmZoomInBtn');
  const mmZoomOutBtn = $('mmZoomOutBtn');
  const mmResetViewBtn = $('mmResetViewBtn');

  window.addEventListener('resize', () => {
    if (wikiMindMapModal && !wikiMindMapModal.classList.contains('hidden')) {
      resizeMindMapCanvas();
    }
  });

  if (wikiMindMapCanvas) {
    wikiMindMapCanvas.addEventListener('mousedown', (e) => {
      const { x: wx, y: wy } = screenToWorld(e.clientX, e.clientY);
      const hit = findNodeAt(wx, wy);

      if (hit) {
        mmDraggingNode = hit;
        hit.pinned = true;
        mmDragStartPos = { x: e.clientX, y: e.clientY };
      } else {
        mmIsPanning = true;
        mmPanStart = { x: e.clientX - mmTransform.x, y: e.clientY - mmTransform.y };
      }
    });

    wikiMindMapCanvas.addEventListener('mousemove', (e) => {
      const { x: wx, y: wy } = screenToWorld(e.clientX, e.clientY);

      if (mmDraggingNode) {
        mmDraggingNode.x = wx;
        mmDraggingNode.y = wy;
        mmDraggingNode.vx = 0;
        mmDraggingNode.vy = 0;
      } else if (mmIsPanning) {
        mmTransform.x = e.clientX - mmPanStart.x;
        mmTransform.y = e.clientY - mmPanStart.y;
      } else {
        const hit = findNodeAt(wx, wy);
        mmHoveredNode = hit;

        if (hit && mindMapTooltip) {
          mindMapTooltip.classList.remove('hidden');
          mindMapTooltip.style.left = `${e.clientX + 16}px`;
          mindMapTooltip.style.top = `${e.clientY + 16}px`;

          let tooltipHtml = `<div class="font-bold text-white mb-1 flex items-center space-x-1.5">
            <span class="w-2.5 h-2.5 rounded-full" style="background:${hit.color}"></span>
            <span>${escapeHtml(hit.label)}</span>
          </div>`;

          if (hit.type === 'note') {
            tooltipHtml += `<div class="text-[11px] text-slate-400 space-y-0.5 font-mono">
              <p>🎓 Domain: <span class="text-amber-300">${hit.domain || 'general'}</span></p>
              <p>📖 Topic: <span class="text-sky-300">${hit.topic || 'general'}</span></p>
              <p>📊 Words: ${hit.words || 0} | Tokens: ${hit.tokens || 0}</p>
              ${hit.tags && hit.tags.length ? `<p class="text-emerald-400">#${hit.tags.join(' #')}</p>` : ''}
              <p class="text-indigo-300 font-sans mt-1.5 font-semibold">👉 Click to open note in editor</p>
            </div>`;
          } else if (hit.type === 'tag') {
            tooltipHtml += `<p class="text-[11px] text-slate-300">Tag connected to ${hit.count || 1} note(s).</p>`;
          } else if (hit.type === 'domain') {
            tooltipHtml += `<p class="text-[11px] text-slate-300">Degree Domain cluster (${hit.count || 1} notes).</p>`;
          } else if (hit.type === 'topic') {
            tooltipHtml += `<p class="text-[11px] text-slate-300">Class Topic cluster (${hit.count || 1} notes).</p>`;
          }

          mindMapTooltip.innerHTML = tooltipHtml;
        } else if (mindMapTooltip) {
          mindMapTooltip.classList.add('hidden');
        }
      }
    });

    window.addEventListener('mouseup', (e) => {
      if (mmDraggingNode) {
        const distMoved = Math.hypot(e.clientX - mmDragStartPos.x, e.clientY - mmDragStartPos.y);
        const clickedNode = mmDraggingNode;
        mmDraggingNode.pinned = false;
        mmDraggingNode = null;

        if (distMoved < 5 && clickedNode.type === 'note' && clickedNode.path) {
          closeMindMap();
          if (typeof mmNoteSelectCallback === 'function') {
            mmNoteSelectCallback(clickedNode.path);
          }
        }
      }
      mmIsPanning = false;
    });

    wikiMindMapCanvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.15 : 0.88;
      mmTransform.scale = Math.max(0.2, Math.min(4.0, mmTransform.scale * zoomFactor));
      if (mmRunner) mmRunner.wake();
    });

    let touchStartDist = 0;
    wikiMindMapCanvas.addEventListener(
      'touchstart',
      (e) => {
        if (e.touches.length === 1) {
          const touch = e.touches[0];
          const { x: wx, y: wy } = screenToWorld(touch.clientX, touch.clientY);
          const hit = findNodeAt(wx, wy);

          if (hit) {
            mmDraggingNode = hit;
            hit.pinned = true;
            mmDragStartPos = { x: touch.clientX, y: touch.clientY };
            if (mmRunner) mmRunner.wake();
          } else {
            mmIsPanning = true;
            mmPanStart = { x: touch.clientX - mmTransform.x, y: touch.clientY - mmTransform.y };
          }
        } else if (e.touches.length === 2) {
          touchStartDist = Math.hypot(
            e.touches[0].clientX - e.touches[1].clientX,
            e.touches[0].clientY - e.touches[1].clientY
          );
        }
      },
      { passive: true }
    );

    wikiMindMapCanvas.addEventListener(
      'touchmove',
      (e) => {
        if (e.touches.length === 1) {
          const touch = e.touches[0];
          const { x: wx, y: wy } = screenToWorld(touch.clientX, touch.clientY);

          if (mmDraggingNode) {
            mmDraggingNode.x = wx;
            mmDraggingNode.y = wy;
            mmDraggingNode.vx = 0;
            mmDraggingNode.vy = 0;
            if (mmRunner) mmRunner.wake();
          } else if (mmIsPanning) {
            mmTransform.x = touch.clientX - mmPanStart.x;
            mmTransform.y = touch.clientY - mmPanStart.y;
            if (mmRunner) mmRunner.wake();
          }
        } else if (e.touches.length === 2 && touchStartDist > 0) {
          const dist = Math.hypot(
            e.touches[0].clientX - e.touches[1].clientX,
            e.touches[0].clientY - e.touches[1].clientY
          );
          const factor = dist / touchStartDist;
          mmTransform.scale = Math.max(0.2, Math.min(4.0, mmTransform.scale * (factor > 1 ? 1.03 : 0.97)));
          touchStartDist = dist;
          if (mmRunner) mmRunner.wake();
        }
      },
      { passive: true }
    );

    wikiMindMapCanvas.addEventListener('touchend', () => {
      if (mmDraggingNode) {
        mmDraggingNode.pinned = false;
        mmDraggingNode = null;
      }
      mmIsPanning = false;
      touchStartDist = 0;
    });
  }

  if (wikiMindMapViewBtn) {
    wikiMindMapViewBtn.addEventListener('click', () => openMindMap({ onNoteSelect }));
  }

  if (wikiMindMapCloseBtn) {
    wikiMindMapCloseBtn.addEventListener('click', closeMindMap);
  }

  if (wikiMindMapModal) {
    wikiMindMapModal.addEventListener('click', (e) => {
      if (e.target === wikiMindMapModal) {
        closeMindMap();
      }
    });
  }

  if (mindMapSearchInput) {
    mindMapSearchInput.addEventListener('input', () => {
      initMindMapGraph();
      if (mmRunner) mmRunner.wake();
    });
  }

  [mmToggleNotes, mmToggleTags, mmToggleDomains, mmToggleTopics].forEach((chk) => {
    if (chk) {
      chk.addEventListener('change', () => {
        initMindMapGraph();
        if (mmRunner) mmRunner.wake();
      });
    }
  });

  if (mmZoomInBtn) {
    mmZoomInBtn.addEventListener('click', () => {
      mmTransform.scale = Math.min(4.0, mmTransform.scale * 1.25);
      if (mmRunner) mmRunner.wake();
    });
  }
  if (mmZoomOutBtn) {
    mmZoomOutBtn.addEventListener('click', () => {
      mmTransform.scale = Math.max(0.2, mmTransform.scale * 0.8);
      if (mmRunner) mmRunner.wake();
    });
  }
  if (mmResetViewBtn) {
    mmResetViewBtn.addEventListener('click', () => {
      mmTransform = { x: 0, y: 0, scale: 1 };
      if (mmRunner) mmRunner.wake();
    });
  }
}
