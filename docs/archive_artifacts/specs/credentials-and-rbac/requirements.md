# Requirements Specification: Credential Vault and Per-Agent Access Control

> **Spec Status**: Implemented  
> **Card Reference**: CARD-168  
> **Primary Component**: `AutoReiv.Security`, `AutoReiv.Agents`, `AutoReiv.Kernel`, `AutoReiv.Web`  
> **Applicable ADRs**: `docs/adr/0003-agent-kernel-scoped-tool-registry-and-sqlite-state-persistence.md`

---

## 1. Executive Summary & Intent

Automated tools and agents require sensitive secrets (cloud tokens, API keys, database connection strings, host credentials). AutoReiv provides a dedicated, encrypted local **Credential Vault** where the operator stores secrets once, and grants granular access to specific agents via direct allowlists in Agent Studio. Credentials are dynamically injected just-in-time (JIT) during tool execution, and tool outputs/transcripts are scrubbed in real-time to prevent accidental disclosure.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-VAULT-001]: Encrypted Local Credential Storage
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL persist secrets in a SQLite credentials table encrypted using AES-256-GCM with a locally-managed master key.`
- **Acceptance Criteria**:
  - [x] Given a plaintext secret and metadata, when `save_credential` is called, then the secret is encrypted with AES-256-GCM and stored alongside a random nonce.
  - [x] Given an existing credential, when retrieved via `get_credential`, then it can be decrypted back to the original plaintext.
  - [x] Given no existing vault key on disk, when initialized, then a cryptographically strong 256-bit key is generated in `$DATA_DIR/.vault_key` with strict file permissions.

### [REQ-VAULT-002]: REST API for Credential Management with Masking
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL expose REST endpoints under /api/vault/credentials to list, create, and delete credentials while strictly masking secret values on read operations.`
- **Acceptance Criteria**:
  - [x] Given a `GET /api/vault/credentials` request, when returned, then all secret values are masked (e.g. `****...abcd`) and plaintext secrets are never exposed.
  - [x] Given a `POST /api/vault/credentials` request with `id`, `name`, `type`, and `secret`, when executed, then the secret is encrypted and persisted.
  - [x] Given a `DELETE /api/vault/credentials/{id}` request, when executed, then the credential record is removed from the vault.

### [REQ-VAULT-003]: Agent Studio Credential Grants
- **Type**: Event-Driven
- **EARS Statement**: `WHEN configuring an agent in Agent Studio THE SYSTEM SHALL present available vault credentials and persist selected credential grants in allowed_credentials.`
- **Acceptance Criteria**:
  - [x] Given available vault credentials, when viewing Agent Studio, then the Credential Vault Access card renders a checklist of credentials with type badges.
  - [x] Given selected credentials, when saving the agent profile, then `allowed_credentials` is persisted to SQLite and `pack.json`.
  - [x] Given an agent loaded in Agent Studio, when rendered, then currently granted credentials are checked and the count badge reflects the total grants.

### [REQ-VAULT-004]: JIT Credential Injection into Tool Execution
- **Type**: State-Driven
- **EARS Statement**: `WHILE an agent executes a tool THE SYSTEM SHALL inject only authorized credentials from allowed_credentials into the tool context and ephemeral environment variables.`
- **Acceptance Criteria**:
  - [x] Given an agent with `allowed_credentials`, when a tool runs, then authorized secrets are decrypted and available in `get_tool_context()["credentials"]` and `AUTOREIV_CRED_<KEY>` environment variables.
  - [x] Given an agent without access to a credential, when a tool runs, then unauthorized secrets are omitted from the context.
  - [x] Given tool completion or error, when exiting execution, then ephemeral environment variables are cleaned up.

### [REQ-VAULT-005]: Real-Time Transcript and Tool Output Scrubbing
- **Type**: Event-Driven
- **EARS Statement**: `WHEN tool execution results or chat messages are processed THE SYSTEM SHALL scrub all known secret values from tool output, logs, and transcript payloads.`
- **Acceptance Criteria**:
  - [x] Given tool execution output containing a plain secret, when returned to the kernel or transcript, then the secret is replaced with `***MASKED***`.
  - [x] Given structured dict or list tool results containing secrets, when scrubbed, then nested string values are sanitized recursively.
  - [x] Given absent or empty secrets, when scrubbing, then original output is returned unmodified.
