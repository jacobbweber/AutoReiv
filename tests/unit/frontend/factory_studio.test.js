import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Capabilities & Scaffolding Workshop Studio [CARD-386]', () => {
  let html;

  beforeEach(() => {
    html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  });

  it('includes Factory Studio in navigation and prunes obsolete rail button [REQ-FACT-034, CARD-369]', () => {
    expect(html).not.toContain('id="railBtnFactory"');
    expect(html).toContain('id="tab-factory"');
    expect(html).toContain('data-tab="factory"');
  });

  it('declares dedicated Factory Studio view container with 3-column scaffolder workshop [CARD-386]', () => {
    expect(html).toContain('id="view-factory"');
    expect(html).toContain('id="factoryStudio"');
    expect(html).toContain('id="factoryIntakeView"');
    expect(html).not.toContain('id="factoryTabPipelineBtn"');
    expect(html).not.toContain('id="factoryTabRunsBtn"');
    expect(html).not.toContain('id="factoryTabIntakeBtn"');
    expect(html).not.toContain('id="factoryPipelineView"');
    expect(html).not.toContain('id="factoryRunsView"');
  });

  it('prunes legacy 8-stage visual flowchart and Phase Prompt Inspector [CARD-386]', () => {
    expect(html).not.toContain('id="factoryFlowchartContainer"');
    expect(html).not.toContain('id="factoryPhaseInspector"');
    expect(html).not.toContain('id="factoryPhasePromptInput"');
    expect(html).not.toContain('id="factoryInspectorStageTitle"');
    expect(html).not.toContain('id="factorySavePromptBtn"');
    expect(html).not.toContain('id="factoryResetPromptBtn"');
  });

  it('prunes legacy training runs pane, HITL card, and live packet feed [CARD-386]', () => {
    expect(html).not.toContain('id="factoryRunsListPane"');
    expect(html).not.toContain('id="factoryRunSearchInput"');
    expect(html).not.toContain('id="factoryRunsList"');
    expect(html).not.toContain('id="factoryRunDetailPane"');
    expect(html).not.toContain('id="factoryDetailHitlCard"');
    expect(html).not.toContain('id="factoryDetailPacketsFeed"');
    expect(html).not.toContain('id="factoryDetailStepper"');
    expect(html).not.toContain('id="factoryDetailApproveBtn"');
    expect(html).not.toContain('id="factoryDetailRejectBtn"');
  });

  it('prunes obsolete new training run button and mobile back button [CARD-386]', () => {
    expect(html).not.toContain('id="factoryNewRunBtn"');
    expect(html).not.toContain('id="factoryNewRunBtnText"');
    expect(html).not.toContain('id="factoryMobileBackToRunsBtn"');
  });

  it('renders Target Specialist Selector in Column 1 with New Agent option [CARD-386]', () => {
    expect(html).toContain('id="factoryAgentSelect"');
    expect(html).toContain('+ Create New Agent');
    expect(html).not.toContain('id="factoryNewAgentBtn"');
  });

  it('renders top action banner and 3 columns with canonical Scaffolder workshop DOM structure [CARD-386, CARD-387]', () => {
    // Top Horizontal Action Banner [CARD-387]
    expect(html).toContain('id="factoryTopActionBar"');
    expect(html).toContain('id="factoryIntakeTalkToForgeBtn"');
    expect(html).toContain('1. Talk it out with Forge');
    expect(html).toContain('id="factoryGenerateRunbookBtn"');
    expect(html).toContain('2. ✨ Generate / Refine Runbook');
    expect(html).toContain('id="factorySaveSkillBtn"');
    expect(html).toContain('3. 💾 Save &amp; Pin Skill to Agent');
    expect(html).toContain('id="factoryGenerateStatusText"');
    expect(html).toContain('id="factorySaveFeedbackMsg"');

    // Column 1: Agent Brief
    expect(html).toContain('id="factoryIntakeAgentCard"');
    expect(html).toContain('id="factoryAgentSelect"');
    expect(html).toContain('id="factoryAgentIdInput"');
    expect(html).toMatch(/id="factoryAgentIdInput"[^>]*readonly/);
    expect(html).toContain('id="factoryAgentNameInput"');
    expect(html).toContain('id="factoryAgentPromptInput"');
    expect(html).not.toContain('id="factoryAgentModelSelect"');
    expect(html).toContain('id="factoryCurrentSkillsList"');
    expect(html).toContain('id="factoryAssignedSkillsCount"');
    expect(html).toContain('data-testid="factory-assigned-skills"');

    // Column 2: Skill Workshop
    expect(html).toContain('id="factoryExistingSkillSelect"');
    expect(html).toContain('id="factoryExistingSkillFilter"');
    expect(html).toContain('id="factoryNewSkillFormBtn"');
    expect(html).toContain('id="factoryWorkshopSkillBadge"');
    expect(html).toContain('id="factorySkillNameInput"');
    expect(html).toContain('id="factorySkillIdInput"');
    expect(html).toMatch(/id="factorySkillIdInput"[^>]*readonly/);
    expect(html).toContain('id="factorySkillTriggerInput"');
    expect(html).toContain('id="factorySkillTriggerCharCount"');
    expect(html).toContain('id="factorySkillIntentInput"');
    expect(html).toContain('id="factorySkillMarkdownEditor"');

    // Column 3: Capabilities & Grounding
    expect(html).toContain('id="factorySelectedToolCountBadge"');
    expect(html).toContain('id="factoryToolSearchInput"');
    expect(html).toContain('id="factorySelectAllToolsBtn"');
    expect(html).toContain('id="factoryClearAllToolsBtn"');
    expect(html).toContain('id="factoryAutoSuggestToolsBtn"');
    expect(html).toContain('id="factoryCapabilitiesContainer"');
    expect(html).toContain('id="factorySourceContextInput"');
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
    expect(typeof ctrl.loadFactoryStudio).toBe('function');
    expect(typeof ctrl.stopPolling).toBe('function');
  });

  it('excludes internal agent_builder and agent-builder from agent options [REQ-FACT-040]', async () => {
    const { populateFactoryAgentOptions } = await import('../../../src/web/static/modules/studios/factory.js');
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
      { id: 'agent_builder', name: 'Agent Builder' },
      { id: 'agent-builder', name: 'Agent Builder 2' },
      { id: 'developer', name: 'Software Developer' },
    ];

    populateFactoryAgentOptions(selectEl, sampleAgents, 'developer');
    expect(selectEl.children.length).toBe(3); // All Agents + assistant + developer
    const ids = selectEl.children.map((c) => c.value);
    expect(ids).toContain('assistant');
    expect(ids).toContain('developer');
    expect(ids).not.toContain('agent_builder');
    expect(ids).not.toContain('agent-builder');
  });

  it('retires redundant training buttons from Agent Studio [REQ-FACT-042]', () => {
    expect(html).not.toContain('id="forgeTrainAgentBtn"');
    expect(html).not.toContain('id="forgeLabMonitorBtn"');
  });

  it('preserves Needs Training Backlog inside Agent Studio character sheet [CARD-195, CARD-386]', () => {
    expect(html).toContain('id="agentTrainingBacklogCard"');
    expect(html).toContain('id="agentBacklogCountBadge"');
    expect(html).toContain('id="agentBacklogList"');
  });

  it('locks training modal to selected agent and omits secondary target dropdown [REQ-FACT-043]', () => {
    const modalSlice = html.slice(html.indexOf('id="trainAgentHandshakeModal"'));
    expect(modalSlice).toContain('id="trainAgentTargetBadge"');
    expect(modalSlice).toContain('id="trainAgentTargetName"');
    expect(modalSlice).toContain('id="trainAgentTargetIdBadge"');
    expect(modalSlice).not.toContain('id="trainAgentTargetSelect"');
    expect(modalSlice).not.toContain('id="trainAgentNameGroup"');
  });

  it('transforms backlog gap item into intake pre-fill values [REQ-FACT-059]', async () => {
    const { applyBacklogGapToIntake } = await import('../../../src/web/static/modules/studios/factory.js');
    const gapItem = {
      agent_id: 'hyperv-admin',
      missing_capability: 'Support snapshot creation and rollback',
      user_intent: 'Operator asked to take VM checkpoint before upgrade',
      suggested_deliverable: 'tool',
      gap_type: 'missing_tool',
    };

    const prefill = applyBacklogGapToIntake(gapItem);
    expect(prefill.targetAgentId).toBe('hyperv-admin');
    expect(prefill.seedIntent).toBe('Support snapshot creation and rollback');
    expect(prefill.objectives).toContain('Support snapshot creation and rollback');
    expect(prefill.deliverableType).toBe('tool');
  });

  it('renders Talk it out with Forge button and builds initial prompt context [REQ-FACT-063]', async () => {
    expect(html).toContain('id="factoryIntakeTalkToForgeBtn"');

    const { buildForgeInitialPrompt } = await import('../../../src/web/static/modules/studios/factory.js');
    expect(typeof buildForgeInitialPrompt).toBe('function');

    const promptWithAgent = buildForgeInitialPrompt('hyperv-admin');
    expect(promptWithAgent).toContain('hyperv-admin');
    expect(promptWithAgent).toMatch(/design a new capability/i);

    const promptDefault = buildForgeInitialPrompt('');
    expect(promptDefault).toMatch(/design a new capability/i);
  });

  it('converts display names to clean snake_case agent slugs [CARD-387]', async () => {
    const { toSnakeCase } = await import('../../../src/web/static/modules/studios/factory.js');
    expect(typeof toSnakeCase).toBe('function');
    expect(toSnakeCase('3D Scene Artist')).toBe('3d_scene_artist');
    expect(toSnakeCase('   Blender & Unity Pro!!  ')).toBe('blender_unity_pro');
    expect(toSnakeCase('my-custom_agent--name')).toBe('my_custom_agent_name');
    expect(toSnakeCase('')).toBe('');
  });
});
