"""
Tool: summarize_finances [CARD-148, CARD-159].
Computes net cashflow, category breakdown, budget compliance, and alerts.
"""

import sqlite3
from typing import Any, Dict, Optional


def summarize_finances(db_path: str, month: Optional[str] = None) -> Dict[str, Any]:
    try:
        if not db_path:
            return {"success": False, "error": "db_path is required."}

        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()

            # 1. Net Cashflow
            cur.execute("SELECT type, SUM(amount) FROM transactions GROUP BY type")
            totals = {row[0]: float(row[1]) for row in cur.fetchall()}
            income = totals.get("credit", 0.0)
            expenses = totals.get("debit", 0.0)
            net_cashflow = round(income - expenses, 2)

            # 2. Category Breakdown
            cur.execute(
                "SELECT category, SUM(amount) FROM transactions WHERE type = 'debit' GROUP BY category ORDER BY SUM(amount) DESC"
            )
            cat_breakdown = {row[0]: round(float(row[1]), 2) for row in cur.fetchall()}

            # 3. Budget Status & Alerts
            cur.execute("SELECT category, monthly_limit FROM budgets")
            budgets = {row[0]: float(row[1]) for row in cur.fetchall()}

            alerts = []
            budget_status = []

            for cat, limit in budgets.items():
                spent = cat_breakdown.get(cat, 0.0)
                remaining = round(limit - spent, 2)
                pct = round((spent / limit) * 100.0, 1) if limit > 0 else 100.0

                if spent > limit:
                    alerts.append(f"OVER BUDGET ALERT: Category '{cat}' spent ${spent:.2f}, exceeding ${limit:.2f} limit!")
                elif pct >= 80.0:
                    alerts.append(f"WARNING: Category '{cat}' reached {pct:.1f}% of ${limit:.2f} limit.")

                budget_status.append(
                    {
                        "category": cat,
                        "monthly_limit": limit,
                        "spent": spent,
                        "remaining": remaining,
                        "percent_utilized": pct,
                    }
                )

            # 4. Savings Status
            cur.execute("SELECT goal_name, target_amount, current_amount, target_date FROM savings_goals")
            goals = [
                {
                    "goal_name": row[0],
                    "target_amount": float(row[1]),
                    "current_amount": float(row[2]),
                    "progress_percent": round((float(row[2]) / float(row[1])) * 100.0, 1) if float(row[1]) > 0 else 100.0,
                    "target_date": row[3],
                }
                for row in cur.fetchall()
            ]

            return {
                "success": True,
                "summary": {
                    "total_income": round(income, 2),
                    "total_expenses": round(expenses, 2),
                    "net_cashflow": net_cashflow,
                    "category_breakdown": cat_breakdown,
                    "budget_status": budget_status,
                    "alerts": alerts,
                    "savings_goals": goals,
                },
            }

        finally:
            conn.close()

    except Exception as exc:
        return {"success": False, "error": f"Failed to summarize finances: {exc}"}
