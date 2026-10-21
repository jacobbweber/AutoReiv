import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  getDefaultProviderBaseUrl,
  setCachedProviderSettings,
  discoverModelsForAgent,
  setupAgentModelConfig,
} from '../../../src/web/static/modules/studios/forge/config.js';

function makeSelect(initialValue = 'default') {
  const listeners = {};
  const el = {
    value: initialValue,
    options: [{ value: 'default', textContent: 'Use Global Default' }],
    set innerHTML(_v) {
      this.options = [{ value: 'default', textContent: 'Use Global Default' }];
    },
    appendChild(opt) {
      this.options.push(opt);
    },
    addEventListener(type, fn) {
      listeners[type] = fn;
    },
    trigger(type) {
      if (listeners[type]) return listeners[type]();
    },
  };
  return el;
}

describe('CARD-736 Agent Studio provider URL prefill and model discovery errors', () => {
  let prevDocument;
  let els;

  beforeEach(() => {
    prevDocument = globalThis.document;
    els = {
      forgeProviderSelect: makeSelect('default'),
      forgeProviderConfigContainer: {
        classList: { add: vi.fn(), remove: vi.fn() },
      },
      forgeApiBaseUrlInput: { value: '', placeholder: '' },
      forgeApiKeyInput: { value: '', placeholder: '' },
      forgeAgentModelSelect: makeSelect('default'),
      forgeDiscoverModelsBtn: {
        disabled: false,
        innerHTML: '',
        addEventListener: vi.fn(),
      },
      toastContainer: {
        children: [],
        appendChild(child) {
          this.children.push(child);
        },
      },
    };
    globalThis.document = {
      getElementById: (id) => els[id] || null,
      querySelector: () => null,
      createElement: (tag) => ({
        tag,
        value: '',
        textContent: '',
        className: '',
        innerHTML: '',
        setAttribute: vi.fn(),
        querySelector: () => null,
        classList: { add: vi.fn(), remove: vi.fn() },
        remove: vi.fn(),
      }),
    };
    setCachedProviderSettings(null);
  });

  afterEach(() => {
    globalThis.document = prevDocument;
    vi.restoreAllMocks();
  });

  it('prefers saved provider base_url from provider_settings over PRESETS_DEFAULTS localhost', () => {
    setCachedProviderSettings({
      default_provider_id: 'vllm',
      ollama_host: 'http://192.168.1.29:11434',
      providers: {
        vllm: { base_url: 'http://192.168.1.218:8099/v1' },
        ollama: { base_url: 'http://192.168.1.29:11434' },
      },
    });

    expect(getDefaultProviderBaseUrl('ollama')).toBe('http://192.168.1.29:11434');
    expect(getDefaultProviderBaseUrl('vllm')).toBe('http://192.168.1.218:8099/v1');
    expect(getDefaultProviderBaseUrl('lmstudio')).toBe('http://127.0.0.1:1234/v1');
    expect(getDefaultProviderBaseUrl('default')).toBe('');
  });

  it('switching provider in Agent Studio pre-fills saved provider URL and auto-discovers live models', async () => {
    setCachedProviderSettings({
      default_provider_id: 'vllm',
      providers: {
        vllm: { base_url: 'http://192.168.1.218:8099/v1' },
        ollama: { base_url: 'http://192.168.1.29:11434' },
      },
    });

    const fetchedUrls = [];
    globalThis.fetch = vi.fn(async (url) => {
      fetchedUrls.push(String(url));
      return {
        ok: true,
        json: async () => ({
          models: [{ id: 'ollama/qwen3.8:latest', name: 'qwen3.8:latest', provider: 'ollama' }],
          using_fallback_presets: false,
          discovery_error: null,
        }),
      };
    });

    setupAgentModelConfig();
    els.forgeProviderSelect.value = 'ollama';
    await els.forgeProviderSelect.trigger('change');
    await new Promise((r) => setTimeout(r, 10));

    expect(els.forgeApiBaseUrlInput.value).toBe('http://192.168.1.29:11434');
    expect(fetchedUrls).toEqual([
      '/api/models/discover?provider_id=ollama&host_url=http%3A%2F%2F192.168.1.29%3A11434',
    ]);
    const optionValues = els.forgeAgentModelSelect.options.map((o) => o.value);
    expect(optionValues).toContain('qwen3.8:latest');
  });

  it('surfaces a warning toast and marks fallback options when using_fallback_presets is true', async () => {
    els.forgeProviderSelect.value = 'ollama';
    els.forgeApiBaseUrlInput.value = 'http://192.268.1.29:11434';

    globalThis.fetch = vi.fn(async () => ({
      ok: true,
      json: async () => ({
        models: [{ id: 'ollama/llama3.2:1b', name: 'llama3.2:1b', provider: 'ollama' }],
        using_fallback_presets: true,
        discovery_error: 'All connection attempts failed',
      }),
    }));

    await discoverModelsForAgent();

    const toastText = els.toastContainer.children.map((c) => c.innerHTML || c.textContent).join(' ');
    expect(toastText).toContain('All connection attempts failed');
    expect(toastText).not.toContain('Discovered 1 model(s) for ollama');
    const optLabels = els.forgeAgentModelSelect.options.map((o) => o.textContent);
    expect(optLabels.some((t) => t.includes('llama3.2:1b') && t.toLowerCase().includes('preset'))).toBe(true);
  });
});
