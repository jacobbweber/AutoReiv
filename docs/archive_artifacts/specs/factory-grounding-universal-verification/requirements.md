# Requirements: Factory Studio Real Project Grounding, Decoupled Authoring, and Universal Verification

> Feature: Factory Studio Real Project Grounding, Decoupled Authoring, and Universal Verification  
> Card: CARD-356  
> Domain: `AutoReiv.Factory`

---

## 1. Context & Business Intent
When an operator initiates a training run for an agent (such as `homelab-admin`), Factory Studio must reliably inspect and ground the training job against real project code on disk (e.g. OpenTofu `.tf` modules, Ansible `.yml` playbooks, PowerShell `.ps1` scripts, Packer templates). The Author phase must generate complete, robust tools and runbooks without timing out or hiding behind silent fallback templates. The Verification battery must evaluate deliverables against realistic domain criteria without tripping on trivial Markdown headings or forcing Hyper-V ISO keywords when the domain is IaC/automation.

---

## 2. EARS Requirements

### 2.1 Project Directory Grounding
- **[REQ-FACT-064]**: WHILE an active project is selected in settings, THE SYSTEM SHALL default `target_directory` to `selected_project.path` in training job dispatch unless explicitly overridden.
- **[REQ-FACT-065]**: WHEN `GroundPhase` executes for a job with a valid `target_directory`, THE SYSTEM SHALL invoke `EnvironmentInspectionSkill` to scan the filesystem tree, catalog configuration files, scripts, and domain SOPs, and embed this structured inventory in the ground packet manifest and operating manual.

### 2.2 Author Resilience & Progress Honesty
- **[REQ-FACT-066]**: WHILE authoring tools and runbooks, THE SYSTEM SHALL configure a minimum LLM execution timeout of 180 seconds for local model providers, allowing sufficient latency runway for complex generation.
- **[REQ-FACT-067]**: WHEN an Author phase LLM call times out or fails parsing, THE SYSTEM SHALL record honest diagnostic telemetry with the failure reason and execution duration, preventing silent substitution of unvetted stub code as LLM output.

### 2.3 Universal Verification Battery Harmonization
- **[REQ-FACT-068]**: THE SYSTEM SHALL accept both `## Purpose` and `## Overview` (case-insensitive) as valid objective headings in `is_shallow_stub_artifact`, harmonizing runbook evaluation with `ToolSynthesizer` templates and system prompts.
- **[REQ-FACT-069]**: WHEN evaluating non-Hyper-V domain artifacts (such as OpenTofu, Ansible, or CLI automation), THE SYSTEM SHALL evaluate coverage against the grounded file manifest and distilled scenarios rather than requiring Hyper-V ISO or unattended install keywords.
