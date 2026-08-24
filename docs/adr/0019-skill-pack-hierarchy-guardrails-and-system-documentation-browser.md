# ADR-0019: Skill Pack Hierarchy, Deterministic Guardrails, and System Documentation Browser

> **Status**: Accepted  
> **Date**: 2026-08-23  
> **Decision Makers**: Jacob Weber, Principal Agent Engineer  
> **Linked Issue / Card**: CARD-018

---

## 1. Context and Problem Statement

As AutoReiv expands with dozens of specialized tools and custom agent configurations, operators need:
1. **Hierarchical Skill Packs**: Grouping atomic tools into logical, collapsible skill bundles (e.g. Sysadmin, Librarian, Verification) with one-click bundle toggles while preserving granular tool-level authorization.
2. **Deterministic Guardrails**: Enforcing platform invariants at the schema level so newly synthesized agents cannot contain hallucinated tools, invalid slugs, malformed prompts, or unbounded turn limits.
3. **System Documentation & Specs Browser**: An in-app navigation tab in the Control Plane SPA allowing operators to search and read platform specifications (`docs/specs/`), ADRs (`docs/adr/`), and architecture invariants rendered cleanly in Markdown.

---

## 2. Considered Options

- **Option A: Flat Tool Lists and Separate Markdown Files (Status Quo)**:
  Flat checkboxes for tools; reading documentation solely in git or external editors. Leads to cognitive friction and risk of hallucinated tool authorization.
- **Option B: Hierarchical Skill Packs, Invariant Guardrails, and In-App Specs Reader (Chosen)**:
  Groups tools by parent Skill Pack, strictly validates all agent profiles through Pydantic guardrails, and renders full platform documentation directly in the Control Plane UI.

---

## 3. Decision Outcome

**Chosen Option**: **Option B**.

### Positive Consequences
- **Low Cognitive Friction**: Operators can enable entire skill packs with one click or drill down to individual tools.
- **Strict Correctness**: Hallucinated tools or malformed profiles are rejected deterministically before reaching SQLite.
- **Self-Documenting Platform**: Full visibility into specs, architecture decisions, and SDLC rules right inside the application.
