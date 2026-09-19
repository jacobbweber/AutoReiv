# Technical Design Specification: Provider & Model Settings Persistence

> **Document ID**: `DESIGN-SETTINGS-PERSIST-001`  
> **Status**: Approved  
> **Traceability ID**: `[REQ-SET-007]`, `[REQ-SET-008]`

---

## 1. Architectural Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as Human Operator
    participant UI as Settings Studio (app.js)
    participant API as FastAPI Router (app.py)
    participant Store as SQLite StateStore
    participant Gateway as MultiProviderGateway

    User->>UI: Selects Provider (Ollama) & Model (3.8)
    User->>UI: Clicks [Save Provider]
    UI->>API: POST /api/settings/providers { default_provider_id: "ollama", default_model_id: "llama3.8", ... }
    API->>Store: set_setting("provider_settings", payload)
    API->>Gateway: register_provider() & set default_model_id
    API-->>UI: { status: "saved", providers: { ... } }
    UI->>UI: Retains selected model (llama3.8) in state & UI
    Note over User,Store: Next Page Refresh
    UI->>API: GET /api/settings
    API->>Store: get_setting("provider_settings")
    API-->>UI: { providers: { default_provider_id: "ollama", default_model_id: "llama3.8", ... } }
    UI->>UI: Hydrates provPresetSelect ("ollama") & provModelSelect ("llama3.8")
```

---

## 2. Data Contract Changes

### `ProviderSettingsRequest` (`src/web/app.py`)
```python
class ProviderSettingsRequest(BaseModel):
    ollama_host: Optional[str] = "http://127.0.0.1:11434"
    openai_base_url: Optional[str] = "https://api.openai.com/v1"
    openai_api_key: Optional[str] = None
    default_provider_id: Optional[str] = "ollama"
    default_model_id: Optional[str] = "default"
```
