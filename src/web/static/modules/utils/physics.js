/**
 * Pure 2D Force-Directed Graph Layout Simulation Math [REQ-UNIT-001]
 */

export const DEFAULT_PHYSICS_CONFIG = {
  repulsion: 120,
  spring: 0.04,
  linkDist: 60,
  damping: 0.88,
  centerGravity: 0.005,
  maxRepulsionDist: 450,
};

/**
 * Calculates and applies Coulomb node-node repulsive forces.
 * @param {Array<{x: number, y: number, vx: number, vy: number}>} nodes
 * @param {number} repulsion
 * @param {number} maxDist
 */
export function applyNodeRepulsion(
  nodes,
  repulsion = DEFAULT_PHYSICS_CONFIG.repulsion,
  maxDist = DEFAULT_PHYSICS_CONFIG.maxRepulsionDist
) {
  const nLen = nodes.length;
  for (let i = 0; i < nLen; i++) {
    const n1 = nodes[i];
    for (let j = i + 1; j < nLen; j++) {
      const n2 = nodes[j];
      const dx = n2.x - n1.x;
      const dy = n2.y - n1.y;
      const distSq = dx * dx + dy * dy + 1;
      const dist = Math.sqrt(distSq);

      if (dist < maxDist) {
        const force = (repulsion * 20) / distSq;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;

        n1.vx -= fx;
        n1.vy -= fy;
        n2.vx += fx;
        n2.vy += fy;
      }
    }
  }
}

/**
 * Calculates and applies Hooke's Law spring attractive forces for connected edges.
 * @param {Array<{sourceNode: Object, targetNode: Object}>} edges
 * @param {number} linkDist
 * @param {number} spring
 */
export function applyEdgeAttraction(
  edges,
  linkDist = DEFAULT_PHYSICS_CONFIG.linkDist,
  spring = DEFAULT_PHYSICS_CONFIG.spring
) {
  const eLen = edges.length;
  for (let i = 0; i < eLen; i++) {
    const edge = edges[i];
    const s = edge.sourceNode;
    const t = edge.targetNode;
    if (!s || !t) continue;

    const dx = t.x - s.x;
    const dy = t.y - s.y;
    const dist = Math.sqrt(dx * dx + dy * dy) + 0.1;
    const delta = dist - linkDist;
    const force = delta * spring;

    const fx = (dx / dist) * force;
    const fy = (dy / dist) * force;

    s.vx += fx;
    s.vy += fy;
    t.vx -= fx;
    t.vy -= fy;
  }
}

/**
 * Applies center gravity pulling towards (0,0) and integrates velocity into position with damping.
 * @param {Array<{x: number, y: number, vx: number, vy: number, pinned?: boolean}>} nodes
 * @param {number} centerGravity
 * @param {number} damping
 */
export function applyCenterGravityAndDamping(
  nodes,
  centerGravity = DEFAULT_PHYSICS_CONFIG.centerGravity,
  damping = DEFAULT_PHYSICS_CONFIG.damping
) {
  const nLen = nodes.length;
  for (let i = 0; i < nLen; i++) {
    const n = nodes[i];
    n.vx -= n.x * centerGravity;
    n.vy -= n.y * centerGravity;

    if (!n.pinned) {
      n.x += n.vx;
      n.y += n.vy;
      n.vx *= damping;
      n.vy *= damping;
    }
  }
}

/**
 * Performs a single complete Euler integration step for the graph simulation.
 * @param {Array} nodes
 * @param {Array} edges
 * @param {Object} [config={}]
 */
export function stepSimulation(nodes, edges, config = {}) {
  const cfg = { ...DEFAULT_PHYSICS_CONFIG, ...config };
  applyNodeRepulsion(nodes, cfg.repulsion, cfg.maxRepulsionDist);
  applyEdgeAttraction(edges, cfg.linkDist, cfg.spring);
  applyCenterGravityAndDamping(nodes, cfg.centerGravity, cfg.damping);
}
