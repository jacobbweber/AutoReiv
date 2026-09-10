# [CARD-211] Per-Provider LLM Credentials and Vault Persistence

> **Status**: In Review
> **Created**: 2026-09-10
> **Spec Reference**: none
> **Labels**: `type:feature`, `domain:settings`, `domain:security`, `domain:gateway`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Never Lose Saved API Keys When Switching Providers**:
   - In Settings Studio (`#view-settings`), when you change the Provider Preset dropdown (`#provPresetSelect`) between Google Gemini, OpenAI, Anthropic, or Ollama, each provider should remember its own host URL, API key, and default model.
   - Switching providers back and forth should never clear, blank out, or overwrite previously saved API keys.
2. **Encrypted Storage via Credential Vault**:
   - Instead of storing cloud provider API keys in plaintext inside the system settings table, LLM provider API keys should be encrypted at rest with AES-256-GCM using AutoReiv's Credential Vault (`/api/vault/credentials`).
3. **Seamless Swapping**:
   - When a provider is chosen in the dropdown, the UI shows if a key is already saved for that provider (e.g. masked password dots or placeholder), populates the saved host URL, and immediately lets you test or use models without re-entering the key.

---

### Beat 2: What AutoReiv Does Now
1. **Single Shared Cloud Slot**:
   - The settings database (`provider_settings` in `settings` table) currently only stores a single `openai_api_key` and a single `openai_base_url`.
   - When switching presets in the dropdown, `settings.js` does not restore the key for the selected provider; it only updates the placeholder text.
2. **Plaintext Storage**:
   - The active API key is stored as unencrypted plaintext JSON in `database/autoreiv.db`, while the rest of AutoReiv's secrets use the encrypted Credential Vault.
3. **Overwrite on Save**:
   - Saving settings while on a different provider overwrites the single `openai_api_key` field in the database.

---

### Beat 3: What Will Change
1. **Per-Provider Configuration Dictionary**:
   - Backend `provider_settings` will store configurations mapped by provider ID:
     ```json
     {
       "default_provider_id": "gemini",
       "providers": {
         "gemini": { "base_url": "...", "model": "gemini-3.5-flash", "vault_cred_id": "llm-provider-gemini" },
         "openai": { "base_url": "...", "model": "gpt-4o", "vault_cred_id": "llm-provider-openai" },
         "anthropic": { "base_url": "...", "model": "claude-3-5-sonnet", "vault_cred_id": "llm-provider-anthropic" },
         "ollama": { "base_url": "http://192.168.1.29:11434", "model": "qwen3.8:latest" }
       }
     }
     ```
2. **Credential Vault Encryption**:
   - When an API key is saved for a provider, the secret is stored in the Credential Vault (`credentials` table) encrypted with AES-256-GCM.
   - The settings payload only stores the vault reference ID (`vault_cred_id`), keeping sensitive tokens encrypted at rest.
   - Backward compatibility: On boot, any existing legacy `openai_api_key` in `provider_settings` is automatically migrated into the encrypted vault for the active provider.
3. **Settings Studio Dropdown Hydration**:
   - In Settings Studio (`settings.js`), changing `#provPresetSelect` dynamically loads the saved host URL and indicates whether an encrypted key exists in the vault for that provider.
   - Entering a new key and clicking "Save Provider" updates that specific provider without wiping any other provider's credentials.

---

## 2. Acceptance Criteria (Definition of Done)
- [x] **AC-1 (Key Persistence Across Swaps)**: Swapping between Google Gemini, OpenAI, Anthropic, and Ollama in Settings Studio preserves each provider's URL, default model, and API key.
- [x] **AC-2 (Credential Vault Encryption)**: LLM provider API keys are encrypted at rest with AES-256-GCM via the Credential Vault, with zero plaintext keys stored in the `settings` table.
- [x] **AC-3 (Automatic Legacy Key Migration)**: Existing saved keys (including Jacob's current Google Gemini key in `autoreiv.db`) are automatically imported into the encrypted vault without data loss.
- [x] **AC-4 (UI Feedback & Masking)**: Settings Studio displays whether a key is saved for the selected provider (e.g. `••••••••` masked indicator and "Encrypted in Vault" badge) and allows overriding or updating it.
- [x] **AC-5 (Automated Tests Green)**: Python unit tests for settings provider vault persistence and Vitest frontend tests pass cleanly.

---

## 3. Constraints & Invariants
- Honor the 5 Hard Invariants from AGENTS.md.
- Feature branch `feat/provider-vault-credentials` cut from `qa`.
- No breaking changes to existing gateway adapters or agent tool runs.
- Keep card in `Ready` status until Jacob explicitly approves the build.
