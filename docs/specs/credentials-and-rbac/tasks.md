# Task Breakdown: Credential Vault and Per-Agent Access Control

> **Spec Status**: Implemented  
> **Card Reference**: CARD-168  

---

## Tasks

- [x] Task 1: AES-256-GCM Credential Vault Domain & Scrubber (`[REQ-VAULT-001]`, `[REQ-VAULT-005]`)
  - [x] Implement `CredentialVault` in `src/domain/security/vault.py`.
  - [x] Implement `TranscriptScrubber` in `src/domain/security/scrubber.py`.
  - [x] Unit tests for vault encryption and scrubber.

- [x] Task 2: SQLite Credentials Repository & Migration (`[REQ-VAULT-001]`)
  - [x] Add `credentials` table schema and migration.
  - [x] Add `allowed_credentials_json` column to `agent_overrides` and `custom_agents`.
  - [x] Implement `CredentialRepositoryMixin` in `src/infrastructure/memory/repositories/credentials.py`.

- [x] Task 3: REST API Endpoints (`[REQ-VAULT-002]`)
  - [x] Implement `/api/vault/credentials` router (`GET`, `POST`, `DELETE`).
  - [x] Mount router in FastAPI app.
  - [x] Unit tests for REST API.

- [x] Task 4: JIT Tool Injection & Kernel Scrubbing (`[REQ-VAULT-004]`, `[REQ-VAULT-005]`)
  - [x] Add JIT credential injection in `ScopedToolRegistry.execute()`.
  - [x] Add `execute_and_scrub_tool()` to `AgentKernel`.
  - [x] Unit tests for JIT tool credential execution.

- [x] Task 5: Web UI in Settings Studio & Agent Studio (`[REQ-VAULT-003]`)
  - [x] Add Credential Vault UI in Settings Studio.
  - [x] Add Credential Grants UI in Agent Studio.
  - [x] Vitest tests for UI components.
