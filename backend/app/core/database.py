"""Database connection helpers for the backend API layer."""

import logging

import psycopg2

from .settings import (DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_SSLMODE,
                       DB_USER)

logger = logging.getLogger(__name__)


def get_db_connection():
	try:
		conn = psycopg2.connect(
			host=DB_HOST,
			port=DB_PORT,
			user=DB_USER,
			password=DB_PASSWORD,
			database=DB_NAME,
			sslmode=DB_SSLMODE,
		)
		logger.debug("Connected to database %s", DB_NAME)
		return conn
	except Exception as exc:
		logger.error("Database connection failed: %s", exc)
		return None


def close_connection(conn):
	try:
		if conn:
			conn.close()
	except Exception as exc:
		logger.error("Error closing database connection: %s", exc)
