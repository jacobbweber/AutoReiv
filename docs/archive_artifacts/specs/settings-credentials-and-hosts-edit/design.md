# Technical Design: Settings Studio Edit and Unmask Controls

> **Spec Status**: In Progress  
> **Card Reference**: CARD-188  
> **Primary Component**: `AutoReiv.Web`, `AutoReiv.Security`, `AutoReiv.Settings`  

---

## 1. Architecture Overview

This design enhances the operator control plane within **Settings Studio** by providing update and unmask operations for both Credential Vault entries and Remote SSH Host profiles.

```mermaid
sequenceDiagram
    autonumber
    actor Operator as Human Operator
    participant UI as Settings Studio (settings.js)
    participant CredAPI as /api/vault/credentials
    participant HostAPI as /api/remote_hosts
    participant Store as SQLiteStateStore

    Note over Operator, UI: Unmasking Secret
    Operator->>UI: Click Eye on table row (data-reveal-cred)
    UI->>CredAPI: GET /api/vault/credentials/{id}/reveal
    CredAPI->>Store: get_credential(id)
    Store-->>CredAPI: Credential(id, secret=decrypted)
    CredAPI-->>UI: { id, secret }
    UI-->>Operator: Display plaintext secret (toggleable)

    Note over Operator, UI: Editing Credential
    Operator->>UI: Click Pencil on table row (data-edit-cred)
    UI->>UI: Populate form, disable ID field
    Operator->>UI: Click Save & Encrypt
    UI->>CredAPI: POST /api/vault/credentials (id, name, type, desc, secret?)
    CredAPI->>Store: save_credential (new secret or retain existing)
    Store-->>CredAPI: success
    CredAPI-->>UI: 200 OK
    UI->>UI: Refresh table & reset form
```

---

## 2. API Contract Changes

### `GET /api/vault/credentials/{cred_id}/reveal`
- **Response** `200 OK`:
  ```json
  {
    "id": "github-token",
    "secret": "ghp_1234567890abcdef"
  }
  ```
- **Response** `404 Not Found`:
  ```json
  {
    "detail": "Credential not found"
  }
  ```

### `POST /api/vault/credentials` Update Behavior
- If `id` matches an existing credential and `secret` is omitted or empty string, the existing decrypted secret is retained while updating `name`, `type`, and `description`.
- If a new `secret` is provided, it is encrypted and saved.
