# [CARD-168] Credential Vault and Per-Agent Access Control (RBAC vs. Direct Grant)

> **Status**: Ready
> **Created**: 2026-09-05
> **Spec Reference**: docs/specs/credentials-and-rbac/
> **Labels**: `type:feature`, `AutoReiv.Security`, `AutoReiv.Agents`, `AutoReiv.Web`

---

## 1. Why / Intent

Automated tools and agents increasingly need sensitive secrets (e.g. cloud tokens, API keys, database connection strings, SSH keys, and host credentials). Currently, secrets risk being hardcoded into agent system prompts, tool scripts, or environment configs.

AutoReiv requires a dedicated, encrypted **Credential Vault** where the operator can store secrets once, and granularly control which agents are permitted to use them.

---

## 2. Access Control Architecture Brainstorming & Trade-Offs

Before implementing, we evaluate the optimal access control model for AutoReiv's architecture:

### Option A: Traditional Role-Based Access Control (RBAC)
- **Mechanism**: Define abstract roles (e.g., `InfrastructureAdmin`, `DataScientist`, `ReadOnlyObserver`). Assign roles to agents; tag credentials with required roles.
- **Pros**: Matches traditional multi-user enterprise permissions.
- **Cons**: High cognitive overhead for a single-operator local control plane. Requires managing two separate mappings (Agent $\leftrightarrow$ Role and Role $\leftrightarrow$ Secret). Overkill when an operator simply wants "Agent Hyper-V to have Credential X".

### Option B: Per-Agent Direct Allowlist / Grant (Recommended Default)
- **Mechanism**: Mirror AutoReiv's proven tool allowlist pattern (`allowed_tool_names` in `pack.json`). In Agent Studio, provide a "Granted Credentials" selector listing vault secrets by name. The agent's `pack.json` declares `allowed_credentials: ["vm_admin_key", "hyperv_host_token"]`.
- **Pros**: Direct, transparent, zero-indirection visibility. The operator sees exactly what the agent can access in Agent Studio.
- **Cons**: If managing dozens of identical agents, grants must be configured per agent (mitigated by platform default packs).

### Option C: Skill/Tool-Scoped Secret Binding
- **Mechanism**: Secrets are attached directly to specific tool schemas or skill runbooks rather than the agent.
- **Pros**: Strict least-privilege at the individual execution unit.
- **Cons**: If two agents use the same platform tool (e.g., `run_host_script`), but only one should have admin credentials, tool-level binding leaks privilege across agents.

### Option D: Just-In-Time (JIT) Sandbox Injection & Output Scrubbing
- **Mechanism**: Combines Option B with execution-time isolation. Secrets are **never** rendered into LLM prompts or chat transcripts. When the agent invokes a tool, the Kernel fetches the authorized secret from the Vault and injects it strictly as an environment variable or standard input into the sandboxed subprocess. All stdout, stderr, and chat messages pass through an active secret scrubber to prevent accidental echo leaks.

> **Recommendation**: Implement **Option B + Option D** (Direct Agent Allowlist in Agent Studio + JIT Subprocess Injection with Transcript Scrubbing). This provides maximum security with zero unnecessary enterprise indirection.

---

## 3. What to Build

### A. Backend Storage & Security (`src/domain/security/`, `src/infrastructure/database/`)
- Encrypted SQLite table `credentials` (`id`, `name`, `type`, `encrypted_value`, `description`, `created_at`, `updated_at`).
- AES-256-GCM encryption using a local master key derived from machine salt or operator passphrase.
- Endpoints under `/api/vault/credentials`:
  - `GET /api/vault/credentials` (names, types, and descriptions only; never plaintext secret values).
  - `POST /api/vault/credentials` (create/update secret).
  - `DELETE /api/vault/credentials/{id}`.

### B. Agent Studio Integration (`src/web/templates/index.html`, `src/web/static/modules/studios/forge.js`)
- Add a new "Credential Grants" section in Agent Studio.
- Multi-select checkbox grid listing available vault secrets.
- Persist authorized credential IDs into `pack.json` under `allowed_credentials`.

### C. Kernel JIT Execution & Scrubbing (`src/application/kernel/`)
- When dispatching a tool call, inspect `allowed_credentials` for the active agent.
- Inject authorized secrets into the tool runner's execution environment.
- Run deterministic regex scrubbing on tool results before returning output to LLM context or UI transcripts.

---

## 4. Acceptance Criteria (Definition of Done)

- [ ] [REQ-VAULT-001] Secure SQLite credentials repository storing AES-256-GCM encrypted values.
- [ ] [REQ-VAULT-002] REST endpoints for managing secrets with strict non-exposure of plaintext values on read.
- [ ] [REQ-VAULT-003] Agent Studio provides credential grant multi-select persisted into `pack.json` (`allowed_credentials`).
- [ ] [REQ-VAULT-004] Agent execution kernel restricts credential resolution strictly to allowed credentials for the calling agent.
- [ ] [REQ-VAULT-005] Active transcript scrubber masks secret tokens from appearing in chat history and LLM context.
- [ ] Automated unit and integration tests pass cleanly via pytest.
- [ ] Frontend tests pass cleanly via Vitest.

---

## 5. Constraints & Honor Flags

- Zero third-party product names in card, UI, or repo artifacts.
- Plaintext secrets must never touch the database unencrypted or leak into git/logs.

