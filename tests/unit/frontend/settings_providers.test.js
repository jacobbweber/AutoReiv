import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { PRESETS_DEFAULTS, resolveActiveDefaultModelSelection } from '../../../src/web/static/modules/studios/settings.js';

const repoRoot = path.resolve(process.cwd());

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

  it('configures Google Gemini with official key placeholder [CARD-211]', () => {
    expect(PRESETS_DEFAULTS.gemini.keyPlaceholder).toBe('AIzaSy...');
  });

  it('configures Anthropic with official key placeholder [CARD-211]', () => {
    expect(PRESETS_DEFAULTS.anthropic.keyPlaceholder).toBe('sk-ant-...');
  });
});

describe('Settings Studio Hybrid Credential Vault Picker [CARD-212]', () => {
  const indexHtml = fs.readFileSync(path.join(repoRoot, 'src/web/templates/index.html'), 'utf-8');
  const settingsJs = fs.readFileSync(path.join(repoRoot, 'src/web/static/modules/studios/settings.js'), 'utf-8');

  it('renders credential source dropdown and direct key container in index.html', () => {
    expect(indexHtml).toContain('id="provVaultCredSelect"');
    expect(indexHtml).toContain('Direct Secret Input (Auto-Vault)');
    expect(indexHtml).toContain('id="provDirectKeyContainer"');
    expect(indexHtml).toContain('id="provKeyVaultBadgeText"');
  });

  it('wires hybrid credential source selection and dropdown population in settings.js', () => {
    expect(settingsJs).toContain('provVaultCredSelect');
    expect(settingsJs).toContain('updateKeyInputForVaultSelection');
    expect(settingsJs).toContain('populateVaultCredDropdown');
    expect(settingsJs).toContain('vault_cred_id');
  });
});



describe('Settings Studio Refresh Models honesty [CARD-290]', () => {
  const settingsJs = fs.readFileSync(path.join(repoRoot, 'src/web/static/modules/studios/settings.js'), 'utf-8');

  it('exports resolveActiveDefaultModelSelection helper', () => {
    expect(typeof resolveActiveDefaultModelSelection).toBe('function');
  });

  it('preselects saved default only when present in live list', () => {
    const r = resolveActiveDefaultModelSelection({
      liveModelNames: ['qwen3.8-27b-fp8', 'other'],
      savedDefault: 'qwen3.8-27b-fp8',
      currentSelected: 'default',
    });
    expect(r.selected).toBe('qwen3.8-27b-fp8');
    expect(r.staleSaved).toBeNull();
    expect(r.usedLiveFallback).toBe(false);
  });

  it('clears ghost saved default not on live endpoint and falls back to first live model', () => {
    const r = resolveActiveDefaultModelSelection({
      liveModelNames: ['qwen3.8-27b-fp8'],
      savedDefault: 'Qwen/Qwen2.5-Coder-32B-Instruct',
      currentSelected: 'Qwen/Qwen2.5-Coder-32B-Instruct',
    });
    expect(r.selected).toBe('qwen3.8-27b-fp8');
    expect(r.staleSaved).toBe('Qwen/Qwen2.5-Coder-32B-Instruct');
    expect(r.usedLiveFallback).toBe(true);
  });

  it('allows single-model vLLM lists without padding', () => {
    const r = resolveActiveDefaultModelSelection({
      liveModelNames: ['qwen3.8-27b-fp8'],
      savedDefault: 'default',
      currentSelected: 'default',
    });
    expect(r.selected).toBe('default');
    expect(r.staleSaved).toBeNull();
  });

  it('does not inject Custom/Saved ghost option in discoverAndPopulateModels', () => {
    expect(settingsJs).not.toMatch(/\(Custom \/ Saved\)`/);
    expect(settingsJs).not.toContain('savedOpt.textContent');
    expect(settingsJs).toContain('resolveActiveDefaultModelSelection');
  });
});
