"""
Database schema definitions and migrations.
"""

import sqlite3
from typing import Optional


def init_schema(db_path: str) -> sqlite3.Connection:
    """
    Initialize SQLite database with required tables.

    Creates tables for raw corpus, transitions, and compacted states.

    Args:
        db_path: Path to SQLite database file

    Returns:
        Database connection
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Raw corpus table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            channel_id TEXT,
            user_id TEXT,
            content TEXT
        )
    """
    )

    # Normalized transitions table (write-optimized)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS transitions (
            order_n INTEGER,
            state_text TEXT,
            next_token TEXT,
            count INTEGER,
            PRIMARY KEY (order_n, state_text, next_token)
        )
    """
    )

    # Compacted states table (read-optimized)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS states (
            order_n INTEGER,
            state_text TEXT,
            dist_blob BLOB,
            total_count INTEGER,
            updated_at DATETIME,
            PRIMARY KEY (order_n, state_text)
        )
    """
    )

    conn.commit()
    return conn
