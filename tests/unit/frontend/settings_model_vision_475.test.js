import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

import {
  modelVisionCell,
  wireModelVisionToggles,
  visionSourceLabel,
} from '../../../src/web/static/modules/studios/settings_model_vision.js';

/** CARD-475 (D2): per-model "Can view images" checkbox after Refresh Models. */

const ROOT = path.resolve(__dirname, '../../..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf-8');
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');

describe('CARD-475 model vision checkbox', () => {
  it('renders checked for a vision model with its source', () => {
    const html = modelVisionCell({ id: 'vllm/gemma-4-26b-a4b', can_view_images: true, vision_source: 'provider' }, esc);
    expect(html).toContain('data-model-id="vllm/gemma-4-26b-a4b" checked');
    expect(html).toContain('provider says yes');
  });

  it('renders unchecked and "text only" for an unknown model', () => {
    const html = modelVisionCell({ id: 'vllm/nemotron-3.5-lightning', can_view_images: false, vision_source: 'default' }, esc);
    expect(html).not.toContain(' checked');
    expect(html).toContain('text only');
  });

  it('a tick posts the override and shows "set by you"', async () => {
    let handler = null;
    const posts = [];
    const label = { textContent: 'text only' };
    const box = {
      checked: true, disabled: false, dataset: { modelId: 'vllm/nemotron-3.5-lightning' },
      classList: { contains: (c) => c === 'model-vision-toggle' },
      parentElement: { querySelector: () => label },
    };
    const tbody = { dataset: {}, addEventListener: (t, fn) => { handler = fn; } };
    const fetchFn = async (url, opts) => {
      posts.push([url, JSON.parse(opts.body)]);
      return { ok: true, json: async () => ({ can_view_images: true, vision_source: 'override' }) };
    };
    wireModelVisionToggles(tbody, { fetchFn });
    await handler({ target: box });
    expect(posts).toEqual([['/api/settings/model-capabilities', { model_id: 'vllm/nemotron-3.5-lightning', vision: true }]]);
    expect(label.textContent).toBe(visionSourceLabel('override'));
    expect(box.checked).toBe(true);
  });

  it('a failed save reverts the checkbox', async () => {
    let handler = null;
    const box = {
      checked: true, disabled: false, dataset: { modelId: 'vllm/x' },
      classList: { contains: () => true }, parentElement: null,
    };
    const tbody = { dataset: {}, addEventListener: (t, fn) => { handler = fn; } };
    wireModelVisionToggles(tbody, { fetchFn: async () => ({ ok: false, status: 500 }) });
    await handler({ target: box });
    expect(box.checked).toBe(false);
  });

  it('settings.js renders the cell and the table has the column', () => {
    const js = read('src/web/static/modules/studios/settings.js');
    expect(js).toContain('modelVisionCell(r, escapeHtml)');
    expect(js).toContain('wireModelVisionToggles(modelFitTableBody)');
    expect(read('src/web/templates/index.html')).toContain('Can view images');
  });
});
