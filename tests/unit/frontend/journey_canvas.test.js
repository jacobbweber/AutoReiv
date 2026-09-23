/**
 * Unit & Contract Tests for Observability Journey Canvas [CARD-428].
 *
 * Verifies:
 * 1. File size invariant: journey_canvas.js is strictly under 800 lines.
 * 2. DOM elements and 4 architectural swimlanes declared in index.html.
 * 3. Step coordinate calculations and SVG connector bezier curves.
 * 4. Step bounds clamping and inspector rendering.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

import {
  calculateStepCoordinates,
  buildSvgConnectorPath,
  clampStepIndex,
  formatStateTransitionBadge,
} from '../../../src/web/static/modules/observability/journey_canvas.js';

describe('Observability Journey Canvas [CARD-428]', () => {
  const indexHtmlPath = path.resolve(__dirname, '../../../src/web/templates/index.html');
  const indexHtml = fs.readFileSync(indexHtmlPath, 'utf-8');

  const journeyJsPath = path.resolve(__dirname, '../../../src/web/static/modules/observability/journey_canvas.js');
  const journeyJs = fs.readFileSync(journeyJsPath, 'utf-8');

  it('enforces monolith decomposition: journey_canvas.js is strictly under 800 lines', () => {
    const lineCount = journeyJs.split('\n').length;
    expect(lineCount).toBeLessThan(800);
    expect(lineCount).toBeGreaterThan(50); // Sanity check
  });

  it('renders dedicated journey-canvas section in index.html', () => {
    expect(indexHtml).toContain('data-obs-section="journey-canvas"');
    expect(indexHtml).toContain('id="journeyScenarioSelect"');
    expect(indexHtml).toContain('id="journeyPrevStepBtn"');
    expect(indexHtml).toContain('id="journeyPlayPauseBtn"');
    expect(indexHtml).toContain('id="journeyNextStepBtn"');
    expect(indexHtml).toContain('id="journeyStepScrubber"');
    expect(indexHtml).toContain('id="journeyStepBadge"');
  });

  it('renders four distinct architectural swimlanes in index.html', () => {
    expect(indexHtml).toContain('id="journeyLaneUi"');
    expect(indexHtml).toContain('id="journeyLaneApi"');
    expect(indexHtml).toContain('id="journeyLaneOrchestrator"');
    expect(indexHtml).toContain('id="journeyLaneStorage"');
  });

  it('renders code and payload inspector elements in index.html', () => {
    expect(indexHtml).toContain('id="journeyInspectorDrawer"');
    expect(indexHtml).toContain('id="journeyInspectorFileBadge"');
    expect(indexHtml).toContain('id="journeyInspectorStateBadge"');
    expect(indexHtml).toContain('id="journeyCodeLines"');
    expect(indexHtml).toContain('id="journeyPayloadCode"');
    expect(indexHtml).toContain('id="journeyCopyPayloadBtn"');
  });

  it('clamps step index within valid scenario bounds', () => {
    expect(clampStepIndex(0, 10)).toBe(1);
    expect(clampStepIndex(5, 10)).toBe(5);
    expect(clampStepIndex(11, 10)).toBe(10);
    expect(clampStepIndex(-3, 5)).toBe(1);
  });

  it('generates valid SVG bezier curve between sequential nodes', () => {
    const p1 = { x: 100, y: 50 };
    const p2 = { x: 250, y: 150 };
    const pathD = buildSvgConnectorPath(p1, p2);
    expect(pathD).toMatch(/^M 100 50 C/);
    expect(pathD).toContain('250 150');
  });

  it('computes step coordinates based on swimlane index and step order', () => {
    const coords1 = calculateStepCoordinates({ swimlane: 'ui', step_index: 1 }, 200);
    const coords2 = calculateStepCoordinates({ swimlane: 'api', step_index: 2 }, 200);
    expect(coords1.x).toBeLessThan(coords2.x);
    expect(coords1.laneIndex).toBe(0);
    expect(coords2.laneIndex).toBe(1);
  });

  it('formats state transition badge with clean color classes', () => {
    const hitlBadge = formatStateTransitionBadge('PLANNING -> AWAITING_APPROVAL');
    expect(hitlBadge.isWarning).toBe(true);
    expect(hitlBadge.text).toBe('PLANNING -> AWAITING_APPROVAL');

    const normalBadge = formatStateTransitionBadge('IDLE -> SUBMITTING');
    expect(normalBadge.isWarning).toBe(false);
  });
});
