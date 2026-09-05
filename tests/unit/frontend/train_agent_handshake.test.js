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
} from '../../../src/web/static/modules/studios/chat.js';

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

  it('index.html contains #trainAgentHandshakeModal with target, objectives, and risk policy', () => {
    const html = readIndexHtml();
    expect(html).toContain('id="trainAgentHandshakeModal"');
    expect(html).toContain('id="trainTargetLocation"');
    expect(html).toContain('id="startTrainAgentBtn"');
    expect(html).toContain('id="cancelTrainAgentBtn"');
    expect(html).toContain('name="trainTargetType"');
    expect(html).toContain('id="trainSeedObjectives"');
    expect(html).toContain('id="trainRequireApproval"');
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
});

describe('Train Agent API Dispatch [REQ-FACT-005]', () => {
  it('dispatches POST to /api/factory/jobs', async () => {
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
    expect(calledUrl).toBe('/api/factory/jobs');
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
});
