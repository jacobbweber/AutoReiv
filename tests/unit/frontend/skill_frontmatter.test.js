/**
 * CARD-411 REQ-411-001/002: structured metadata round-trips requires_tools and keeps the body.
 */

import { describe, it, expect } from 'vitest';
import { applyWorkshopMetadata, splitSkillMarkdown } from '../../../src/web/static/modules/utils/skill_frontmatter.js';

const SAMPLE = `---
name: Widget Notes
description: Read widget notes
version: 1.0.0
tier: pack
requires_tools:
  - inspect_widget
safety:
  read_only: true
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: Widget was read.
---

# Widget Notes

Keep-this-sentence.
`;

describe('skill frontmatter workshop metadata [CARD-411]', () => {
  it('adds and removes catalog tools in requires_tools without dropping the body', () => {
    const catalog = ['inspect_widget', 'wiki_note_read'];
    const added = applyWorkshopMetadata(SAMPLE, {
      name: 'Widget Notes',
      description: 'Read widget notes',
      tier: 'user',
      safety: { read_only: false, requires_hitl: true, untrusted_input_allowed: false },
      requires_tools: ['wiki_note_read', 'not_a_tool', 'wiki_note_read'],
    }, catalog);

    expect(added.requires_tools).toEqual(['wiki_note_read']);
    expect(added.rejected).toEqual(['not_a_tool']);
    expect(added.markdown).toContain('wiki_note_read');
    expect(added.markdown).not.toContain('not_a_tool');
    expect(added.markdown).toContain('Keep-this-sentence.');
    expect(added.meta.tier).toBe('user');
    expect(added.meta.safety.requires_hitl).toBe(true);
    expect(added.meta.verification.rule).toBe('Widget was read.');

    const { body } = splitSkillMarkdown(added.markdown);
    expect(body).toContain('Keep-this-sentence.');

    const removed = applyWorkshopMetadata(added.markdown, {
      requires_tools: [],
    }, catalog);
    expect(removed.requires_tools).toEqual([]);
    expect(removed.markdown).toContain('Keep-this-sentence.');
    expect(removed.markdown).not.toContain('wiki_note_read');
  });
});
