<!-- Title format: <type>(<scope>): <concise description> -->
<!-- Target Branch: Default to 'qa' for all feature and bugfix PRs -->

## 1. Summary & Intent

<!-- What changed and why? Reference the primary user motivation. -->

## 2. Linked Card & ADR References

- **Work Card**: `docs/cards/CARD-xxx.md` (or #issue)
- **ADR Reference**: `docs/adr/0001-baseline-sdlc.md` (or "N/A")

---

## 3. Definition of Done Checklist

- [ ] **Card Sync**: Four Beats, acceptance criteria, and prune list in `docs/cards/CARD-xxx.md` match implementation.
- [ ] **Test-Locked Delivery**: Unit, integration, and smoke tests passing locally (`npm run preflight`).
- [ ] **Scavenger Pass**: Callers audited via ripgrep; zero orphaned functions, dead variables, or zombie DOM elements left behind.
- [ ] **Single Lever**: Exactly one canonical code path exists for every modified capability (zero duplicate functions or shadow listeners).
- [ ] **Lint & Style**: Zero lint errors and zero warnings (`ruff check .`, `npm run lint:frontend`).
- [ ] **Changelog**: `CHANGELOG.md` updated under `[Unreleased]`.
- [ ] **Zero Suppressions**: No unverified `@ts-ignore` or `# type: ignore` tags.

---

## 4. Human QA Verification Runbook

<!-- Provide concise steps so Jacob / Human QA can verify this in under 2 minutes -->

1. **Setup**:

   ```bash
   # Commands to start the service / app
   ```

2. **Action / Test Steps**:
   - Step 1...
   - Step 2...
3. **Expected Outcome**:
   - Observable output / UI response:
