"""Transaction use-cases for the backend API."""

from ..core.database import close_connection, get_db_connection
from ..repositories.transactions_repository import (get_transaction_summary,
                                                    list_recent_transactions)


def get_transactions_page(limit=20):
    conn = get_db_connection()
    if not conn:
        raise RuntimeError("Database connection failed")

    try:
        items = list_recent_transactions(conn, limit=limit)
        summary = get_transaction_summary(conn)
        return {
            "items": items,
            "summary": summary,
        }
    finally:
        close_connection(conn)