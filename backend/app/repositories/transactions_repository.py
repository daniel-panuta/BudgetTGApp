"""Transaction persistence helpers for the backend API."""

import logging

from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


def list_recent_transactions(conn, limit=20):
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT
            t.id,
            t.date,
            t.amount,
            t.currency,
            t.amount_original,
            t.amount_mdl,
            t.raw_text,
            s.name AS shop_name,
            c.name AS category_name
        FROM transactions t
        JOIN shops s ON s.id = t.shop_id
        LEFT JOIN categories c ON c.id = s.default_category_id
        ORDER BY t.date DESC, t.id DESC
        LIMIT %s
        """,
        (limit,),
    )
    return cursor.fetchall()


def get_transaction_summary(conn):
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        """
        SELECT
            COUNT(*)::int AS total_transactions,
            COALESCE(SUM(CASE WHEN t.amount < 0 THEN ABS(t.amount_mdl) ELSE 0 END), 0) AS total_expenses,
            COALESCE(SUM(CASE WHEN t.amount > 0 THEN t.amount_mdl ELSE 0 END), 0) AS total_income
        FROM transactions t
        """
    )
    row = cursor.fetchone() or {
        "total_transactions": 0,
        "total_expenses": 0,
        "total_income": 0,
    }
    return {
        "total_transactions": row["total_transactions"],
        "total_expenses": float(row["total_expenses"] or 0),
        "total_income": float(row["total_income"] or 0),
    }