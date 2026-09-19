# Technical Design: Credential Vault and Per-Agent Access Control

> **Spec Status**: Implemented  
> **Card Reference**: CARD-168  
> **Primary Component**: `AutoReiv.Security`, `AutoReiv.Agents`, `AutoReiv.Kernel`, `AutoReiv.Web`  

---

## 1. Architecture Overview

The Credential Vault provides secure, encrypted credential storage with per-agent access control, just-in-time injection, and transcript secret scrubbing.

```
+-------------------------------------------------------------------+
|                        AutoReiv Web UI                            |
|  Settings Studio: Credential Vault   Agent Studio: Direct Grants  |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                           REST API                                |
|          /api/vault/credentials (GET, POST, DELETE)               |
|          /api/agents/{id} (with allowed_credentials)              |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                    SQLite State Store (WAL)                       |
|           credentials table (AES-256-GCM encrypted)               |
|      agent_overrides & custom_agents (allowed_credentials_json)   |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|               Kernel Execution & Scrubber Loop                    |
|  1. Decrypt allowed secrets -> inject into context & env vars     |
|  2. Execute tool                                                  |
|  3. Clean up ephemeral env vars in finally block                  |
|  4. TranscriptScrubber masks all secret values -> ***MASKED***   |
+-------------------------------------------------------------------+
```

---

## 2. Key Modules & Interfaces

- `src/domain/security/vault.py`: `CredentialVault` manages local key generation/retrieval (`.vault_key`) and AES-256-GCM encryption/decryption.
- `src/domain/security/scrubber.py`: `TranscriptScrubber` handles exact-token replacement across strings, dicts, and lists with `***MASKED***`.
- `src/infrastructure/memory/repositories/credentials.py`: `CredentialRepositoryMixin` provides SQLite persistence for credentials with masked reads.
- `src/application/kernel/tool_registry.py`: `ScopedToolRegistry` dynamically resolves authorized secrets, injects `_tool_context["credentials"]` and `AUTOREIV_CRED_<KEY>` environment variables, and cleans them up in a `finally` block.
- `src/application/kernel/agent_kernel.py`: `AgentKernel` executes tools via `execute_and_scrub_tool` and filters all transcripts/outputs before saving or sending.
- `src/web/routers/credentials.py`: FastAPI router exposing `/api/vault/credentials`.
