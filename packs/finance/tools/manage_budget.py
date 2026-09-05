"""
Tool: manage_budget [CARD-148, CARD-159].
Sets, queries, and evaluates monthly category budget limits in finance_storage.db.
"""

import sqlite3
from typing import Any, Dict, Optional


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT UNIQUE NOT NULL,
            monthly_limit REAL NOT NULL,
            month TEXT
        )
        """
    )
    conn.commit()


def manage_budget(
    db_path: str,
    action: str = "query",
    category: Optional[str] = None,
    monthly_limit: Optional[float] = None,
    month: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        if not db_path:
            return {"success": False, "error": "db_path is required."}

        conn = sqlite3.connect(db_path)
        try:
            init_db(conn)
            cur = conn.cursor()

            act = action.strip().lower()

            if act == "set":
                if not category or monthly_limit is None:
                    return {"success": False, "error": "category and monthly_limit are required for 'set'."}
                cur.execute(
                    """
                    INSERT INTO budgets (category, monthly_limit, month)
                    VALUES (?, ?, ?)
                    ON CONFLICT(category) DO UPDATE SET
                        monthly_limit = excluded.monthly_limit,
                        month = excluded.month
                    """,
                    (category.strip(), float(monthly_limit), (month or "").strip()),
                )
                conn.commit()
                return {
                    "success": True,
                    "action": "set",
                    "category": category.strip(),
                    "monthly_limit": float(monthly_limit),
                    "month": month,
                }

            elif act == "query":
                cur.execute("SELECT category, monthly_limit, month FROM budgets ORDER BY category ASC")
                rows = cur.fetchall()
                budget_list = []
                for cat, limit, m in rows:
                    # Check spent from transactions if transactions table exists
                    spent = 0.0
                    try:
                        cur.execute(
                            "SELECT SUM(amount) FROM transactions WHERE category = ? AND type = 'debit'",
                            (cat,),
                        )
                        spent_row = cur.fetchone()
                        if spent_row and spent_row[0] is not None:
                            spent = float(spent_row[0])
                    except sqlite3.OperationalError:
                        pass

                    budget_list.append(
                        {
                            "category": cat,
                            "monthly_limit": limit,
                            "spent": spent,
                            "remaining": round(limit - spent, 2),
                            "month": m,
                        }
                    )
                return {
                    "success": True,
                    "action": "query",
                    "count": len(budget_list),
                    "budgets": budget_list,
                }

            elif act == "delete":
                if not category:
                    return {"success": False, "error": "category is required for 'delete'."}
                cur.execute("DELETE FROM budgets WHERE category = ?", (category.strip(),))
                conn.commit()
                return {"success": True, "action": "delete", "category": category}

            else:
                return {"success": False, "error": f"Unknown action: {action}. Allowed: 'set', 'query', 'delete'."}

        finally:
            conn.close()

    except Exception as exc:
        return {"success": False, "error": f"Failed to manage budget: {exc}"}
