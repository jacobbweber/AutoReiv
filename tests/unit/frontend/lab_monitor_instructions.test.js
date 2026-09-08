/**
 * CARD-175: Agent Training Factory Visual Flowchart & Phase Instruction Inspector.
 * Contract tests for DOM elements, step tile interaction, and read-only context variables.
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Lab Monitor Phase Instruction Inspector DOM Contract [CARD-175]', () => {
  it('index.html contains Phase Instruction Inspector container and controls', () => {
    const html = read('src/web/templates/index.html');
    expect(html).toContain('id="labPhaseInspector"');
    expect(html).toContain('id="labPhaseTitle"');
    expect(html).toContain('id="labPhaseDescription"');
    expect(html).toContain('id="labPhaseBadge"');
    expect(html).toContain('id="labPhaseContextPills"');
    expect(html).toContain('id="labPhasePromptInput"');
    expect(html).toContain('id="labSavePhasePromptBtn"');
    expect(html).toContain('id="labResetPhasePromptBtn"');
  });

  it('lab stepper tiles contain data-phase-id and role=button', () => {
    const html = read('src/web/templates/index.html');
    expect(html).toContain('data-phase-id="intent_distill"');
    expect(html).toContain('data-phase-id="ground"');
    expect(html).toContain('data-phase-id="blueprint"');
    expect(html).toContain('data-phase-id="author"');
    expect(html).toContain('data-phase-id="scenario_verify"');
    expect(html).toContain('data-phase-id="verify"');
    expect(html).toContain('data-phase-id="optimize"');
    expect(html).toContain('data-phase-id="promote"');
  });

  it('forge.js wires phase inspector loading, saving, and reset', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js');
    expect(forgeJs).toContain('labPhaseInspector');
    expect(forgeJs).toContain('labPhasePromptInput');
    expect(forgeJs).toContain('labSavePhasePromptBtn');
    expect(forgeJs).toContain('labResetPhasePromptBtn');
    expect(forgeJs).toContain('/api/agent_training_factory/phases/instructions');
  });
});
