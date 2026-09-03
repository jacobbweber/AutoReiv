# [CARD-149] Finance Specialist Agent Pack with Transaction Tracking

> **Status**: Ready
> **Created**: 2026-09-03
> **Spec Reference**: none
> **Labels**: `type:feature`, `AutoReiv.Agents`, `AutoReiv.Skills`, `AutoReiv.Tools`

---

## 1. Why / Intent

Users want an intelligent personal financial advisor and expense tracking specialist inside AutoReiv. The finance agent needs to ingest transaction summaries (from bank statements, credit card exports, CSVs, or pasted text), store them in its dedicated private database (leveraging CARD-148 per-agent storage), and provide analysis, category breakdown, spending trends, and financial guidance.

---

## 2. What to Build

1. **Finance Agent Pack (`agent-packs/finance/`)**:
   - `pack.json`:
     - `id`: `"finance"`
     - `name`: `"Finance Advisor"`
     - `description`: `"Personal financial advisor for tracking expenses, analyzing bank/credit card statements, and budget insights."`
     - `avatar_icon`: `"database"`
     - `storage`: `{"enabled": true, "type": "sqlite"}`
     - Skills and tools bindings.
2. **Financial Skills & Runbooks (`agent-packs/finance/skills/`)**:
   - `transaction-ingest/SKILL.md`: Step-by-step runbook for parsing pasted statements, CSV lines, and receipt summaries into structured rows (`date`, `merchant`, `amount`, `category`, `account_type`, `notes`).
   - `financial-analysis/SKILL.md`: Step-by-step runbook for answering spending questions, calculating monthly burn, identifying top expense categories, and tracking savings goals.
3. **Transaction Tools (`src/application/skills/finance_tools.py` or platform tool registry)**:
   - `ingest_financial_transactions`: Parse and insert transaction records into the finance agent's private database.
   - `query_spending_summary`: Query totals grouped by category, month, or merchant.
   - `list_recent_transactions`: Retrieve transaction rows with filtering by date range, merchant, or category.
4. **Initial Database Schema**:
   - Automatically initialize table `transactions` in the agent's isolated SQLite database:
     - `id TEXT PRIMARY KEY`
     - `date TEXT NOT NULL`
     - `merchant TEXT NOT NULL`
     - `amount REAL NOT NULL`
     - `category TEXT NOT NULL`
     - `account_type TEXT` (e.g. "checking", "credit_card")
     - `raw_description TEXT`
     - `notes TEXT`
     - `created_at TIMESTAMP`

---

## 3. Acceptance Criteria (Definition of Done)

- [ ] `[REQ-FINANCE-001]`: `agent-packs/finance` catalog directory created with valid `pack.json` declaring isolated SQLite storage.
- [ ] `[REQ-FINANCE-002]`: Skill runbooks for transaction ingestion and financial analysis added to the pack.
- [ ] `[REQ-FINANCE-003]`: Financial tools for ingesting transactions, querying summaries, and filtering records implemented and tested.
- [ ] `[REQ-FINANCE-004]`: Pack successfully imports via Agent Studio Import and runs queries against its isolated database.
- [ ] `[REQ-FINANCE-005]`: Automated unit tests pass cleanly via `pytest`.
- [ ] `[REQ-FINANCE-006]`: Zero linting errors via `ruff check .`.

---

## 4. Constraints & Honor Flags

- Zero mixing of financial records into the main `autoreiv.db`.
- Strictly adheres to the Agent Pack SDK schema in `docs/agent-packs.md`.
- Requires CARD-148 for per-agent persistent storage.
- Local `qa` branch is source of truth.
