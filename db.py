"""
SQLite database layer — customers table with seed data and query helpers.

The three public functions (lookup_customer, list_customers_by_plan,
get_customer_stats) are designed to be passed directly to the Gemini SDK
as automatic function-calling tools.

CPF numbers follow the official Brazilian validation algorithm (mod-11 check digits).
Credit card numbers are fake but pass the Luhn algorithm — safe to use for testing.
"""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data.db"

# Increment this whenever the schema changes to trigger an automatic migration.
SCHEMA_VERSION = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT    NOT NULL,
    email               TEXT    NOT NULL,
    company             TEXT    NOT NULL,
    plan                TEXT    NOT NULL CHECK(plan IN ('free', 'pro', 'enterprise')),
    mrr                 REAL    NOT NULL DEFAULT 0,
    country             TEXT    NOT NULL,
    cpf                 TEXT    NOT NULL,
    credit_card_type    TEXT    NOT NULL,
    credit_card_number  TEXT    NOT NULL,
    credit_card_expiry  TEXT    NOT NULL,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

# Each row: (name, email, company, plan, mrr, country,
#            cpf, credit_card_type, credit_card_number, credit_card_expiry, created_at)
#
# CPF — valid Brazilian CPF (all pass the official mod-11 check-digit algorithm).
# Credit card — Luhn-valid test numbers (Visa/Mastercard/Amex standard test values).
SEED_DATA = [
    (
        "Alice Johnson", "alice@acmecorp.com", "Acme Corp", "enterprise", 4500.00, "US",
        "529.982.247-25", "Visa",       "4111 1111 1111 1111", "12/27", "2024-01-15",
    ),
    (
        "Bob Smith", "bob@widgetsinc.com", "Widgets Inc", "pro", 199.00, "UK",
        "111.444.777-35", "Mastercard", "5500 0000 0000 0004", "09/26", "2024-02-20",
    ),
    (
        "Carlos Rivera", "carlos@dataflow.io", "DataFlow", "enterprise", 8200.00, "BR",
        "222.333.668-08", "Visa",       "4242 4242 4242 4242", "03/28", "2023-11-03",
    ),
    (
        "Diana Chen", "diana@nexatech.cn", "NexaTech", "pro", 349.00, "CN",
        "348.417.573-76", "Mastercard", "5105 1051 0510 5100", "07/27", "2024-03-10",
    ),
    (
        "Erik Johansson", "erik@nordicai.se", "Nordic AI", "free", 0.00, "SE",
        "652.137.984-46", "Visa",       "4000 0000 0000 0002", "11/25", "2024-06-01",
    ),
    (
        "Fatima Al-Rashid", "fatima@gulfdata.ae", "Gulf Data Systems", "enterprise", 12000.00, "AE",
        "417.892.356-00", "Amex",       "3782 822463 10005",   "01/29", "2023-08-22",
    ),
    (
        "Grace Okonkwo", "grace@panafricloud.ng", "PanAfriCloud", "pro", 249.00, "NG",
        "763.542.189-19", "Visa",       "4000 0000 0000 0077", "06/26", "2024-04-18",
    ),
    (
        "Hiroshi Tanaka", "hiroshi@sakurasoft.jp", "SakuraSoft", "free", 0.00, "JP",
        "891.234.657-19", "Mastercard", "5200 8282 8282 8210", "08/27", "2024-07-05",
    ),
    (
        "Isabella Rossi", "isabella@euroanalytics.it", "EuroAnalytics", "enterprise", 6700.00, "IT",
        "345.678.912-28", "Amex",       "3714 496353 98431",   "04/28", "2023-12-11",
    ),
    (
        "Jake Williams", "jake@startuplab.com", "StartupLab", "free", 0.00, "US",
        "987.654.321-00", "Mastercard", "5425 2334 3010 9903", "10/26", "2024-09-30",
    ),
]

_INSERT_SQL = (
    "INSERT INTO customers "
    "(name, email, company, plan, mrr, country, "
    " cpf, credit_card_type, credit_card_number, credit_card_expiry, created_at) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)

_SELECT_COLS = (
    "id, name, email, company, plan, mrr, country, "
    "cpf, credit_card_type, credit_card_number, credit_card_expiry, created_at"
)


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _needs_migration(conn: sqlite3.Connection) -> bool:
    """Return True if the customers table is missing any of the new columns."""
    cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(customers)").fetchall()
    }
    return not {"cpf", "credit_card_number", "credit_card_type", "credit_card_expiry"}.issubset(cols)


def init_db() -> None:
    """Create (or migrate) the schema and seed data."""
    conn = _get_connection()
    try:
        # Check if table exists and whether migration is needed
        table_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='customers'"
        ).fetchone()

        if table_exists and _needs_migration(conn):
            conn.execute("DROP TABLE customers")
            conn.commit()

        conn.execute(SCHEMA)
        conn.commit()

        count = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        if count == 0:
            conn.executemany(_INSERT_SQL, SEED_DATA)
            conn.commit()
    finally:
        conn.close()


def lookup_customer(query: str) -> str:
    """Search for customers by name, company name, CPF, or credit card number (full or partial).

    Args:
        query: Full or partial customer name, company name, CPF, or credit card number
               (e.g. "Alice", "Acme Corp", "529.982.247-25", "4111", or last 4 digits).
    """
    conn = _get_connection()
    try:
        rows = conn.execute(
            f"SELECT {_SELECT_COLS} FROM customers "
            "WHERE name               LIKE '%' || ? || '%' COLLATE NOCASE "
            "   OR company            LIKE '%' || ? || '%' COLLATE NOCASE "
            "   OR cpf                LIKE '%' || ? || '%' "
            "   OR credit_card_number LIKE '%' || ? || '%'",
            (query, query, query, query),
        ).fetchall()
        return json.dumps([dict(r) for r in rows]) if rows else json.dumps([])
    finally:
        conn.close()


def list_customers_by_plan(plan: str) -> str:
    """List all customers on a specific plan tier.

    Args:
        plan: The plan tier to filter by — one of 'free', 'pro', or 'enterprise'.
    """
    conn = _get_connection()
    try:
        rows = conn.execute(
            f"SELECT {_SELECT_COLS} FROM customers WHERE plan = ? COLLATE NOCASE",
            (plan.lower(),),
        ).fetchall()
        return json.dumps([dict(r) for r in rows]) if rows else json.dumps([])
    finally:
        conn.close()


def get_customer_stats() -> str:
    """Return aggregate customer statistics: total count, total MRR, and breakdown by plan."""
    conn = _get_connection()
    try:
        total = conn.execute(
            "SELECT COUNT(*) as count, COALESCE(SUM(mrr), 0) as total_mrr FROM customers"
        ).fetchone()
        breakdown = conn.execute(
            "SELECT plan, COUNT(*) as count, COALESCE(SUM(mrr), 0) as total_mrr "
            "FROM customers GROUP BY plan ORDER BY plan"
        ).fetchall()
        return json.dumps({
            "total_customers": total["count"],
            "total_mrr": total["total_mrr"],
            "by_plan": [dict(r) for r in breakdown],
        })
    finally:
        conn.close()
