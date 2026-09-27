/**
 * CARD-539 D6: when no agent covers a request the reply says so and offers Ask Developer as a button.
 */

import { describe, it, expect } from 'vitest';
import { offersAskDeveloper, askDeveloperButtonHtml } from '../../../src/web/static/modules/studios/chat/render.js';
import { buildAskDeveloperDraft } from '../../../src/web/static/modules/studios/chat/teach_modal.js';

describe('CARD-539 D6: Ask Developer button on a no-agent-covers reply', () => {
  it('offers the button only on agent replies that suggest Ask Developer', () => {
    expect(offersAskDeveloper('assistant', 'No agent here covers that. You can use Ask Developer to build it.')).toBe(true);
    // live QA: models paraphrase the suggestion ("ask a developer to integrate one")
    expect(offersAskDeveloper('assistant', 'For travel booking, use a travel service or ask a developer to integrate one.')).toBe(true);
    expect(offersAskDeveloper('assistant', 'You could ask the Developer agent to add it.')).toBe(true);
    expect(offersAskDeveloper('assistant', 'The developer console shows no errors.')).toBe(false);
    expect(offersAskDeveloper('assistant', 'Here is the weather.')).toBe(false);
    expect(offersAskDeveloper('user', 'Ask Developer please')).toBe(false);
  });

  it('renders a button that carries the request', () => {
    const html = askDeveloperButtonHtml('book a flight');
    expect(html).toContain('msg-ask-developer-btn');
    expect(html).toContain('Ask Developer');
    expect(html).toContain('book a flight');
  });

  it('drafts a Developer request naming the agent and the uncovered request', () => {
    const d = buildAskDeveloperDraft('Book me a flight to Denver', 'No agent covers flight booking.', 'autoreiv');
    expect(d.intent).toBe('create');
    expect(d.target_agent_id).toBe('autoreiv');
    expect(d.behavior).toContain('Book me a flight to Denver');
    expect(d.behavior).toContain('No agent covers flight booking.');
  });
});
