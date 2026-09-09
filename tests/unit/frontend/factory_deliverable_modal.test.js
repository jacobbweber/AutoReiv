import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Tabbed HITL Promotion Deliverable Inspector [CARD-197, REQ-FACT-055]', () => {
  let html;

  beforeEach(() => {
    html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  });

  it('declares tabbed deliverable inspection modal in DOM [REQ-FACT-055]', () => {
    expect(html).toContain('id="factoryDeliverableModal"');
    expect(html).toContain('id="factoryDeliverableModalTitle"');
    expect(html).toContain('id="closeFactoryDeliverableModalBtn"');
    expect(html).toContain('id="closeFactoryDeliverableFooterBtn"');
  });

  it('declares 3 deliverable inspection tabs (Runbook, Python Code, Manifest Diff) [REQ-FACT-055]', () => {
    expect(html).toContain('id="factoryTabRunbookBtn"');
    expect(html).toContain('id="factoryTabToolBtn"');
    expect(html).toContain('id="factoryTabDiffBtn"');

    expect(html).toContain('id="factoryTabContentRunbook"');
    expect(html).toContain('id="factoryTabContentTool"');
    expect(html).toContain('id="factoryTabContentDiff"');

    expect(html).toContain('id="factoryDeliverableRunbookPreview"');
    expect(html).toContain('id="factoryDeliverableToolCode"');
    expect(html).toContain('id="factoryDeliverableManifestDiff"');
  });

  it('includes Inspect Deliverables trigger in HITL deployment card [REQ-FACT-055]', () => {
    expect(html).toContain('id="factoryInspectDeliverablesBtn"');
  });

  it('exports deliverable extractor helper from factory.js [REQ-FACT-055]', async () => {
    const { extractJobDeliverables } = await import('../../../src/web/static/modules/studios/factory.js');
    expect(typeof extractJobDeliverables).toBe('function');

    const sampleJob = { target_agent_id: 'sample-agent', seed_intent: 'Test agent intent' };
    const samplePackets = [
      {
        sender_role: 'author',
        payload: {
          files_map: {
            'skills/sample-skill/SKILL.md': '# Sample Runbook\n\n## Overview\nTest overview.',
            'tools/manage_sample.py': 'def manage_sample(action="status"): return {"status": "success"}',
          },
        },
      },
    ];

    const delivs = extractJobDeliverables(sampleJob, samplePackets);
    expect(delivs.runbookPath).toBe('skills/sample-skill/SKILL.md');
    expect(delivs.runbookContent).toContain('## Overview');
    expect(delivs.toolPath).toBe('tools/manage_sample.py');
    expect(delivs.toolCode).toContain('manage_sample');
    expect(delivs.manifestDiff).toContain('sample-agent');
  });
});
