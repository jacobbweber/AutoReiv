/**
 * CARD-198: Agent Visibility ('public' vs 'internal') and Fleet Grouping [REQ-FLEET-001, REQ-FLEET-002].
 */

import { describe, it, expect } from 'vitest';
import {
  isAgentVisibleInChat,
  agentsVisibleInChat,
} from '../../../src/web/static/modules/studios/chat.js';

describe('Agent Visibility & Fleet Filtering [CARD-198]', () => {
  it('hides agents with visibility: internal from chat picker', () => {
    const homelabLead = { id: 'homelab', name: 'Homelab', visibility: 'public', show_in_chat: true };
    const homelabArchitect = { id: 'homelab-architect', name: 'Homelab Architect', visibility: 'internal', show_in_chat: false };
    const homelabEngineer = { id: 'homelab-engineer', name: 'Homelab Engineer', visibility: 'internal', show_in_chat: false };

    expect(isAgentVisibleInChat(homelabLead)).toBe(true);
    expect(isAgentVisibleInChat(homelabArchitect)).toBe(false);
    expect(isAgentVisibleInChat(homelabEngineer)).toBe(false);

    const visible = agentsVisibleInChat([homelabLead, homelabArchitect, homelabEngineer]);
    expect(visible.map((a) => a.id)).toEqual(['homelab']);
  });

  it('hides deprecated hyperv agent from chat picker', () => {
    const hypervAgent = { id: 'hyperv', name: 'Hyper-V', visibility: 'public', show_in_chat: true };
    expect(isAgentVisibleInChat(hypervAgent)).toBe(false);
  });

  it('filters homelab internal fleet specialists while retaining lead', () => {
    const fleet = [
      { id: 'homelab', name: 'Homelab Coordinator', visibility: 'public', fleet: 'homelab' },
      { id: 'homelab-architect', name: 'Homelab Architect', visibility: 'internal', fleet: 'homelab' },
      { id: 'homelab-engineer', name: 'Homelab Engineer', visibility: 'internal', fleet: 'homelab' },
      { id: 'homelab-admin', name: 'Homelab Admin', visibility: 'internal', fleet: 'homelab' },
      { id: 'homelab-janitor', name: 'Homelab Janitor', visibility: 'internal', fleet: 'homelab' },
    ];
    const filtered = agentsVisibleInChat(fleet);
    expect(filtered).toHaveLength(1);
    expect(filtered[0].id).toBe('homelab');
  });
});
