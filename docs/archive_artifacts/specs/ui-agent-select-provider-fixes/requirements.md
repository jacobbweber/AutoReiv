# Requirements Specification: Chat Studio Agent Selection & Provider Model Discovery Fixes

> **Document ID**: `SPEC-UI-001`  
> **Status**: Approved  
> **Traceability ID**: `[REQ-UI-001]`, `[REQ-UI-002]`

---

## 1. User Stories

1. **As a** user in Chat Studio on desktop or mobile,  
   **I want** to easily switch between agents directly from the top bar header and have my selection remembered,  
   **So that** I don't lose context or have to repeatedly reselect my active agent.

2. **As a** platform operator configuring LLM endpoints in Settings Studio,  
   **I want** model discovery to properly query endpoints for all provider presets (Ollama, OpenAI, Groq, DeepSeek, Anthropic, vLLM) and keep my saved model selection visible,  
   **So that** I can configure and verify any LLM provider without losing model choices.

---

## 2. EARS Requirements

### [REQ-UI-001] Chat Studio Persistent Multi-Surface Agent Switcher (Ubiquitous)
The platform SHALL render an interactive agent switcher dropdown in the Chat Studio header synchronized two-way with the sidebar agent selector, persisting the active agent ID in browser local storage and restoring it upon tab navigation and page reload.

### [REQ-UI-002] Multi-Preset Model Discovery & Saved Model Retention (Ubiquitous)
The LLM Gateway adapters and Settings Studio SHALL support dynamic provider IDs across all preset configurations (Ollama, OpenAI, OpenRouter, Groq, DeepSeek, Anthropic, Together, vLLM) and preserve user-saved model selections in dropdowns across discovery refreshes.
