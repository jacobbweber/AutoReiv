/**
 * CARD-425: packs/<id>/tools/*.py is a legacy in-process loader.
 * REQ-425-002. Catalog origin is Legacy pack tool, never Native custom.
 */

import { describe, it, expect } from 'vitest';
import {
  buildCatalogGroups,
  filterCatalogGroups,
  originLabel,
  renderCatalogMarkup,
} from '../../../src/web/static/modules/studios/tools_studio_catalog.js';

describe('Legacy pack tool catalog origin [CARD-425]', () => {
  const namespaces = [
    {
      id: 'legacy_pack_tool',
      name: 'Legacy pack tool',
      source: 'legacy_pack_tool',
      origin_label: 'Legacy pack tool',
      tools: [{ name: 'widget_ping', description: 'Legacy in-process pack tool' }],
    },
    {
      id: 'native_custom',
      name: 'Native custom',
      source: 'native_custom',
      origin_label: 'Native custom',
      tools: [{ name: 'echo_token', description: 'Echo a token' }],
    },
  ];

  it('does not label an in-process pack tool as Native custom [REQ-425-002]', () => {
    const groups = buildCatalogGroups({ namespaces });
    const legacy = groups.find((group) => group.tools.some((tool) => tool.name === 'widget_ping'));
    expect(legacy.source).toBe('legacy_pack_tool');
    expect(legacy.source).not.toBe('native_custom');
    expect(originLabel(legacy)).toBe('Legacy pack tool');
    expect(originLabel(legacy)).not.toBe('Native custom');

    const markup = renderCatalogMarkup(groups);
    expect(markup).toContain(
      'data-tool-name="widget_ping" data-source="legacy_pack_tool" data-origin="legacy_pack_tool"',
    );
    expect(markup).not.toContain('data-tool-name="widget_ping" data-source="native_custom"');
    expect(markup).not.toContain('data-origin="native_custom" data-tool-name="widget_ping"');

    const nativeOnly = filterCatalogGroups(groups, { source: 'native' });
    expect(nativeOnly.map((group) => group.source)).toEqual(['native_custom']);
    expect(renderCatalogMarkup(nativeOnly)).not.toContain('widget_ping');
    expect(renderCatalogMarkup(filterCatalogGroups(groups, { source: 'platform' }))).not.toContain('widget_ping');
  });

  it('falls back to Legacy pack tool when the API omits origin_label', () => {
    const groups = buildCatalogGroups({
      namespaces: [
        {
          id: 'legacy_pack_tool',
          name: 'Legacy pack tool',
          source: 'legacy_pack_tool',
          tools: [{ name: 'widget_ping', description: 'Legacy in-process pack tool' }],
        },
      ],
    });
    expect(originLabel(groups[0])).toBe('Legacy pack tool');
    expect(originLabel(groups[0])).not.toBe('Native custom');
  });
});
