# [CARD-212] LLM Provider Hybrid Credential Vault Picker

> **Status**: In Review
> **Created**: 2026-09-10
> **Spec Reference**: none
> **Labels**: `type:feature`, `domain:settings`, `domain:security`, `domain:ui`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Choose Between Existing Vault Secret or Direct Typing**:
   - In Settings Studio (`#view-settings` -> LLM Provider configuration), Jacob wants a dropdown picker that lists credentials already saved in the **Credential Vault** (`/api/vault/credentials`).
   - If an existing credential in the Vault is selected (e.g. "Google Gemini Key", "Work Anthropic Token"), the provider binds directly to that credential ID without having to re-paste the secret.
   - At the same time, Jacob still wants the flexibility to type/paste a new key directly into the input box without being forced to create a Vault entry first (Hybrid mode).
2. **Zero Duplicate Secrets**:
   - Multiple providers or purposes can reference the same saved Vault credential if desired (e.g. shared OpenRouter or OpenAI token).

---

## Beat 2: What AutoReiv Does Now
1. **Automatic Direct Vault Storage (CARD-211)**:
   - In Settings Studio, there is a password input (`#provKeyInput`) with a static "Encrypted in Vault" badge.
   - When a key is typed and saved, AutoReiv creates or updates a dedicated vault entry named `llm-provider-{pid}`.
2. **No Vault Selector in Provider Form**:
   - There is no dropdown control in the provider settings form to inspect or select from existing credentials in the Credential Vault.

---

## Beat 3: What Will Change
1. **Hybrid Credential Selector Control in Settings Studio**:
   - Above the API key input in Settings Studio, add a dropdown selector (`#provVaultCredSelect`):
     ```text
     [ Direct Secret Input (Auto-Vault)               v ]
     --------------------------------------------------
     [ Google Gemini API Key (vault: llm-provider-gemini) ]
     [ Personal Anthropic Key (vault: personal-claude)    ]
     [ Team OpenAI Key (vault: team-openai)              ]
     ```
   - If an existing Vault credential is selected from the dropdown:
     - The text input is disabled/hidden or locked with a badge indicating the linked Vault ID.
     - The provider's configuration references that specific `vault_cred_id`.
   - If "Direct Secret Input (Auto-Vault)" is selected:
     - The password input (`#provKeyInput`) is active for entering a new secret value directly.
2. **API & Model Binding**:
   - `ProviderSettingsRequest` accepts an explicit `vault_cred_id: Optional[str] = None`.
   - When `vault_cred_id` is passed, the provider links directly to that Vault credential without requiring plaintext secret submission.
3. **Live Sync with Credential Vault Table**:
   - Adding or deleting credentials in the Credential Vault table below dynamically refreshes the options inside the LLM provider vault dropdown picker.

---

## 2. Acceptance Criteria (Definition of Done)
- [x] **AC-1 (Dropdown Population)**: Settings Studio loads all credentials from `/api/vault/credentials` into the `#provVaultCredSelect` dropdown alongside a default "Direct Input (Auto-Vault)" option.
- [x] **AC-2 (Binding Existing Vault Credential)**: Selecting an existing Vault credential links the provider to that `vault_cred_id`, and saving persists the link in `provider_settings`.
- [x] **AC-3 (Direct Input Hybrid Mode)**: Selecting "Direct Input" enables `#provKeyInput` to paste/save a new secret value directly into the Vault as before.
- [x] **AC-4 (Discovery & Gateway Resolution)**: Gateway initialization and `/api/models/discover` resolve the decrypted secret from whichever `vault_cred_id` is linked to that provider.
- [x] **AC-5 (Automated Tests Green)**: Vitest frontend tests and Python integration tests verify binding, saving, and resolving existing vault credentials.

---

## 3. Constraints & Invariants
- Follow the 5 Hard Invariants from AGENTS.md.
- Feature branch `feat/llm-provider-vault-picker` cut from `qa`.
- Keep card in `Ready` status until Jacob explicitly says **build**.
