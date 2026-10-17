import { describe, expect, it, vi } from 'vitest';
import {
  PROBE_LOCAL_URL,
  activateLocalModel,
  scanLocalServers,
} from '../../../src/web/static/modules/studios/settings_local_model_probe.js';

function makeEls() {
  const appendedCards = [];
  const appendedOptions = [];
  const doc = {
    createElement: (tag) => {
      if (tag === 'option') {
        return { value: '', textContent: '' };
      }
      const listeners = {};
      const attrs = {};
      const useBtn = {
        disabled: false,
        textContent: 'Use Model',
        addEventListener: (ev, fn) => {
          listeners[ev] = fn;
        },
        click: () => listeners.click && listeners.click(),
      };
      return {
        tagName: tag,
        className: '',
        innerHTML: '',
        attrs,
        setAttribute: (k, v) => {
          attrs[k] = v;
        },
        querySelector: (sel) => (sel === '[data-use-local-model]' ? useBtn : null),
        useBtn,
      };
    },
  };
  return {
    doc,
    appendedCards,
    scanBtn: { disabled: false },
    status: { textContent: '', className: '' },
    results: {
      innerHTML: '',
      appendChild: (el) => appendedCards.push(el),
    },
    presetSelect: { value: 'ollama' },
    hostInput: { value: 'http://127.0.0.1:11434' },
    modelSelect: {
      value: 'default',
      options: appendedOptions,
      appendChild: (opt) => appendedOptions.push(opt),
    },
    activeProviderTag: { textContent: 'ollama' },
  };
}

describe('CARD-703 local model auto-probing in Settings Studio', () => {
  it('scans local servers, renders discovered model cards, and activates a model in one click', async () => {
    const els = makeEls();
    const calls = [];
    const fetchFn = vi.fn(async (url, opts) => {
      const body = JSON.parse(opts?.body || '{}');
      calls.push({ url, body });
      if (body.activate) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            status: 'activated',
            activated: body.activate,
          }),
        };
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({
          total_servers: 1,
          total_models: 1,
          servers: [
            {
              provider_id: 'vllm',
              host: '127.0.0.1',
              port: 8006,
              base_url: 'http://127.0.0.1:8006/v1',
              models: ['nvidia/Nemotron-3-Super-120B-A12B-NVFP4'],
              latency_ms: 4.2,
            },
          ],
          models: [
            {
              provider_id: 'vllm',
              host: '127.0.0.1',
              port: 8006,
              base_url: 'http://127.0.0.1:8006/v1',
              model: 'nvidia/Nemotron-3-Super-120B-A12B-NVFP4',
              latency_ms: 4.2,
            },
          ],
        }),
      };
    });

    await scanLocalServers(els, { fetchFn });
    expect(calls[0].url).toBe(PROBE_LOCAL_URL);
    expect(els.status.textContent).toContain('Discovered 1 model(s) across 1 local server(s).');
    expect(els.appendedCards.length).toBe(1);
    expect(els.appendedCards[0].attrs['data-model-id']).toBe(
      'nvidia/Nemotron-3-Super-120B-A12B-NVFP4',
    );

    const res = await activateLocalModel(
      {
        provider_id: 'vllm',
        base_url: 'http://127.0.0.1:8006/v1',
        model: 'nvidia/Nemotron-3-Super-120B-A12B-NVFP4',
      },
      els,
      { fetchFn },
    );
    expect(res?.status).toBe('activated');
    expect(els.presetSelect.value).toBe('vllm');
    expect(els.hostInput.value).toBe('http://127.0.0.1:8006/v1');
    expect(els.modelSelect.value).toBe('nvidia/Nemotron-3-Super-120B-A12B-NVFP4');
    expect(els.activeProviderTag.textContent).toBe('vllm');
  });
});
