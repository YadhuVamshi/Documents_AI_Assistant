import os
import sqlite3

DATABASE_NAME = "data/chat_memory.db"


def initialize_database():
    os.makedirs(os.path.dirname(DATABASE_NAME), exist_ok=True)
    conn = sqlite3.connect(DATABASE_NAME)

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def save_message(session_id, role, message):
    conn = sqlite3.connect(DATABASE_NAME)

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO chat_history
        (session_id, role, message)
        VALUES (?, ?, ?)
        """,
        (session_id, role, message)
    )

    conn.commit()
    conn.close()


def get_chat_history(session_id, limit=6):
    conn = sqlite3.connect(DATABASE_NAME)

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT role, message
        FROM chat_history
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (session_id, limit)
    )

    rows = cursor.fetchall()

    conn.close()

    rows.reverse()

    return rows