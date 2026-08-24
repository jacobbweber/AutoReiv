import { describe, it, expect } from 'vitest';
import {
  DEFAULT_PHYSICS_CONFIG,
  applyNodeRepulsion,
  applyEdgeAttraction,
  applyCenterGravityAndDamping,
  stepSimulation,
} from '../../../src/web/static/modules/utils/physics.js';

describe('Mind Map Force-Directed Physics Engine [REQ-UNIT-001]', () => {
  it('defines valid default simulation configuration parameters', () => {
    expect(DEFAULT_PHYSICS_CONFIG.repulsion).toBeGreaterThan(0);
    expect(DEFAULT_PHYSICS_CONFIG.spring).toBeGreaterThan(0);
    expect(DEFAULT_PHYSICS_CONFIG.linkDist).toBeGreaterThan(0);
    expect(DEFAULT_PHYSICS_CONFIG.damping).toBeLessThan(1);
    expect(DEFAULT_PHYSICS_CONFIG.damping).toBeGreaterThan(0);
    expect(DEFAULT_PHYSICS_CONFIG.centerGravity).toBeGreaterThan(0);
  });

  it('repels close nodes away from each other', () => {
    const nodes = [
      { id: 'a', x: 0, y: 0, vx: 0, vy: 0 },
      { id: 'b', x: 10, y: 0, vx: 0, vy: 0 },
    ];

    applyNodeRepulsion(nodes, 100, 450);

    // Node A should be pushed to the left (negative vx)
    expect(nodes[0].vx).toBeLessThan(0);
    // Node B should be pushed to the right (positive vx)
    expect(nodes[1].vx).toBeGreaterThan(0);
    // Y velocities should remain approximately zero for horizontal separation
    expect(nodes[0].vy).toBeCloseTo(0, 5);
    expect(nodes[1].vy).toBeCloseTo(0, 5);
  });

  it('attracts connected nodes across long edge distances', () => {
    const nodeA = { id: 'a', x: -100, y: 0, vx: 0, vy: 0 };
    const nodeB = { id: 'b', x: 100, y: 0, vx: 0, vy: 0 };
    const edges = [{ sourceNode: nodeA, targetNode: nodeB }];

    // linkDist = 50, current dist = 200 -> delta = 150 > 0 (spring pulls nodes together)
    applyEdgeAttraction(edges, 50, 0.05);

    // Node A should be pulled right (positive vx)
    expect(nodeA.vx).toBeGreaterThan(0);
    // Node B should be pulled left (negative vx)
    expect(nodeB.vx).toBeLessThan(0);
  });

  it('applies center gravity pulling free nodes toward the origin', () => {
    const nodes = [
      { id: 'a', x: 100, y: 50, vx: 0, vy: 0 },
      { id: 'b', x: -100, y: -50, vx: 0, vy: 0 },
    ];

    applyCenterGravityAndDamping(nodes, 0.01, 0.9);

    expect(nodes[0].vx).toBeLessThan(0); // Pulled left toward 0
    expect(nodes[0].vy).toBeLessThan(0); // Pulled up toward 0
    expect(nodes[1].vx).toBeGreaterThan(0); // Pulled right toward 0
    expect(nodes[1].vy).toBeGreaterThan(0); // Pulled down toward 0
  });

  it('does not mutate positions of pinned nodes during simulation steps', () => {
    const nodeA = { id: 'a', x: 50, y: 50, vx: 0, vy: 0, pinned: true };
    const nodeB = { id: 'b', x: 100, y: 100, vx: 0, vy: 0, pinned: false };
    const edges = [{ sourceNode: nodeA, targetNode: nodeB }];

    stepSimulation([nodeA, nodeB], edges, DEFAULT_PHYSICS_CONFIG);

    expect(nodeA.x).toBe(50);
    expect(nodeA.y).toBe(50);
    expect(nodeB.x).not.toBe(100);
  });

  it('converges to a stable equilibrium state over multiple simulation steps', () => {
    const nodeA = { id: 'a', x: 10, y: 0, vx: 0, vy: 0 };
    const nodeB = { id: 'b', x: 20, y: 0, vx: 0, vy: 0 };
    const edges = [{ sourceNode: nodeA, targetNode: nodeB }];

    for (let step = 0; step < 50; step++) {
      stepSimulation([nodeA, nodeB], edges, DEFAULT_PHYSICS_CONFIG);
    }

    // Velocities should decay towards zero due to damping
    expect(Math.abs(nodeA.vx)).toBeLessThan(0.5);
    expect(Math.abs(nodeB.vx)).toBeLessThan(0.5);
    // Nodes should maintain a positive separation distance
    expect(nodeB.x - nodeA.x).toBeGreaterThan(10);
  });
});
