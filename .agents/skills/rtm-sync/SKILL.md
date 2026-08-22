---
name: rtm-sync
description: >-
  Synchronizes and validates the machine-readable Requirements Traceability Matrix (docs/rtm.json), executes unified Definition of Done pre-flight gates, and calculates blast radius for code changes. Use before modifying existing code or after completing a feature.
---

# RTM Traceability & Blast Radius Skill

Follow this runbook to maintain 100% traceability between requirements, architecture, code, and tests.

---

## 1. Calculating Blast Radius (Before Making Changes)
When asked to modify a file or fix a bug:
1. Run the impact analysis command:
   ```bash
   python .agents/skills/rtm-sync/scripts/verify_rtm.py --impact <path_to_modified_file>
   ```
2. Review the impacted requirements, associated specs, and test suites.
3. Ensure all listed test suites are executed during and after your changes.

---

## 2. Registering New Requirements (After Spec Approval)
When a new spec in `docs/specs/<feature>/requirements.md` is approved:
1. Open `docs/rtm.json`.
2. Add a new requirement entry for each `[REQ-xxx]` tag:
   ```json
   {
     "id": "REQ-DOMAIN-001",
     "title": "Clear requirement title",
     "ears_type": "Event-Driven",
     "status": "in_progress",
     "spec": "docs/specs/<feature>/requirements.md",
     "adr": "docs/adr/0001-baseline-sdlc.md",
     "c4_component": "ComponentName",
     "source_modules": ["src/domain/entity.py", "src/application/service.py"],
     "test_suites": ["tests/unit/test_domain.py", "tests/integration/test_service.py"]
   }
   ```

---

## 3. Validating RTM Integrity
1. Run the validator:
   ```bash
   python .agents/skills/rtm-sync/scripts/verify_rtm.py
   ```
2. Verify that all referenced file paths exist on disk and that zero validation errors are reported.

---

## 4. Unified Definition of Done Pre-Flight Check
Before opening a Pull Request, run the complete automated quality gate:
```bash
python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight
```
This automatically verifies:
- [x] `docs/rtm.json` schema and file references.
- [x] Linter commands configured in `steering/tech.md`.
- [x] Test runner commands configured in `steering/tech.md`.
