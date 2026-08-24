# ADR-0030: Web UI Tab Hydration and Rendering Architecture

> **Date**: 2026-08-23  
> **Status**: Accepted  
> **Deciders**: Human Visionary, AI Agent  
> **Consulted**: Master Agent Constitution

---

## 1. Context & Problem Statement
AutoReiv's zero-build Single Page Application (SPA) integrates 7 studio tabs (Chat, Routines, Observability, Agent Studio, Settings Studio, System Info Hub, Wiki Studio). Users reported intermittent blank rendering or missing controls on specific tabs (such as empty skill packs in Agent Studio, topic index failure in System Info, and empty vault view in Wiki Studio on mobile viewports).

---

## 2. Decision Drivers
* Zero-build simplicity with reliable client-side hydration.
* Complete mobile accessibility (<768px viewport) without hidden drawers or missing touch affordances.
* Zero console exceptions during rapid tab switching and data loading.

---

## 3. Considered Options
* **Option A**: Dynamic isolated tab loaders with deterministic catalog re-rendering, initial document auto-selection, and try/catch boundaries (Selected).
* **Option B**: Full frontend rewrite to React/Vue with node build pipeline.

---

## 4. Decision Outcome
Chosen option: **Option A**, because it maintains our lightweight zero-build vanilla JS architecture while resolving all lifecycle, caching, and DOM state issues.

### Positive Consequences
* Instant, flicker-free tab hydration across all 7 views.
* Skill packs, System Info topics, and Wiki tree notes reliably render on first and repeated visits.
* Clean error boundaries ensure one failing endpoint never breaks other tabs.

### Negative Consequences / Trade-offs
* Requires careful manual state synchronization across DOM elements.

