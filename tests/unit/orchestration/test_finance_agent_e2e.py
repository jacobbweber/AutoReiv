"""
End-to-End Verification and Hardening of Autonomous Agent Pack Factory:
Personal Finance Agent (finance) [REQ-FACT-001 - REQ-FACT-015, CARD-148, CARD-159].
"""

import sqlite3
from pathlib import Path

import pytest

from src.application.agent_packs.service import AgentPackService
from src.application.orchestration.capability_graph import (
    AgentSplitPolicy,
    ToolConsolidationGate,
    UserPackFinalizer,
)
from src.application.orchestration.verification_battery import VerificationBatteryService
from src.application.skills.environment_inspection import EnvironmentInspectionTools
from src.application.skills.sandbox_runner import SandboxTestRunner
from src.infrastructure.data.resolver import resolve_agent_storage_path

# -----------------------------------------------------------------------------
# Tool Source Code Definitions
# -----------------------------------------------------------------------------

TOOL_LOG_TRANSACTIONS = '''"""
Tool: log_transactions
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
'''

TEST_LOG_TRANSACTIONS = '''
import sqlite3
from tool import log_transactions

db_file = "test_finance.db"

# Test 1: Log structured transactions
txs = [
    {"date": "2026-09-01", "merchant": "Payroll", "category": "Income", "amount": 3000.0, "type": "credit"},
    {"date": "2026-09-02", "merchant": "Groceries Store", "category": "Groceries", "amount": 120.0, "type": "debit"},
]
res1 = log_transactions(db_path=db_file, transactions=txs)
assert res1["success"] is True
assert res1["inserted_count"] == 2
assert res1["total_transactions"] >= 2

# Test 2: Idempotent / repeat call
txs2 = [{"date": "2026-09-03", "merchant": "Cafe", "category": "Dining", "amount": 15.0, "type": "debit"}]
res2 = log_transactions(db_path=db_file, transactions=txs2)
assert res2["success"] is True
assert res2["inserted_count"] == 1
assert res2["total_transactions"] >= 3
'''


TOOL_MANAGE_BUDGET = '''"""
Tool: manage_budget
Sets, queries, and evaluates monthly category budget limits in finance_storage.db.
"""

import sqlite3
from typing import Any, Dict, List, Optional


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
'''

TEST_MANAGE_BUDGET = '''
from tool import manage_budget

db_file = "test_budget.db"

# Set budget
res_set = manage_budget(db_path=db_file, action="set", category="Groceries", monthly_limit=500.0, month="2026-09")
assert res_set["success"] is True
assert res_set["monthly_limit"] == 500.0

# Query budget
res_q = manage_budget(db_path=db_file, action="query")
assert res_q["success"] is True
assert res_q["count"] >= 1
assert res_q["budgets"][0]["category"] == "Groceries"
assert res_q["budgets"][0]["remaining"] == 500.0
'''


TOOL_SET_SAVINGS_GOAL = '''"""
Tool: set_savings_goal
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
'''

TEST_SET_SAVINGS_GOAL = '''
from tool import set_savings_goal

db_file = "test_savings.db"

# Set goal
res1 = set_savings_goal(db_path=db_file, action="set", goal_name="Emergency Fund", target_amount=5000.0, target_date="2026-12-31")
assert res1["success"] is True

# Contribute
res2 = set_savings_goal(db_path=db_file, action="contribute", goal_name="Emergency Fund", contribution=1000.0)
assert res2["success"] is True
assert res2["current_amount"] >= 1000.0
assert res2["progress_percent"] >= 20.0

# Query
res3 = set_savings_goal(db_path=db_file, action="query")
assert res3["success"] is True
assert res3["count"] >= 1
'''


TOOL_SUMMARIZE_FINANCES = '''"""
Tool: summarize_finances
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
'''

TEST_SUMMARIZE_FINANCES = '''
import sqlite3
from tool import summarize_finances

db_file = "test_summary.db"
conn = sqlite3.connect(db_file)
conn.execute("CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY, date TEXT, merchant TEXT, category TEXT, amount REAL, type TEXT)")
conn.execute("CREATE TABLE IF NOT EXISTS budgets (id INTEGER PRIMARY KEY, category TEXT UNIQUE, monthly_limit REAL, month TEXT)")
conn.execute("CREATE TABLE IF NOT EXISTS savings_goals (id INTEGER PRIMARY KEY, goal_name TEXT UNIQUE, target_amount REAL, current_amount REAL, target_date TEXT)")

conn.execute("DELETE FROM transactions")
conn.execute("DELETE FROM budgets")
conn.execute("DELETE FROM savings_goals")

conn.execute("INSERT INTO transactions (date, merchant, category, amount, type) VALUES ('2026-09-01', 'Payroll', 'Income', 3500.0, 'credit')")
conn.execute("INSERT INTO transactions (date, merchant, category, amount, type) VALUES ('2026-09-02', 'Store', 'Groceries', 150.0, 'debit')")
conn.execute("INSERT INTO budgets (category, monthly_limit, month) VALUES ('Groceries', 500.0, '2026-09')")
conn.execute("INSERT INTO savings_goals (goal_name, target_amount, current_amount, target_date) VALUES ('Vacation', 2000.0, 500.0, '2026-11-01')")
conn.commit()
conn.close()

res = summarize_finances(db_path=db_file)
assert res["success"] is True
assert res["summary"]["total_income"] == 3500.0
assert res["summary"]["total_expenses"] == 150.0
assert res["summary"]["net_cashflow"] == 3350.0
assert "Groceries" in res["summary"]["category_breakdown"]
assert len(res["summary"]["budget_status"]) == 1
assert len(res["summary"]["savings_goals"]) == 1
'''


# -----------------------------------------------------------------------------
# End-to-End Test Suite
# -----------------------------------------------------------------------------


def test_finance_workspace_environment_inspection():
    """Verify EnvironmentInspectionTools accurately extracts the finance fixture structure."""
    fixture_dir = Path("tests/fixtures/finance_workspace").resolve()
    inspector = EnvironmentInspectionTools()

    manifest = inspector.compile_manifest(str(fixture_dir))
    assert manifest["target_os"] != ""
    files = manifest["files_tree"]
    assert len(files) >= 2

    # Verify checking_transactions.csv was discovered and profiled
    csv_file = next((f for f in files if f["name"] == "checking_transactions.csv"), None)
    assert csv_file is not None
    assert csv_file["format"] == "csv"

    # Verify monthly_budget_plan.txt was discovered
    txt_file = next((f for f in files if f["name"] == "monthly_budget_plan.txt"), None)
    assert txt_file is not None
    assert txt_file["format"] == "txt"


@pytest.mark.asyncio
async def test_finance_tools_verification_battery():
    """Verify all 4 finance tools pass all 4 stages of VerificationBatteryService."""
    battery = VerificationBatteryService(runner=SandboxTestRunner())

    tools_to_verify = [
        ("log_transactions", TOOL_LOG_TRANSACTIONS, TEST_LOG_TRANSACTIONS),
        ("manage_budget", TOOL_MANAGE_BUDGET, TEST_MANAGE_BUDGET),
        ("set_savings_goal", TOOL_SET_SAVINGS_GOAL, TEST_SET_SAVINGS_GOAL),
        ("summarize_finances", TOOL_SUMMARIZE_FINANCES, TEST_SUMMARIZE_FINANCES),
    ]

    for tool_name, tool_code, test_code in tools_to_verify:
        result = await battery.run_battery(tool_code=tool_code, test_code=test_code)
        assert result.passed is True, f"Tool '{tool_name}' failed battery: {result.critic_notes}\nStderr: {result.stderr}"
        assert result.stage_1_functional is True
        assert result.stage_2_safety is True
        assert result.stage_3_idempotency is True
        assert result.stage_4_critic is True


def test_finance_tool_consolidation_and_split_gates():
    """Verify ToolConsolidationGate and AgentSplitPolicy certify the 4-tool finance pack."""
    proposed_tools = [
        {"name": "log_transactions", "target_entity": "transactions", "domain": "personal_finance"},
        {"name": "manage_budget", "target_entity": "budgets", "domain": "personal_finance"},
        {"name": "set_savings_goal", "target_entity": "savings", "domain": "personal_finance"},
        {"name": "summarize_finances", "target_entity": "reports", "domain": "personal_finance"},
    ]

    gate = ToolConsolidationGate()
    consolidation_eval = gate.evaluate(proposed_tools)
    assert consolidation_eval["should_consolidate"] is False
    assert consolidation_eval["reason"] == "No common entity tool bloat detected."

    split_policy = AgentSplitPolicy()
    split_eval = split_policy.evaluate_split(agent_id="finance", tools=proposed_tools, max_tools_per_agent=6)
    assert split_eval["should_split"] is False
    assert "responsibilities are properly cohesive" in split_eval["reason"]


def test_finance_pack_finalization_and_live_turns(tmp_path):
    """
    Finalize the finance pack into isolated pack storage, then simulate live chat turns:
    Turn 1: Ingest sample bank CSV transactions
    Turn 2: Set monthly category budgets ($600 Groceries, $200 Utilities, $200 Dining, $150 Transport)
    Turn 3: Set Emergency Fund savings goal ($5,000 target by 2026-12-31, contribute $1,000)
    Turn 4: Generate financial summary
    Assert all invariants directly against finance_storage.db.
    """
    finalizer = UserPackFinalizer(data_dir=str(tmp_path))

    manifest_data = {
        "id": "finance",
        "name": "Personal Finance Lead",
        "description": "Tracks personal finances, budgets, and savings goals.",
        "system_prompt": "You are Personal Finance Lead. Manage budgets, log transactions, and compute financial summaries.",
        "storage": {"enabled": True, "type": "sqlite"},
        "show_in_chat": True,
        "skills": [
            {
                "id": "personal_finance",
                "tools": ["log_transactions", "manage_budget", "set_savings_goal", "summarize_finances"],
            }
        ],
        "pack_tool_names": ["log_transactions", "manage_budget", "set_savings_goal", "summarize_finances"],
        "allowed_tool_names": ["log_transactions", "manage_budget", "set_savings_goal", "summarize_finances"],
    }

    files = {
        "tools/log_transactions.py": TOOL_LOG_TRANSACTIONS,
        "tools/manage_budget.py": TOOL_MANAGE_BUDGET,
        "tools/set_savings_goal.py": TOOL_SET_SAVINGS_GOAL,
        "tools/summarize_finances.py": TOOL_SUMMARIZE_FINANCES,
        "skills/personal_finance/SKILL.md": "# Personal Finance Runbook\n\nRunbook for logging expenses and tracking budgets.",
    }

    pack_dir_str = finalizer.finalize_pack(agent_id="finance", manifest_data=manifest_data, files=files)
    pack_dir = Path(pack_dir_str)
    assert (pack_dir / "pack.json").is_file()
    assert (pack_dir / "tools" / "log_transactions.py").is_file()
    assert (pack_dir / "tools" / "manage_budget.py").is_file()
    assert (pack_dir / "tools" / "set_savings_goal.py").is_file()
    assert (pack_dir / "tools" / "summarize_finances.py").is_file()

    # Dedicated pack database path [CARD-148]
    storage_db_path = resolve_agent_storage_path("finance", data_dir=tmp_path)
    assert storage_db_path == tmp_path / "packs" / "finance" / "finance_storage.db"

    # Import modules dynamically from authored pack
    import importlib.util

    def load_pack_tool(name: str):
        tool_file = pack_dir / "tools" / f"{name}.py"
        spec = importlib.util.spec_from_file_location(name, tool_file)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    mod_log = load_pack_tool("log_transactions")
    mod_budget = load_pack_tool("manage_budget")
    mod_savings = load_pack_tool("set_savings_goal")
    mod_summary = load_pack_tool("summarize_finances")

    # --- Turn 1: Ingest Bank Transactions CSV ---
    csv_fixture = Path("tests/fixtures/finance_workspace/checking_transactions.csv").resolve()
    t1_res = mod_log.log_transactions(db_path=str(storage_db_path), csv_path=str(csv_fixture))
    assert t1_res["success"] is True
    assert t1_res["inserted_count"] == 5
    assert t1_res["total_transactions"] == 5

    # --- Turn 2: Set Monthly Category Budgets ---
    budgets_to_set = [
        ("Groceries", 600.0),
        ("Utilities", 200.0),
        ("Dining", 200.0),
        ("Transport", 150.0),
    ]
    for cat, limit in budgets_to_set:
        b_res = mod_budget.manage_budget(
            db_path=str(storage_db_path), action="set", category=cat, monthly_limit=limit, month="2026-09"
        )
        assert b_res["success"] is True

    # Query budgets to verify spent and remaining calculations
    b_query = mod_budget.manage_budget(db_path=str(storage_db_path), action="query")
    assert b_query["success"] is True
    assert b_query["count"] == 4

    groceries_budget = next(b for b in b_query["budgets"] if b["category"] == "Groceries")
    assert groceries_budget["monthly_limit"] == 600.0
    assert groceries_budget["spent"] == 180.50
    assert groceries_budget["remaining"] == 419.50

    # --- Turn 3: Set Savings Goal & Contribute ---
    s_res1 = mod_savings.set_savings_goal(
        db_path=str(storage_db_path),
        action="set",
        goal_name="Emergency Fund",
        target_amount=5000.0,
        target_date="2026-12-31",
    )
    assert s_res1["success"] is True

    s_res2 = mod_savings.set_savings_goal(
        db_path=str(storage_db_path),
        action="contribute",
        goal_name="Emergency Fund",
        contribution=1000.0,
    )
    assert s_res2["success"] is True
    assert s_res2["current_amount"] == 1000.0
    assert s_res2["progress_percent"] == 20.0
    assert s_res2["remaining"] == 4000.0

    # --- Turn 4: Summarize Finances ---
    sum_res = mod_summary.summarize_finances(db_path=str(storage_db_path))
    assert sum_res["success"] is True
    summary = sum_res["summary"]

    # Invariants
    assert summary["total_income"] == 3500.00
    assert summary["total_expenses"] == 385.70  # 180.50 + 95.20 + 65.00 + 45.00
    assert summary["net_cashflow"] == 3114.30
    assert len(summary["category_breakdown"]) == 4
    assert len(summary["alerts"]) == 0  # None over budget!
    assert len(summary["savings_goals"]) == 1

    # --- Direct SQLite Database Verification ---
    assert storage_db_path.is_file()
    direct_conn = sqlite3.connect(str(storage_db_path))
    try:
        cur = direct_conn.cursor()

        # Check transactions table
        cur.execute("SELECT COUNT(*) FROM transactions")
        assert cur.fetchone()[0] == 5

        cur.execute("SELECT merchant, amount, type FROM transactions ORDER BY id ASC")
        rows = cur.fetchall()
        assert rows[0] == ("Acme Payroll", 3500.0, "credit")
        assert rows[1] == ("Whole Foods", 180.5, "debit")
        assert rows[2] == ("City Electric Power", 95.2, "debit")
        assert rows[3] == ("Trattoria Roma", 65.0, "debit")
        assert rows[4] == ("Metro Transit", 45.0, "debit")

        # Check budgets table
        cur.execute("SELECT COUNT(*) FROM budgets")
        assert cur.fetchone()[0] == 4

        # Check savings_goals table
        cur.execute("SELECT goal_name, target_amount, current_amount FROM savings_goals")
        goal_row = cur.fetchone()
        assert goal_row == ("Emergency Fund", 5000.0, 1000.0)

    finally:
        direct_conn.close()


def test_finance_agent_pack_service_import_and_registry(tmp_path):
    """Verify AgentPackService imports the finance pack and sets up storage permissions."""
    finalizer = UserPackFinalizer(data_dir=str(tmp_path))
    manifest_data = {
        "id": "finance",
        "name": "Personal Finance Lead",
        "description": "Tracks personal finances, budgets, and savings goals.",
        "system_prompt": "You are Personal Finance Lead.",
        "storage": {"enabled": True, "type": "sqlite"},
        "show_in_chat": True,
        "skills": [
            {
                "id": "personal_finance",
                "tools": ["log_transactions", "manage_budget", "set_savings_goal", "summarize_finances"],
            }
        ],
        "pack_tool_names": ["log_transactions", "manage_budget", "set_savings_goal", "summarize_finances"],
        "allowed_tool_names": ["log_transactions", "manage_budget", "set_savings_goal", "summarize_finances"],
    }
    files = {
        "skills/personal_finance/SKILL.md": "# Finance Runbook",
    }
    pack_dir_str = finalizer.finalize_pack(agent_id="finance", manifest_data=manifest_data, files=files)

    from src.infrastructure.agents.registry import BuiltinAgentRegistry
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore

    db_file = tmp_path / "test_store.db"
    store = SQLiteStateStore(db_path=str(db_file))
    registry = BuiltinAgentRegistry(profiles=[], state_store=store)
    service = AgentPackService(data_dir=tmp_path, agent_registry=registry, store=store)
    profile = service.import_path(Path(pack_dir_str))

    assert profile.id == "finance"
    assert profile.name == "Personal Finance Lead"
    assert profile.storage_enabled is True
    assert profile.storage_type == "sqlite"
    assert "log_transactions" in profile.allowed_tool_names
    assert "manage_budget" in profile.allowed_tool_names
    assert "set_savings_goal" in profile.allowed_tool_names
    assert "summarize_finances" in profile.allowed_tool_names
