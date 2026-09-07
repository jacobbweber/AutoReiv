/**
 * CARD-182: Lab Monitor retry training job and copy activity feed controls.
 * [REQ-LAB-001, REQ-LAB-002, REQ-LAB-003]
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

import {
  formatLabActivityFeedText,
  populateTrainModalForRetry,
} from '../../../src/web/static/modules/studios/forge.js';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Lab Monitor Activity Feed Formatter [REQ-LAB-001]', () => {
  it('returns empty string for empty or missing packets', () => {
    expect(formatLabActivityFeedText([])).toBe('');
    expect(formatLabActivityFeedText(null)).toBe('');
    expect(formatLabActivityFeedText(undefined)).toBe('');
  });

  it('formats packet timestamps, upper-case roles, and message lines', () => {
    const packets = [
      {
        created_at: '2026-09-07T10:11:02.000Z',
        sender_role: 'orchestrator',
        payload: { message: 'Train capabilities for hyperv' },
      },
      {
        created_at: '2026-09-07T10:11:26.000Z',
        sender_role: 'intent_distill',
        payload: { message: 'Intent Distill completed for hyperv (7 question(s)).' },
      },
    ];

    const result = formatLabActivityFeedText(packets);
    expect(result).toContain('[ORCHESTRATOR] Train capabilities for hyperv');
    expect(result).toContain('[INTENT_DISTILL] Intent Distill completed for hyperv (7 question(s)).');
  });

  it('formats multiple lines when packet contains multi-line text or reason', () => {
    const packets = [
      {
        created_at: '2026-09-07T10:12:41.000Z',
        sender_role: 'verify',
        payload: {
          message: 'Verify battery FAILED - inner rinse (1/3) for manage_hyperv_vm [implementation].',
          rinse_kind: 'inner',
          failure_class: 'implementation',
          critic_notes: 'MCP Battery Exception: Execution timeout',
        },
      },
    ];

    const result = formatLabActivityFeedText(packets);
    expect(result).toContain('[VERIFY] Verify battery FAILED');
    expect(result).toContain('[VERIFY] Rinse: inner rinse / implementation');
    expect(result).toContain('[VERIFY] Reason: MCP Battery Exception: Execution timeout');
  });
});

describe('Lab Monitor Retry Pre-population [REQ-LAB-002]', () => {
  function createMockElements() {
    const modal = { dataset: {}, classList: { remove: () => {}, add: () => {} } };
    const nameInput = { value: '' };
    const nameGroup = { classList: { remove: () => {}, add: () => {} } };
    const targetLocation = { value: '' };
    const seedObjectives = { value: '' };
    const promptInput = { value: '' };
    const deliverableType = { value: '' };
    const constraints = { value: '' };
    const prerequisites = { value: '' };
    const referenceDocs = { value: '' };
    const advContent = {
      classList: {
        classes: new Set(['hidden']),
        toggle(cls, force) {
          if (typeof force === 'boolean') {
            if (force) this.classes.add(cls);
            else this.classes.delete(cls);
          } else {
            if (this.classes.has(cls)) this.classes.delete(cls);
            else this.classes.add(cls);
          }
        },
      },
    };
    const advChevron = {
      classList: {
        classes: new Set(),
        toggle(cls, force) {
          if (typeof force === 'boolean') {
            if (force) this.classes.add(cls);
            else this.classes.delete(cls);
          } else {
            if (this.classes.has(cls)) this.classes.delete(cls);
            else this.classes.add(cls);
          }
        },
      },
    };

    return {
      modal,
      nameInput,
      nameGroup,
      targetLocation,
      seedObjectives,
      promptInput,
      deliverableType,
      constraints,
      prerequisites,
      referenceDocs,
      advancedContent: advContent,
      advancedChevron: advChevron,
    };
  }

  it('returns false when jobData is missing', () => {
    expect(populateTrainModalForRetry(null)).toBe(false);
  });

  it('populates modal inputs and expands advanced accordion when inputs are provided', () => {
    const els = createMockElements();
    const jobData = {
      job: {
        id: 'job-12345',
        target_agent_id: 'hyperv-agent',
        seed_intent: 'Manage Hyper-V VMs',
        status: 'failed',
      },
      inputs: {
        target_agent_id: 'hyperv-agent',
        seed_intent: 'Manage Hyper-V VMs',
        objectives: ['Create VM', 'Stop VM', 'Inspect status'],
        deliverable_type: 'cli_pack',
        constraints: 'Run on Windows 11 host with Hyper-V enabled',
        prerequisites: 'PowerShell 7+',
        reference_docs: 'https://learn.microsoft.com/virtualization/hyper-v-on-windows',
        target_directory: 'local',
      },
    };

    const success = populateTrainModalForRetry(jobData, els);
    expect(success).toBe(true);

    expect(els.modal.dataset.agentId).toBe('hyperv-agent');
    expect(els.nameInput.value).toBe('hyperv-agent');
    expect(els.targetLocation.value).toBe('local');
    expect(els.seedObjectives.value).toBe('Create VM\nStop VM\nInspect status');
    expect(els.promptInput.value).toBe('Manage Hyper-V VMs');
    expect(els.deliverableType.value).toBe('cli_pack');
    expect(els.constraints.value).toBe('Run on Windows 11 host with Hyper-V enabled');
    expect(els.prerequisites.value).toBe('PowerShell 7+');
    expect(els.referenceDocs.value).toBe('https://learn.microsoft.com/virtualization/hyper-v-on-windows');

    // Advanced accordion should be expanded (not hidden)
    expect(els.advancedContent.classList.classes.has('hidden')).toBe(false);
    expect(els.advancedChevron.classList.classes.has('rotate-180')).toBe(true);
  });

  it('keeps advanced accordion collapsed when no advanced fields are present', () => {
    const els = createMockElements();
    const jobData = {
      job: {
        id: 'job-simple',
        target_agent_id: 'echo-agent',
        seed_intent: 'Echo messages',
        objectives: ['Echo strings'],
      },
      inputs: {},
    };

    const success = populateTrainModalForRetry(jobData, els);
    expect(success).toBe(true);
    expect(els.nameInput.value).toBe('echo-agent');
    expect(els.seedObjectives.value).toBe('Echo strings');
    expect(els.advancedContent.classList.classes.has('hidden')).toBe(true);
    expect(els.advancedChevron.classList.classes.has('rotate-180')).toBe(false);
  });
});

describe('Lab Monitor DOM Elements Contract [CARD-182]', () => {
  it('index.html contains retry button and copy feed button with required attributes', () => {
    const html = read('src/web/templates/index.html');
    expect(html).toContain('id="labRetryJobBtn"');
    expect(html).toContain('data-testid="lab-retry-job-btn"');
    expect(html).toContain('Retry Training');

    expect(html).toContain('id="labCopyFeedBtn"');
    expect(html).toContain('data-testid="lab-copy-feed-btn"');
    expect(html).toContain('id="labCopyFeedText"');
    expect(html).toContain('title="Copy live activity feed to clipboard"');
  });

  it('forge.js wires labCopyFeedBtn and labRetryJobBtn', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js');
    expect(forgeJs).toContain('formatLabActivityFeedText');
    expect(forgeJs).toContain('populateTrainModalForRetry');
    expect(forgeJs).toContain('labCopyFeedBtn');
    expect(forgeJs).toContain('labRetryJobBtn');
    expect(forgeJs).toContain('currentLabJobData');
  });
});
