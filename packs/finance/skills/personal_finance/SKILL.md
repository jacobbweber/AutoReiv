---
name: personal_finance
description: Personal finance runbook for logging expenses, budgeting, savings targets, and financial summaries.
tools:
  - log_transactions
  - manage_budget
  - set_savings_goal
  - summarize_finances
---

# Personal Finance Runbook

## Overview
This runbook governs personal financial tracking using the agent's dedicated private database (`finance_storage.db`).

## Operating Procedures
1. **Transaction Logging**:
   - Ingest bank statement exports in CSV format using `log_transactions(csv_path="...")`.
   - Or log individual purchases directly using `log_transactions(transactions=[...])`.

2. **Budget Management**:
   - Set monthly spending ceilings per category using `manage_budget(action="set", category="...", monthly_limit=...)`.
   - Review current month spending velocity using `manage_budget(action="query")`.

3. **Savings Milestones**:
   - Establish target savings goals using `set_savings_goal(action="set", goal_name="...", target_amount=..., target_date="...")`.
   - Log contributions using `set_savings_goal(action="contribute", goal_name="...", contribution=...)`.

4. **Periodic Financial Summaries**:
   - Generate cashflow metrics (income, expenses, net balance, over-budget warnings) using `summarize_finances()`.
