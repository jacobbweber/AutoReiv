"""
Tool: log_transactions [CARD-148, CARD-159].
Ingests transaction records and parses bank CSV exports into finance_storage.db.
"""

import csv
import sqlite3
from typing import Any, Dict, List, Optional


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            merchant TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('debit', 'credit')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def log_transactions(
    db_path: str,
    transactions: Optional[List[Dict[str, Any]]] = None,
    csv_path: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        if not db_path:
            return {"success": False, "error": "db_path is required."}

        conn = sqlite3.connect(db_path)
        try:
            init_db(conn)
            cur = conn.cursor()
            inserted = 0

            # 1. Process structured list if provided
            if transactions:
                for tx in transactions:
                    cur.execute(
                        """
                        INSERT INTO transactions (date, merchant, category, amount, type)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            str(tx.get("date", "")).strip(),
                            str(tx.get("merchant", "")).strip(),
                            str(tx.get("category", "Uncategorized")).strip(),
                            float(tx.get("amount", 0.0)),
                            str(tx.get("type", "debit")).strip().lower(),
                        ),
                    )
                    inserted += 1

            # 2. Process CSV file if provided
            if csv_path:
                with open(csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        cur.execute(
                            """
                            INSERT INTO transactions (date, merchant, category, amount, type)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (
                                str(row.get("date", "")).strip(),
                                str(row.get("merchant", "")).strip(),
                                str(row.get("category", "Uncategorized")).strip(),
                                float(row.get("amount", 0.0)),
                                str(row.get("type", "debit")).strip().lower(),
                            ),
                        )
                        inserted += 1

            conn.commit()

            cur.execute("SELECT COUNT(*) FROM transactions")
            total = cur.fetchone()[0]

            return {
                "success": True,
                "inserted_count": inserted,
                "total_transactions": total,
                "message": f"Successfully logged {inserted} transactions.",
            }
        finally:
            conn.close()

    except Exception as exc:
        return {"success": False, "error": f"Failed to log transactions: {exc}"}
