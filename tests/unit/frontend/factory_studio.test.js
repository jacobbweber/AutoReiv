import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Dedicated Agent Training Factory Studio [CARD-195]', () => {
  let html;

  beforeEach(() => {
    html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  });

  it('includes Factory Studio in app rail and sidebar navigation [REQ-FACT-034]', () => {
    expect(html).toContain('id="railBtnFactory"');
    expect(html).toContain('id="tab-factory"');
    expect(html).toContain('data-tab="factory"');
  });

  it('declares dedicated Factory Studio view container with two sub-view switchers [REQ-FACT-035]', () => {
    expect(html).toContain('id="view-factory"');
    expect(html).toContain('id="factoryTabPipelineBtn"');
    expect(html).toContain('id="factoryTabRunsBtn"');
    expect(html).toContain('id="factoryPipelineView"');
    expect(html).toContain('id="factoryRunsView"');
  });

  it('renders 8-stage visual flowchart and Phase Prompt Inspector [REQ-FACT-036]', () => {
    expect(html).toContain('id="factoryFlowchartContainer"');
    expect(html).toContain('id="factoryPhaseInspector"');
    expect(html).toContain('id="factoryInspectorStageTitle"');
    expect(html).toContain('id="factoryInspectorStageDesc"');
    expect(html).toContain('id="factoryInspectorStatusBadge"');
    expect(html).toContain('id="factoryContextVarPills"');
    expect(html).toContain('id="factoryPhasePromptInput"');
    expect(html).toContain('id="factorySavePromptBtn"');
    expect(html).toContain('id="factoryResetPromptBtn"');
  });

  it('renders two-pane workspace for training runs, HITL gate, and live packet feed [REQ-FACT-037]', () => {
    expect(html).toContain('id="factoryRunsListPane"');
    expect(html).toContain('id="factoryRunSearchInput"');
    expect(html).toContain('id="factoryRunsList"');
    expect(html).toContain('id="factoryRunDetailPane"');
    expect(html).toContain('id="factoryDetailJobBadge"');
    expect(html).toContain('id="factoryDetailStatusPill"');
    expect(html).toContain('id="factoryDetailRetryBtn"');
    expect(html).toContain('id="factoryDetailCopyFeedBtn"');
    expect(html).toContain('id="factoryDetailStepper"');
    expect(html).toContain('id="factoryDetailHitlCard"');
    expect(html).toContain('id="factoryDetailApproveBtn"');
    expect(html).toContain('id="factoryDetailRejectBtn"');
    expect(html).toContain('id="factoryDetailArtifactPills"');
    expect(html).toContain('id="factoryDetailPacketsFeed"');
    expect(html).toContain('id="factoryDetailPacketCount"');
  });

  it('provides new training run launcher button in studio header [REQ-FACT-038]', () => {
    expect(html).toContain('id="factoryNewRunBtn"');
  });

  it('includes mobile responsiveness back navigation button for run details [REQ-FACT-039]', () => {
    expect(html).toContain('id="factoryMobileBackToRunsBtn"');
  });

  it('exports 8-stage pipeline metadata and ordering [REQ-FACT-036]', async () => {
    const { PHASE_METADATA, PHASE_ORDER } = await import('../../../src/web/static/modules/studios/factory.js');
    expect(PHASE_METADATA).toHaveLength(8);
    expect(PHASE_ORDER).toEqual([
      'intent_distill',
      'ground',
      'blueprint',
      'author',
      'scenario_verify',
      'verify',
      'optimize',
      'promote',
    ]);
    expect(PHASE_METADATA[0].id).toBe('intent_distill');
    expect(PHASE_METADATA[7].id).toBe('promote');
  });

  it('calculates progress index for active and legacy nodes [REQ-FACT-037]', async () => {
    const { calculateProgressIndex } = await import('../../../src/web/static/modules/studios/factory.js');
    expect(calculateProgressIndex('intent_distill', 'running')).toBe(0);
    expect(calculateProgressIndex('blueprint', 'running')).toBe(2);
    expect(calculateProgressIndex('author', 'running')).toBe(3);
    expect(calculateProgressIndex('coder_node', 'running')).toBe(3); // legacy mapping
    expect(calculateProgressIndex('promote', 'waiting_approval')).toBe(7);
    expect(calculateProgressIndex('done', 'done')).toBe(8);
    expect(calculateProgressIndex('nonexistent_phase', 'idle')).toBe(-1);
  });

  it('filters factory jobs by search query and status pill [REQ-FACT-037]', async () => {
    const { filterJobs } = await import('../../../src/web/static/modules/studios/factory.js');
    const sampleJobs = [
      { id: 'fjob_1111', target_agent_id: 'hyperv-admin', status: 'running' },
      { id: 'fjob_2222', target_agent_id: 'linux-host', status: 'done' },
      { id: 'fjob_3333', target_agent_id: 'hyperv-admin', status: 'waiting_approval' },
      { id: 'fjob_4444', target_agent_id: 'finance-advisor', status: 'failed' },
    ];

    expect(filterJobs(sampleJobs, '', 'all')).toHaveLength(4);
    expect(filterJobs(sampleJobs, 'hyperv', 'all')).toHaveLength(2);
    expect(filterJobs(sampleJobs, '1111', 'all')).toHaveLength(1);
    expect(filterJobs(sampleJobs, '', 'running')).toHaveLength(1);
    expect(filterJobs(sampleJobs, '', 'done')).toHaveLength(1);
    expect(filterJobs(sampleJobs, '', 'waiting_approval')).toHaveLength(1);
    expect(filterJobs(sampleJobs, '', 'failed')).toHaveLength(1);
    expect(filterJobs(sampleJobs, 'nonexistent', 'all')).toHaveLength(0);
  });

  it('renders Agent Context Dropdown selector in Factory Studio header [REQ-FACT-040]', () => {
    expect(html).toContain('id="factoryAgentSelect"');
    expect(html).toContain('id="factoryNewRunBtnText"');
  });

  it('filters factory jobs by selected agent scope in addition to query and status [REQ-FACT-041]', async () => {
    const { filterJobs } = await import('../../../src/web/static/modules/studios/factory.js');
    const sampleJobs = [
      { id: 'fjob_1111', target_agent_id: 'hyperv-admin', status: 'running' },
      { id: 'fjob_2222', target_agent_id: 'linux-host', status: 'done' },
      { id: 'fjob_3333', target_agent_id: 'hyperv-admin', status: 'waiting_approval' },
      { id: 'fjob_4444', target_agent_id: 'finance-advisor', status: 'failed' },
    ];

    expect(filterJobs(sampleJobs, '', 'all', 'hyperv-admin')).toHaveLength(2);
    expect(filterJobs(sampleJobs, '', 'running', 'hyperv-admin')).toHaveLength(1);
    expect(filterJobs(sampleJobs, '', 'all', 'linux-host')).toHaveLength(1);
    expect(filterJobs(sampleJobs, '', 'all', '')).toHaveLength(4);
    expect(filterJobs(sampleJobs, '', 'all', 'nonexistent-agent')).toHaveLength(0);
  });

  it('populates agent options into #factoryAgentSelect dynamically [REQ-FACT-040]', async () => {
    const { populateFactoryAgentOptions } = await import('../../../src/web/static/modules/studios/factory.js');
    expect(typeof populateFactoryAgentOptions).toBe('function');

    const selectEl = {
      innerHTML: '',
      children: [],
      value: '',
      appendChild(child) {
        this.children.push(child);
      },
    };
    const sampleAgents = [
      { id: 'assistant', name: 'General Assistant' },
      { id: 'developer', name: 'Software Developer' },
    ];

    populateFactoryAgentOptions(selectEl, sampleAgents, 'developer');
    expect(selectEl.children.length).toBe(3); // All Agents + 2 agents
    expect(selectEl.children[0].value).toBe('');
    expect(selectEl.children[0].textContent).toContain('All Agents');
    expect(selectEl.children[1].value).toBe('assistant');
    expect(selectEl.children[2].value).toBe('developer');
    expect(selectEl.value).toBe('developer');
  });

  it('provides openFactoryStudio with target agent pre-selection [REQ-FACT-042]', async () => {
    const { initFactoryStudio } = await import('../../../src/web/static/modules/studios/factory.js');
    const ctrl = initFactoryStudio({ activeTab: 'factory' }, {});
    expect(typeof ctrl.setAgentScope).toBe('function');
  });
});

