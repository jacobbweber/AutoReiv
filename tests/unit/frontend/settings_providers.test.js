import { describe, it, expect } from 'vitest';
import { PRESETS_DEFAULTS } from '../../../src/web/static/modules/studios/settings.js';

describe('Settings Studio LLM Provider Presets [CARD-128]', () => {
  const expectedProviders = [
    'ollama',
    'lmstudio',
    'vllm',
    'gemini',
    'openai',
    'anthropic',
    'openrouter',
    'groq',
    'deepseek',
    'together',
  ];

  it('includes all 10 provider presets in PRESETS_DEFAULTS', () => {
    expectedProviders.forEach((id) => {
      expect(PRESETS_DEFAULTS[id], `Missing preset default for '${id}'`).toBeDefined();
      expect(PRESETS_DEFAULTS[id].url).toBeTruthy();
    });
  });

  it('configures LM Studio with port 1234 and local placeholder', () => {
    expect(PRESETS_DEFAULTS.lmstudio.url).toBe('http://127.0.0.1:1234/v1');
    expect(PRESETS_DEFAULTS.lmstudio.keyPlaceholder).toContain('Optional');
  });

  it('configures Google Gemini with official OpenAI compatible endpoint', () => {
    expect(PRESETS_DEFAULTS.gemini.url).toBe('https://generativelanguage.googleapis.com/v1beta/openai');
  });

  it('configures vLLM with port 8000', () => {
    expect(PRESETS_DEFAULTS.vllm.url).toBe('http://127.0.0.1:8000/v1');
  });
});
