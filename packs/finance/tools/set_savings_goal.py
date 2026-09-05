"""
Tool: set_savings_goal [CARD-148, CARD-159].
Creates, tracks, and logs contributions toward financial savings goals.
"""

import sqlite3
from typing import Any, Dict, Optional


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS savings_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_name TEXT UNIQUE NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL NOT NULL DEFAULT 0.0,
            target_date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def set_savings_goal(
    db_path: str,
    action: str = "set",
    goal_name: Optional[str] = None,
    target_amount: Optional[float] = None,
    target_date: Optional[str] = None,
    contribution: Optional[float] = None,
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
                if not goal_name or target_amount is None or not target_date:
                    return {"success": False, "error": "goal_name, target_amount, and target_date are required for 'set'."}

                cur.execute(
                    """
                    INSERT INTO savings_goals (goal_name, target_amount, current_amount, target_date)
                    VALUES (?, ?, 0.0, ?)
                    ON CONFLICT(goal_name) DO UPDATE SET
                        target_amount = excluded.target_amount,
                        target_date = excluded.target_date
                    """,
                    (goal_name.strip(), float(target_amount), target_date.strip()),
                )
                conn.commit()
                return {
                    "success": True,
                    "action": "set",
                    "goal_name": goal_name.strip(),
                    "target_amount": float(target_amount),
                    "target_date": target_date.strip(),
                }

            elif act == "contribute":
                if not goal_name or contribution is None or contribution <= 0:
                    return {"success": False, "error": "goal_name and positive contribution amount are required."}

                cur.execute(
                    "UPDATE savings_goals SET current_amount = current_amount + ? WHERE goal_name = ?",
                    (float(contribution), goal_name.strip()),
                )
                if cur.rowcount == 0:
                    return {"success": False, "error": f"Goal '{goal_name}' not found."}

                conn.commit()
                cur.execute("SELECT target_amount, current_amount, target_date FROM savings_goals WHERE goal_name = ?", (goal_name.strip(),))
                row = cur.fetchone()
                target, current, t_date = row
                pct = round((current / target) * 100.0, 2) if target > 0 else 100.0

                return {
                    "success": True,
                    "action": "contribute",
                    "goal_name": goal_name.strip(),
                    "contributed": float(contribution),
                    "current_amount": current,
                    "target_amount": target,
                    "progress_percent": pct,
                    "remaining": max(0.0, round(target - current, 2)),
                }

            elif act == "query":
                cur.execute("SELECT goal_name, target_amount, current_amount, target_date FROM savings_goals ORDER BY target_date ASC")
                rows = cur.fetchall()
                goals = []
                for g_name, target, current, t_date in rows:
                    pct = round((current / target) * 100.0, 2) if target > 0 else 100.0
                    goals.append(
                        {
                            "goal_name": g_name,
                            "target_amount": target,
                            "current_amount": current,
                            "target_date": t_date,
                            "progress_percent": pct,
                            "remaining": max(0.0, round(target - current, 2)),
                        }
                    )
                return {"success": True, "action": "query", "count": len(goals), "goals": goals}

            else:
                return {"success": False, "error": f"Unknown action: {action}. Allowed: 'set', 'contribute', 'query'."}

        finally:
            conn.close()

    except Exception as exc:
        return {"success": False, "error": f"Failed to set savings goal: {exc}"}
