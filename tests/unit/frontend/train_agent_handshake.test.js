/**
 * Unit tests for Chat Studio Socratic Handshake UX & Factory Loop Integration [REQ-FACT-005, REQ-FACT-014].
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

import {
  buildTrainAgentPayload,
  renderTrainPromotionCard,
  submitTrainAgentJob,
  populateTrainAgentTargetOptions,
  updateTrainAgentLiveIndicator,
} from '../../../src/web/static/modules/studios/chat.js';
import { renderToolBadgeHtml, populateTrainModalForRetry } from '../../../src/web/static/modules/studios/forge.js';

const repoRoot = path.resolve(__dirname, '../../..');

function readIndexHtml() {
  return fs.readFileSync(path.join(repoRoot, 'src/web/templates/index.html'), 'utf-8');
}

describe('Socratic Handshake & Train Agent DOM Contract [REQ-FACT-005]', () => {
  it('index.html contains Train Agent toggle and active badge', () => {
    const html = readIndexHtml();
    expect(html).toContain('id="trainAgentToggle"');
    expect(html).toContain('id="trainAgentBadge"');
    expect(html).toContain('Train Agent');
  });

  it('index.html contains #trainAgentHandshakeModal with target, objectives, deliverable taxonomy, and risk policy', () => {
    const html = readIndexHtml();
    expect(html).toContain('id="trainAgentHandshakeModal"');
    expect(html).toContain('id="trainSeedIntentInput"');
    expect(html).toContain('id="trainTargetLocation"');
    expect(html).toContain('id="startTrainAgentBtn"');
    expect(html).toContain('id="cancelTrainAgentBtn"');
    expect(html).toContain('name="trainTargetType"');
    expect(html).toContain('id="trainSeedObjectives"');
    expect(html).toContain('id="trainDeliverableType"');
    expect(html).toContain('id="toggleTrainAdvancedReqsBtn"');
    expect(html).toContain('id="trainConstraintsInput"');
    expect(html).toContain('id="trainPrerequisitesInput"');
    expect(html).toContain('id="trainReferenceDocsInput"');
    expect(html).toContain('id="trainRequireApproval"');
  });

  it('index.html contains Train in Lab and omits redundant Train New in Agent Studio', () => {
    const html = readIndexHtml();
    expect(html).not.toContain('id="forgeTrainNewAgentBtn"');
    expect(html).toContain('id="forgeTrainAgentBtn"');
    expect(html).toContain('Train in Lab');
  });
});

describe('Train Agent Payload Builder [REQ-FACT-005]', () => {
  it('builds structured factory job payload from modal inputs', () => {
    const payload = buildTrainAgentPayload({
      seedIntent: 'Build a Palworld game server agent',
      targetType: 'remote',
      targetLocation: '192.168.1.150',
      objectives: ['Server Lifecycle', 'Config Management'],
      requireApproval: true,
      sessionId: 'sess_123',
    });

    expect(payload.target_agent_id).toBe('palworld-game-server-agent');
    expect(payload.seed_intent).toBe('Build a Palworld game server agent');
    expect(payload.target_host).toBe('192.168.1.150');
    expect(payload.objectives).toHaveLength(2);
    expect(payload.risk_policy).toBe('ask');
    expect(payload.session_id).toBe('sess_123');
  });

  it('handles local directory target location', () => {
    const payload = buildTrainAgentPayload({
      seedIntent: 'Personal Finance Agent',
      targetType: 'local',
      targetLocation: 'C:/Users/jacob/finances',
      objectives: ['Track Expenses'],
      requireApproval: false,
    });

    expect(payload.target_agent_id).toBe('personal-finance-agent');
    expect(payload.target_host).toBeNull();
    expect(payload.target_directory).toBe('C:/Users/jacob/finances');
    expect(payload.risk_policy).toBe('run');
  });

  it('supports explicit targetAgentId from Agent Studio selection', () => {
    const payload = buildTrainAgentPayload({
      seedIntent: 'Upgrade game server skills',
      targetAgentId: 'palworld-host',
      targetType: 'local',
      targetLocation: 'D:/palworld',
      objectives: ['Automate backups'],
      requireApproval: true,
    });

    expect(payload.target_agent_id).toBe('palworld-host');
    expect(payload.seed_intent).toBe('Upgrade game server skills');
    expect(payload.target_directory).toBe('D:/palworld');
  });

  it('includes deliverable taxonomy and advanced constraints [REQ-DELIV-003]', () => {
    const payload = buildTrainAgentPayload({
      seedIntent: 'Automate Docker swarm deployments',
      targetType: 'local',
      targetLocation: 'D:/docker',
      objectives: ['Deploy stack', 'Scale service'],
      requireApproval: true,
      deliverableType: 'mcp',
      constraints: 'read-only mode',
      prerequisites: 'docker cli',
      referenceDocs: 'https://docs.docker.com',
    });

    expect(payload.deliverable_type).toBe('mcp');
    expect(payload.constraints).toBe('read-only mode');
    expect(payload.prerequisites).toBe('docker cli');
    expect(payload.reference_docs).toBe('https://docs.docker.com');
  });
});

describe('Agent Studio Deliverable Badges [REQ-DELIV-003, REQ-DELIV-006]', () => {
  it('renders Native Tool badge for local atomic tools', () => {
    const html = renderToolBadgeHtml({ name: 'calc_discount' });
    expect(html).toContain('Native Tool');
    expect(html).toContain('bg-slate-800/80');
  });

  it('renders MCP Server badge for MCP-backed tools and servers', () => {
    // 1. Tool object with deliverable_type = 'mcp'
    expect(renderToolBadgeHtml({ name: 'docker_ps', deliverable_type: 'mcp' })).toContain('MCP Server');

    // 2. Tool with mcp_ prefix
    expect(renderToolBadgeHtml('mcp_github_issues')).toContain('MCP Server');

    // 3. Agent pack with mcp_server enabled
    const agent = { mcp_server: { enabled: true } };
    expect(renderToolBadgeHtml({ name: 'custom_query' }, agent)).toContain('MCP Server');
    expect(renderToolBadgeHtml({ name: 'custom_query' }, agent)).toContain('bg-indigo-950/80');
  });
});

describe('Train Agent API Dispatch [REQ-FACT-005]', () => {
  it('dispatches POST to /api/agent_training_factory/jobs', async () => {
    let calledUrl = '';
    let calledBody = null;
    const mockFetch = async (url, opts) => {
      calledUrl = url;
      calledBody = JSON.parse(opts.body);
      return {
        ok: true,
        json: async () => ({ success: true, job_id: 'fjob_test_01', status: 'queued' }),
      };
    };

    const payload = {
      target_agent_id: 'test-agent',
      seed_intent: 'Test agent intent',
      objectives: [],
      risk_policy: 'ask',
    };

    const result = await submitTrainAgentJob(payload, mockFetch);
    expect(calledUrl).toBe('/api/agent_training_factory/jobs');
    expect(calledBody.target_agent_id).toBe('test-agent');
    expect(result.job_id).toBe('fjob_test_01');
  });
});

describe('Promotion Review Card UI [REQ-FACT-014]', () => {
  it('renders promotion review card HTML with score badge and action buttons', () => {
    const jobData = {
      job_id: 'fjob_001',
      target_agent_id: 'game-agent',
      seed_intent: 'Palworld server host',
      tools_authored: ['manage_palworld_server'],
      stages_passed: 4,
    };

    const cardHtml = renderTrainPromotionCard(jobData);
    expect(cardHtml).toContain('factory-promotion-card');
    expect(cardHtml).toContain('game-agent');
    expect(cardHtml).toContain('Approve &amp; Deploy');
    expect(cardHtml).toContain('data-job-id="fjob_001"');
    expect(cardHtml).toContain('manage_palworld_server');
  });

  it('index.html contains #trainAgentNameGroup, #trainAgentNameInput, and autocomplete=off', () => {
    const html = readIndexHtml();
    expect(html).toContain('id="trainAgentNameGroup"');
    expect(html).toContain('id="trainAgentNameInput"');
    expect(html).toContain('id="trainTargetLocation" autocomplete="off"');
    expect(html).toContain('id="trainAgentNameInput" autocomplete="off"');
  });
});

describe('Lab Monitor Drawer DOM & Contract [REQ-FACT-019, REQ-FACT-022]', () => {
  it('index.html contains Lab Monitor toolbar button and active runs badge', () => {
    const html = readIndexHtml();
    expect(html).toContain('id="forgeLabMonitorBtn"');
    expect(html).toContain('id="forgeLabRunsBadge"');
    expect(html).toContain('Lab Monitor');
  });

  it('index.html contains #labMonitorDrawer with 5-stage stepper, live feed, and hitl card', () => {
    const html = readIndexHtml();
    expect(html).toContain('id="labMonitorDrawer"');
    expect(html).toContain('id="labJobSelect"');
    expect(html).toContain('id="labJobStatusPill"');
    expect(html).toContain('id="labStepperContainer"');
    expect(html).toContain('id="labStep1"');
    expect(html).toContain('id="labStep2"');
    expect(html).toContain('id="labStep3"');
    expect(html).toContain('id="labStep4"');
    expect(html).toContain('id="labStep5"');
    expect(html).toContain('id="labHitlCard"');
    expect(html).toContain('id="labApproveDeployBtn"');
    expect(html).toContain('id="labRejectDeployBtn"');
    expect(html).toContain('id="labPacketsFeed"');
  });

  it('index.html guarantees #labMonitorDrawer is an independent sibling, not nested inside #agentBrainDrawer', () => {
    const html = readIndexHtml();
    const brainDrawerIdx = html.indexOf('id="agentBrainDrawer"');
    const labDrawerIdx = html.indexOf('id="labMonitorDrawer"');
    expect(brainDrawerIdx).toBeGreaterThan(-1);
    expect(labDrawerIdx).toBeGreaterThan(brainDrawerIdx);

    // Extract the substring between agentBrainDrawer and labMonitorDrawer
    const intermediate = html.slice(brainDrawerIdx, labDrawerIdx);
    // Count opening vs closing divs in intermediate
    const openDivs = (intermediate.match(/<div(\s|>)/g) || []).length;
    const closeDivs = (intermediate.match(/<\/div>/g) || []).length;
    // agentBrainDrawer must be closed before labMonitorDrawer opens
    expect(closeDivs).toBeGreaterThanOrEqual(openDivs);
  });
});

describe('Explicit Target Agent Selector & Live Pack Indicator [REQ-FACT-043]', () => {
  it('index.html contains #trainAgentTargetSelect and #trainAgentLiveInfo components', () => {
    const html = readIndexHtml();
    expect(html).toContain('id="trainAgentTargetSelect"');
    expect(html).toContain('id="trainAgentLiveInfo"');
    expect(html).toContain('id="trainAgentLivePackPath"');
    expect(html).toContain('id="trainAgentLiveCounts"');
    expect(html).toContain('id="trainAgentLiveInfoText"');
  });

  it('populates #trainAgentTargetSelect with registered agents and brand new agent option', () => {
    const mockSelect = {
      innerHTML: '',
      value: '',
      children: [],
      appendChild(el) {
        this.children.push(el);
      },
    };

    const agents = [
      { id: 'autoreiv', name: 'AutoReiv' },
      { id: 'developer', name: 'Developer' },
      { id: 'researcher', name: 'Researcher' },
    ];

    populateTrainAgentTargetOptions(mockSelect, agents, 'developer');

    expect(mockSelect.children.length).toBe(4);
    expect(mockSelect.children[0].value).toBe('autoreiv');
    expect(mockSelect.children[1].value).toBe('developer');
    expect(mockSelect.children[2].value).toBe('researcher');
    expect(mockSelect.children[3].value).toBe('__new__');
    expect(mockSelect.children[3].textContent).toContain('Create Brand New Agent');
    expect(mockSelect.value).toBe('developer');
  });

  it('updates live indicator and toggles name group for existing agent vs __new__', () => {
    const nameGroupClasses = new Set(['hidden']);
    const liveInfoClasses = new Set(['hidden']);

    const elements = {
      nameGroup: {
        classList: {
          contains: (cls) => nameGroupClasses.has(cls),
          add: (cls) => nameGroupClasses.add(cls),
          remove: (cls) => nameGroupClasses.delete(cls),
        },
      },
      liveInfo: {
        classList: {
          contains: (cls) => liveInfoClasses.has(cls),
          add: (cls) => liveInfoClasses.add(cls),
          remove: (cls) => liveInfoClasses.delete(cls),
        },
      },
      livePackPath: { textContent: '' },
      liveCounts: { textContent: '' },
      liveInfoText: { textContent: '' },
      modalTitle: { innerHTML: '' },
      intentInput: { placeholder: '', value: '' },
      seedObj: { placeholder: '' },
    };

    const agents = [
      {
        id: 'developer',
        name: 'Developer',
        description: 'Software engineer and system architect',
        pack_skills: [{ id: 'git_workflow' }, { id: 'code_review' }],
        allowed_tool_names: ['run_command', 'view_file', 'replace_file_content'],
      },
    ];

    // Case 1: Existing agent selected
    updateTrainAgentLiveIndicator(elements, 'developer', agents);

    expect(nameGroupClasses.has('hidden')).toBe(true);
    expect(liveInfoClasses.has('hidden')).toBe(false);
    expect(elements.livePackPath.textContent).toBe('packs/developer/');
    expect(elements.liveCounts.textContent).toBe('2 skills · 3 tools');
    expect(elements.liveInfoText.textContent).toContain('Developer');
    expect(elements.liveInfoText.textContent).toContain('Augmenting');

    // Case 2: Brand new agent selected
    updateTrainAgentLiveIndicator(elements, '__new__', agents);

    expect(nameGroupClasses.has('hidden')).toBe(false);
    expect(liveInfoClasses.has('hidden')).toBe(true);
  });

  it('populateTrainModalForRetry updates trainAgentTargetSelect with retried agent ID', () => {
    const targetSelect = { value: '' };
    const nameGroup = { classList: { remove: () => {}, add: () => {} } };
    const nameInput = { value: '' };
    const jobData = {
      job: {
        target_agent_id: 'developer',
        seed_intent: 'Add git status tool',
      },
    };

    populateTrainModalForRetry(jobData, {
      trainAgentTargetSelect: targetSelect,
      nameGroup,
      nameInput,
    });

    expect(targetSelect.value).toBe('developer');
  });
});

