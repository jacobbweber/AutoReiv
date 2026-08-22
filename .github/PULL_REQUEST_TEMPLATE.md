<!-- Title format: <type>(<scope>): <concise description> -->
<!-- Target Branch: Default to 'qa' for all feature and bugfix PRs -->

## 1. Summary & Intent
<!-- What changed and why? Reference the primary user motivation. -->

## 2. Linked Issue & Spec References
- **Closes Issue**: #
- **EARS Spec**: `docs/specs/<feature>/requirements.md`
- **Tracked Requirements**: `[REQ-xxx]`, `[REQ-yyy]`
- **ADR Reference**: `docs/adr/0001-baseline-sdlc.md` (or "N/A")

---

## 3. Definition of Done Checklist
- [ ] **Spec Sync**: Spec, Design, and Tasks in `docs/specs/` match implementation.
- [ ] **TDD Verified**: Failing tests written first, now passing in CI / local test runner.
- [ ] **Lint & Style**: Zero lint errors and zero unresolved type issues.
- [ ] **RTM Validated**: `python .agents/skills/rtm-sync/scripts/verify_rtm.py` passes with zero errors.
- [ ] **Changelog**: `CHANGELOG.md` updated under `[Unreleased]`.
- [ ] **Zero Suppressions**: No unverified `@ts-ignore` or `# type: ignore` tags.

---

## 4. Human QA Verification Runbook
<!-- Provide concise steps so the Human QA Tester can verify this in under 2 minutes -->
1. **Setup**:
   ```bash
   # Commands to start the service / app
   ```
2. **Action / Test Steps**:
   - Step 1...
   - Step 2...
3. **Expected Outcome**:
   - Observable output / UI response:
