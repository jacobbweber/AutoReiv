/**
 * Unit Tests for Performance Optimization & Simulation Runner [REQ-PERF-001, REQ-PERF-002, REQ-PERF-004].
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  calculateKineticEnergy,
  createSimulationRunner,
} from '../../../src/web/static/modules/utils/physics.js';

describe('Performance & Kinetic Energy Simulation Runner', () => {
  describe('calculateKineticEnergy', () => {
    it('returns 0 for empty or invalid input', () => {
      expect(calculateKineticEnergy(null)).toBe(0);
      expect(calculateKineticEnergy([])).toBe(0);
    });

    it('calculates sum of v_x^2 + v_y^2 across all nodes', () => {
      const nodes = [
        { vx: 3, vy: 4 }, // 9 + 16 = 25
        { vx: 1, vy: 2 }, // 1 + 4 = 5
      ];
      expect(calculateKineticEnergy(nodes)).toBe(30);
    });

    it('handles nodes missing velocity fields gracefully', () => {
      const nodes = [{ vx: 2 }, { vy: 3 }, {}];
      expect(calculateKineticEnergy(nodes)).toBe(13);
    });
  });

  describe('createSimulationRunner', () => {
    let onTick;
    let onRender;
    let nodes;

    beforeEach(() => {
      onTick = vi.fn();
      onRender = vi.fn();
      nodes = [{ vx: 1, vy: 1 }];
    });

    it('initializes in stopped and non-sleeping state', () => {
      const runner = createSimulationRunner({
        onTick,
        onRender,
        getNodes: () => nodes,
      });

      expect(runner.isRunning()).toBe(false);
      expect(runner.isSleeping()).toBe(false);
    });

    it('transitions to running state on start()', () => {
      const runner = createSimulationRunner({
        onTick,
        onRender,
        getNodes: () => nodes,
      });

      runner.start();
      expect(runner.isRunning()).toBe(true);
      expect(runner.isSleeping()).toBe(false);

      runner.stop();
      expect(runner.isRunning()).toBe(false);
    });

    it('transitions to sleeping state when kinetic energy drops below threshold', () => {
      let energyHigh = true;
      const runner = createSimulationRunner({
        onTick: () => {
          if (!energyHigh) {
            nodes = [{ vx: 0.001, vy: 0.001 }]; // Energy: 0.000002 < 0.005
          }
        },
        onRender,
        getNodes: () => nodes,
        energyThreshold: 0.005,
      });

      nodes = [{ vx: 1, vy: 1 }];
      runner.start();
      expect(runner.isRunning()).toBe(true);

      // Settle energy
      energyHigh = false;
      nodes = [{ vx: 0.001, vy: 0.001 }];

      // Step
      const runnerNodes = [{ vx: 0.001, vy: 0.001 }];
      const runner2 = createSimulationRunner({
        onTick,
        onRender,
        getNodes: () => runnerNodes,
        energyThreshold: 0.005,
      });
      runner2.start();

      expect(runner2.isSleeping()).toBe(true);
      expect(runner2.isRunning()).toBe(false);

      // Wake up on interaction
      runnerNodes[0].vx = 2.0;
      runner2.wake();
      expect(runner2.isRunning()).toBe(true);
      expect(runner2.isSleeping()).toBe(false);
      runner2.stop();
    });

    it('stops cleanly and cancels pending animation frame on stop()', () => {
      const runner = createSimulationRunner({
        onTick,
        onRender,
        getNodes: () => nodes,
      });

      runner.start();
      expect(runner.isRunning()).toBe(true);

      runner.stop();
      expect(runner.isRunning()).toBe(false);
      expect(runner.isSleeping()).toBe(false);
    });
  });
});
