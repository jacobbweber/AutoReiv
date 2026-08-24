# Design Specification: System Info Conceptual Knowledge Hub and Architectural Overviews

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`tasks.md`](./tasks.md)  
> **Traceability Key**: `[REQ-SYST-xxx]`

---

## 1. Architecture & Navigation Structure

```mermaid
flowchart TD
    subgraph SystemInfo_Hub ["ℹ️ System Info Knowledge Hub"]
        A["1. Platform Overview & Core Tenets"]
        B["2. 5-Tier Concept Hierarchy"]
        C["3. Skill Packs & Tools Guide"]
        D["4. Purpose Matrix & Model Sizing"]
        E["5. Multi-Agent Orchestration & Handoffs"]
        F["6. Safety, Sandboxing & HITL Guardrails"]
    end

    subgraph Service_Layer ["Backend / API"]
        G["GET /api/system-info/topics"]
        H["GET /api/system-info/topic/{topic_id}"]
        I["SystemInfoService (Python)"]
    end

    subgraph UI_Layer ["Frontend SPA"]
        J["#view-docs -> #view-system-info"]
        K["Searchable Topic Nav Bar"]
        L["Rich Markdown & Mermaid PTZ Inspector"]
    end

    A --> I
    B --> I
    C --> I
    D --> I
    E --> I
    F --> I
    I --> G
    I --> H
    G --> J
    H --> L
```

---

## 2. Topic Catalog Schema

```python
@dataclass(frozen=True)
class SystemInfoTopic:
    id: str
    title: str
    category: str
    icon: str
    summary: str
    content_markdown: str
```

---

## 3. Endpoints

- `GET /api/system-info/topics`: Returns list of categories and topic metadata for navigation sidebar.
- `GET /api/system-info/topic/{id}`: Returns full topic document with Markdown content and title.
