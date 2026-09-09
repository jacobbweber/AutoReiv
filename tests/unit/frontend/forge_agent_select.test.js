/**
 * CARD-202: Alphabetized Agent Studio Picker [AC-1, AC-2, AC-3].
 */

import { describe, it, expect } from 'vitest';
import {
  formatAgentSelectOption,
  sortStudioAgentsAlphabetically,
  populateForgeAgentSelectOptions,
} from '../../../src/web/static/modules/studios/forge.js';

describe('Agent Studio Alphabetized Picker [CARD-202]', () => {
  it('formats platform and custom agents with uniform tags', () => {
    const platformAgent = { id: 'autoreiv', name: 'AutoReiv', is_platform_pack: true };
    const builtinAgent = { id: 'assistant', name: 'Assistant', is_builtin: true };
    const customAgent = { id: 'my-bot', name: 'My Bot', is_platform_pack: false, is_builtin: false };

    expect(formatAgentSelectOption(platformAgent)).toBe('AutoReiv (Platform)');
    expect(formatAgentSelectOption(builtinAgent)).toBe('Assistant (Platform)');
    expect(formatAgentSelectOption(customAgent)).toBe('My Bot (Custom)');
  });

  it('sorts agents alphabetically by display name (A to Z)', () => {
    const agents = [
      { id: 'homelab', name: 'Homelab Coordinator' },
      { id: 'autoreiv', name: 'AutoReiv' },
      { id: 'homelab-janitor', name: 'Homelab Janitor' },
      { id: 'homelab-admin', name: 'Homelab Admin' },
      { id: 'assistant', name: 'Assistant' },
    ];

    const sorted = sortStudioAgentsAlphabetically(agents);
    expect(sorted.map((a) => a.name)).toEqual([
      'Assistant',
      'AutoReiv',
      'Homelab Admin',
      'Homelab Coordinator',
      'Homelab Janitor',
    ]);
  });

  it('populates select element with options and zero optgroups', () => {
    const mockOptions = [];
    const mockSelect = {
      innerHTML: 'previous',
      value: '',
      appendChild: (child) => mockOptions.push(child),
    };

    const origDoc = global.document;
    global.document = {
      createElement: (tag) => ({ tag, value: '', textContent: '' }),
    };

    try {
      const agents = [
        { id: 'z-agent', name: 'Zebra Agent', is_builtin: false },
        { id: 'a-agent', name: 'Alpha Agent', is_platform_pack: true },
      ];

      const activeId = populateForgeAgentSelectOptions(mockSelect, agents, 'z-agent');

      expect(mockSelect.innerHTML).toBe('');
      expect(mockOptions).toHaveLength(2);
      expect(mockOptions[0].value).toBe('a-agent');
      expect(mockOptions[0].textContent).toBe('Alpha Agent (Platform)');
      expect(mockOptions[1].value).toBe('z-agent');
      expect(mockOptions[1].textContent).toBe('Zebra Agent (Custom)');
      expect(activeId).toBe('z-agent');
      expect(mockSelect.value).toBe('z-agent');
    } finally {
      global.document = origDoc;
    }
  });
});
