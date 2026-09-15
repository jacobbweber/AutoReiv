/**
 * Lumina SVG Visual Layout & Animation Engine [CARD-328].
 * Pure ES Module implementation supporting all 14 visual archetypes:
 * flow, cycle, compare, orbit, stack, split, wave, network, scale,
 * balance, grow, transform, pipeline, system.
 */

const W = 1000;
const H = 800;
const CX = 500;
const CY = 400;

function lineLayout(n, x0, x1, y) {
  if (n <= 1) return [{ x: (x0 + x1) / 2, y }];
  return Array.from({ length: n }, (_, i) => ({
    x: x0 + (i * (x1 - x0)) / (n - 1),
    y,
  }));
}

function circleLayout(n, cx, cy, r, rot = -Math.PI / 2) {
  return Array.from({ length: n }, (_, i) => {
    const a = rot + (i * 2 * Math.PI) / n;
    return { x: cx + Math.cos(a) * r, y: cy + Math.sin(a) * r };
  });
}

function gridLayout(n, x0, y0, x1, y1, cols) {
  const c = cols || (n <= 3 ? n : n <= 4 ? 2 : 3);
  const rows = Math.ceil(n / c);
  const pts = [];
  for (let i = 0; i < n; i++) {
    const col = i % c;
    const row = Math.floor(i / c);
    const inRow = Math.min(c, n - row * c);
    const rowX0 = inRow === c ? x0 : (x0 + x1) / 2 - ((inRow - 1) * (x1 - x0)) / (2 * Math.max(c - 1, 1));
    const x = inRow === 1 ? (x0 + x1) / 2 : rowX0 + (col * (x1 - x0)) / Math.max(c - 1, 1);
    const y = rows === 1 ? (y0 + y1) / 2 : y0 + (row * (y1 - y0)) / Math.max(rows - 1, 1);
    pts.push({ x, y });
  }
  return pts;
}

function edgePoint(from, to, hw, hh) {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  if (dx === 0 && dy === 0) return from;
  const ax = Math.abs(dx) / Math.max(hw, 1);
  const ay = Math.abs(dy) / Math.max(hh, 1);
  if (ax > ay) {
    return { x: from.x + Math.sign(dx) * hw, y: from.y + (dy * hw) / Math.abs(dx) };
  }
  return { x: from.x + (dx * hh) / Math.abs(dy), y: from.y + Math.sign(dy) * hh };
}

function elbow(a, b) {
  const mx = (a.x + b.x) / 2;
  return `M ${a.x} ${a.y} C ${mx} ${a.y}, ${mx} ${b.y}, ${b.x} ${b.y}`;
}

function arc(a, b, sweep = 1) {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const r = Math.max(40, Math.hypot(dx, dy) * 0.72);
  return `M ${a.x} ${a.y} A ${r} ${r} 0 0 ${sweep} ${b.x} ${b.y}`;
}

function renderDefs() {
  return `
    <defs>
      <pattern id="lumina-grid" width="40" height="40" patternUnits="userSpaceOnUse">
        <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(148, 163, 184, 0.08)" stroke-width="1" />
      </pattern>
      <filter id="lumina-glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="5" result="blur" />
        <feMerge>
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
      <marker id="lumina-arrow" markerWidth="10" markerHeight="8" refX="8" refY="4" orient="auto">
        <path d="M 0 0 L 10 4 L 0 8 Z" fill="#818cf8" />
      </marker>
      <marker id="lumina-arrow-dim" markerWidth="10" markerHeight="8" refX="8" refY="4" orient="auto">
        <path d="M 0 0 L 10 4 L 0 8 Z" fill="rgba(148, 163, 184, 0.4)" />
      </marker>
    </defs>
  `;
}

function renderPipe(a, b, label = '', delay = 0, curved = false) {
  const p1 = edgePoint(a, b, 85, 40);
  const p2 = edgePoint(b, a, 85, 40);
  const d = curved ? arc(p1, p2) : elbow(p1, p2);
  const dur = 3.6;

  return `
    <g>
      <path d="${d}" fill="none" stroke="#6366f1" stroke-width="2" opacity="0.65" marker-end="url(#lumina-arrow)" />
      <path d="${d}" fill="none" stroke="#818cf8" stroke-width="1.2" stroke-dasharray="4 8" opacity="0.4" />
      ${label ? `
        <rect x="${(p1.x + p2.x) / 2 - 40}" y="${(p1.y + p2.y) / 2 - 10}" width="80" height="20" rx="10" fill="#1e1b4b" stroke="#6366f1" stroke-width="1" />
        <text x="${(p1.x + p2.x) / 2}" y="${(p1.y + p2.y) / 2 + 4}" text-anchor="middle" fill="#c7d2fe" font-size="10" font-family="sans-serif">${label}</text>
      ` : ''}
      <circle r="4.5" fill="#a5b4fc" filter="url(#lumina-glow)">
        <animateMotion dur="${dur}s" repeatCount="indefinite" begin="${delay / 1000}s" path="${d}" rotate="auto" />
      </circle>
    </g>
  `;
}

function renderCard(pt, node, _index = 0, active = false) {
  const w = 170;
  const h = 76;
  const x = pt.x - w / 2;
  const y = pt.y - h / 2;
  const isEmphasis = node.emphasis || active;

  const strokeColor = isEmphasis ? "#818cf8" : "rgba(100, 116, 139, 0.4)";
  const strokeWidth = isEmphasis ? "2" : "1";
  const bgFill = isEmphasis ? "rgba(30, 27, 75, 0.85)" : "rgba(15, 23, 42, 0.75)";
  const textFill = isEmphasis ? "#ffffff" : "#f1f5f9";
  const captionFill = isEmphasis ? "#a5b4fc" : "#94a3b8";

  return `
    <g class="lumina-node cursor-pointer" data-node-id="${node.id}">
      ${isEmphasis ? `
        <rect x="${x - 4}" y="${y - 4}" width="${w + 8}" height="${h + 8}" rx="18" fill="none" stroke="rgba(99, 102, 241, 0.3)" stroke-width="2">
          <animate attributeName="opacity" values="0.2;0.7;0.2" dur="3s" repeatCount="indefinite" />
        </rect>
      ` : ''}
      <rect x="${x}" y="${y}" width="${w}" height="${h}" rx="14" fill="${bgFill}" stroke="${strokeColor}" stroke-width="${strokeWidth}" />
      ${node.role ? `
        <rect x="${x + 12}" y="${y + 10}" width="40" height="14" rx="7" fill="rgba(99, 102, 241, 0.2)" />
        <text x="${x + 32}" y="${y + 20}" text-anchor="middle" fill="#818cf8" font-size="9" font-weight="600" text-transform="uppercase">${node.role}</text>
      ` : ''}
      <text x="${x + w / 2}" y="${y + (node.caption ? 36 : 44)}" text-anchor="middle" fill="${textFill}" font-size="13" font-weight="600" font-family="sans-serif">${node.label}</text>
      ${node.caption ? `
        <text x="${x + w / 2}" y="${y + 54}" text-anchor="middle" fill="${captionFill}" font-size="10" font-family="sans-serif">${node.caption}</text>
      ` : ''}
    </g>
  `;
}

export function renderLuminaVisual(spec, containerEl) {
  if (!spec || !containerEl) return;

  const kind = spec.kind || "flow";
  const nodes = spec.nodes || [];
  const links = spec.links || [];
  const n = Math.max(2, nodes.length);

  let pts = [];

  switch (kind) {
    case "cycle":
    case "orbit":
      pts = circleLayout(n, CX, CY, Math.min(CX, CY) - 100);
      break;
    case "stack":
      pts = Array.from({ length: n }, (_, i) => ({
        x: CX,
        y: 160 + (i * (H - 260)) / Math.max(1, n - 1),
      }));
      break;
    case "compare":
    case "balance":
    case "scale":
      pts = gridLayout(n, 180, 200, W - 180, H - 200, 2);
      break;
    case "wave":
      pts = Array.from({ length: n }, (_, i) => {
        const x = 160 + (i * (W - 320)) / Math.max(1, n - 1);
        const y = CY + Math.sin((i / (n - 1)) * Math.PI * 2) * 120;
        return { x, y };
      });
      break;
    case "split":
      pts = [
        { x: 180, y: CY },
        ...Array.from({ length: n - 1 }, (_, i) => ({
          x: W - 220,
          y: 180 + (i * (H - 360)) / Math.max(1, n - 2),
        })),
      ];
      break;
    case "flow":
    case "pipeline":
    case "transform":
    case "grow":
    case "network":
    case "system":
    default:
      if (n <= 4) {
        pts = lineLayout(n, 160, W - 160, CY);
      } else {
        pts = gridLayout(n, 160, 180, W - 160, H - 200);
      }
      break;
  }

  // Generate pipe connections
  const nodeMap = new Map(nodes.map((node, i) => [node.id, pts[i]]));
  let pipesHtml = "";

  if (links.length > 0) {
    links.forEach((link, idx) => {
      const a = nodeMap.get(link.from);
      const b = nodeMap.get(link.to);
      if (a && b) {
        pipesHtml += renderPipe(a, b, link.label || "", idx * 180, kind === "cycle" || kind === "orbit");
      }
    });
  } else {
    // Default sequential link
    for (let i = 0; i < nodes.length - 1; i++) {
      if (pts[i] && pts[i + 1]) {
        pipesHtml += renderPipe(pts[i], pts[i + 1], "", i * 200, kind === "cycle" || kind === "orbit");
      }
    }
  }

  // Generate nodes
  let nodesHtml = "";
  nodes.forEach((node, i) => {
    if (pts[i]) {
      nodesHtml += renderCard(pts[i], node, i, node.emphasis);
    }
  });

  const svgContent = `
    <svg viewBox="0 0 ${W} ${H}" class="w-full h-full select-none" xmlns="http://www.w3.org/2000/svg">
      ${renderDefs()}
      <rect x="0" y="0" width="${W}" height="${H}" fill="url(#lumina-grid)" />
      ${spec.title ? `
        <text x="40" y="50" fill="#94a3b8" font-size="13" font-weight="600" letter-spacing="1" text-transform="uppercase" font-family="sans-serif">${spec.title}</text>
      ` : ''}
      <g class="lumina-pipes">${pipesHtml}</g>
      <g class="lumina-cards">${nodesHtml}</g>
    </svg>
  `;

  containerEl.innerHTML = svgContent;
}
