"""
SQLite database interface for corpus and transitions.
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional


class Database:
    """SQLite wrapper for Markov model storage."""

    def __init__(self, db_path: str):
        """
        Initialize or connect to SQLite database.

        Args:
            db_path: Path to database file
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize database schema if not already present."""
        cursor = self.conn.cursor()

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

        self.conn.commit()

    def add_message(
        self, user_id: str, channel_id: str, content: str, timestamp: Optional[datetime] = None
    ) -> int:
        """
        Store raw message in corpus table.

        Args:
            user_id: User identifier
            channel_id: Channel identifier
            content: Message content
            timestamp: Message timestamp (defaults to current time)

        Returns:
            Message ID
        """
        if timestamp is None:
            timestamp = datetime.now()

        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO messages (timestamp, channel_id, user_id, content) VALUES (?, ?, ?, ?)",
            (timestamp, channel_id, user_id, content),
        )
        self.conn.commit()
        return cursor.lastrowid

    def add_transition(self, order_n: int, state: str, next_token: str, count: int = 1) -> None:
        """
        Record or increment n-gram transition count.

        Args:
            order_n: N-gram order
            state: Current state (space-separated tokens)
            next_token: Next token
            count: Count increment (default 1)
        """
        cursor = self.conn.cursor()

        # Try to update first
        cursor.execute(
            """
            UPDATE transitions
            SET count = count + ?
            WHERE order_n = ? AND state_text = ? AND next_token = ?
        """,
            (count, order_n, state, next_token),
        )

        # If no rows were updated, insert new row
        if cursor.rowcount == 0:
            cursor.execute(
                """
                INSERT INTO transitions (order_n, state_text, next_token, count)
                VALUES (?, ?, ?, ?)
            """,
                (order_n, state, next_token, count),
            )

        self.conn.commit()

    def add_transitions_batch(self, transitions: List[tuple]) -> None:
        """
        Record multiple n-gram transitions in a single batch transaction.

        More efficient than calling add_transition() multiple times.

        Args:
            transitions: List of (order_n, state, next_token, count) tuples
        """
        if not transitions:
            return

        cursor = self.conn.cursor()

        try:
            # Begin explicit transaction
            cursor.execute("BEGIN TRANSACTION")

            for order_n, state, next_token, count in transitions:
                # Try to update first
                cursor.execute(
                    """
                    UPDATE transitions
                    SET count = count + ?
                    WHERE order_n = ? AND state_text = ? AND next_token = ?
                """,
                    (count, order_n, state, next_token),
                )

                # If no rows were updated, insert new row
                if cursor.rowcount == 0:
                    cursor.execute(
                        """
                        INSERT INTO transitions (order_n, state_text, next_token, count)
                        VALUES (?, ?, ?, ?)
                    """,
                        (order_n, state, next_token, count),
                    )

            # Commit entire batch as one transaction
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e

    def get_state(self, order_n: int, state: str) -> Optional[Dict]:
        """
        Retrieve compacted state from states table.

        Args:
            order_n: N-gram order
            state: State text

        Returns:
            Dictionary with dist_blob, total_count, updated_at or None
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT dist_blob, total_count, updated_at FROM states WHERE order_n = ? AND state_text = ?",
            (order_n, state),
        )
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def get_all_transitions(self) -> List:
        """
        Retrieve all transitions from database.

        Used to load model from database.

        Returns:
            List of (order_n, state_text, next_token, count) tuples
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT order_n, state_text, next_token, count FROM transitions ORDER BY order_n, state_text"
        )
        return cursor.fetchall()

    def get_messages(self, limit: Optional[int] = None, offset: int = 0) -> List[Dict]:
        """
        Retrieve messages from corpus for inspection/rebuilding.

        Args:
            limit: Maximum number of messages to retrieve
            offset: Offset for pagination

        Returns:
            List of message dictionaries
        """
        cursor = self.conn.cursor()

        if limit:
            cursor.execute(
                "SELECT id, timestamp, channel_id, user_id, content FROM messages ORDER BY id LIMIT ? OFFSET ?",
                (limit, offset),
            )
        else:
            cursor.execute(
                "SELECT id, timestamp, channel_id, user_id, content FROM messages ORDER BY id"
            )

        return [dict(row) for row in cursor.fetchall()]

    def compact(self) -> int:
        """
        Merge transitions table into states table.

        Returns:
            Number of rows compacted
        """
        cursor = self.conn.cursor()

        # Get all transitions grouped by order and state
        cursor.execute(
            """
            SELECT order_n, state_text, next_token, SUM(count) as total_count
            FROM transitions
            GROUP BY order_n, state_text, next_token
        """
        )

        compacted_count = 0

        for row in cursor.fetchall():
            order_n, state_text, next_token, total_count = row

            # For now, store transitions as JSON in dist_blob (simplified)
            # In production, this would use a more efficient binary format
            import json

            cursor.execute(
                """
                SELECT dist_blob, total_count FROM states
                WHERE order_n = ? AND state_text = ?
            """,
                (order_n, state_text),
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing state
                dist_blob_bytes, existing_total = existing
                dist = json.loads(dist_blob_bytes.decode()) if dist_blob_bytes else {}
                dist[next_token] = dist.get(next_token, 0) + total_count
                new_total = existing_total + total_count
            else:
                # Create new state
                dist = {next_token: total_count}
                new_total = total_count

            dist_blob = json.dumps(dist).encode()

            cursor.execute(
                """
                INSERT OR REPLACE INTO states (order_n, state_text, dist_blob, total_count, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (order_n, state_text, dist_blob, new_total),
            )
            compacted_count += 1

        # Clear transitions table
        cursor.execute("DELETE FROM transitions")
        self.conn.commit()

        return compacted_count

    def delete_user_data(self, user_id: str) -> int:
        """
        Delete all messages from a user.

        Args:
            user_id: User identifier

        Returns:
            Number of messages deleted
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
        self.conn.commit()
        return cursor.rowcount

    def rebuild_model(self, order_n: int, processor) -> None:
        """
        Rebuild Markov model from raw corpus.

        Useful when changing tokenization or filters.

        Args:
            order_n: N-gram order
            processor: TextProcessor instance
        """
        # This is for future use - would rebuild transitions from raw corpus
        pass

    def stats(self) -> Dict:
        """
        Return database statistics.

        Returns:
            Dictionary with corpus size, transition count, etc.
        """
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) as count FROM messages")
        message_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM transitions")
        transition_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM states")
        state_count = cursor.fetchone()["count"]

        cursor.execute("SELECT SUM(count) as total FROM transitions")
        total_transitions = cursor.fetchone()["total"] or 0

        return {
            "message_count": message_count,
            "transition_count": transition_count,
            "state_count": state_count,
            "total_transitions": total_transitions,
        }

    def clear_training_data(self) -> None:
        """
        Clear all training data (messages, transitions, states).

        WARNING: This deletes all Markov model training data.
        """
        cursor = self.conn.cursor()

        cursor.execute("DELETE FROM messages")
        cursor.execute("DELETE FROM transitions")
        cursor.execute("DELETE FROM states")

        self.conn.commit()

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
