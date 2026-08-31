# ADR-0006: Live Model Discovery, Hardware Fit Recommendations, and Purpose Routing

> **Date**: 2026-08-22  
> **Status**: Accepted  
> **Deciders**: Human Visionary, AI Agent (Antigravity)  
> **Consulted**: `script-to-agent-labs` Reference Bank (Tiers 2, 8, 11)

---

## 1. Context & Problem Statement

AutoReiv must provide seamless model management:
1. Dynamically discover installed Ollama models and cloud OpenAI models without manual string entry.
2. Route models by operational purpose (Reasoning, Task Execution, Fast Briefings, Vision).
3. Compute host RAM suitability (e.g. running 70B models comfortably on the 128GB Nimo PC, or warning when a model exceeds RAM).
4. Persist customized agent personas, tones, and tools at runtime.

---

## 2. Decision Drivers

* **Zero Hardcoding**: Model lists must update automatically when a user pulls new models in Ollama (`ollama run ...`) and clicks refresh.
* **Hermetic Hardware Safety**: The Hardware Fit Calculator predicts total memory footprint (weight bits + 8k KV cache headroom) to prevent host OOM freezes.
* **Non-Destructive Overrides**: User customizations to agent tone or prompts override defaults in SQLite without modifying core Python codebase files.

---

## 3. Considered Options

* **Option 1**: Fixed configuration file (`settings.yaml`) with static model names.
* **Option 2**: Ad-hoc model selection per chat without purpose routing.
* **Option 3 (Recommended)**: Live discovery via provider ports, purpose matrix routing in SQLite, and dynamic memory fit analyzer.

---

## 4. Decision Outcome

Chosen option: **Option 3 (Live Discovery, Purpose Matrix, and Hardware Fit Analyzer)**, because:
- It delivers a modern control plane experience with purpose-based model routing.
- It maximizes local performance on high-memory hardware (e.g. Nimo Mini PC 128GB unified memory) by recommending ideal quantizations (Q4/Q8/FP16).
- It provides full persistence and dynamic runtime overrides.
