"""Local SQLite persistence layer.

Drop-in replacement for the previous AWS DynamoDB tables (Users,
ChatHistory, Feedback). Everything is stored in a single `scai.db`
file next to the application, so the platform runs fully locally
with zero cloud dependencies.
"""

import json
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scai.db")


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                password TEXT,
                email TEXT UNIQUE,
                registration_date TEXT,
                user_type TEXT DEFAULT 'basic',
                question_count INTEGER DEFAULT 0,
                last_question_date TEXT
            );

            CREATE TABLE IF NOT EXISTS chat_history (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_name TEXT,
                start_time TEXT,
                chat_history TEXT,
                timestamp TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
            CREATE INDEX IF NOT EXISTS idx_chat_user_time
                ON chat_history (user_id, timestamp DESC);

            CREATE TABLE IF NOT EXISTS feedback (
                user_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                feedback TEXT,
                PRIMARY KEY (user_id, timestamp)
            );
            """
        )


# ---------- Users ----------

def get_user(user_id):
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def get_user_by_email(email):
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None


def upsert_user(user):
    with _conn() as c:
        c.execute(
            """
            INSERT INTO users (id, first_name, last_name, username, password,
                               email, registration_date, user_type,
                               question_count, last_question_date)
            VALUES (:id, :first_name, :last_name, :username, :password,
                    :email, :registration_date, :user_type,
                    :question_count, :last_question_date)
            ON CONFLICT(id) DO UPDATE SET
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                username = excluded.username,
                password = excluded.password,
                email = excluded.email,
                registration_date = excluded.registration_date,
                user_type = excluded.user_type,
                question_count = excluded.question_count,
                last_question_date = excluded.last_question_date
            """,
            user,
        )


# ---------- Chat history ----------

def save_chat_session(session_id, user_id, session_name, start_time, messages, timestamp):
    with _conn() as c:
        c.execute(
            """
            INSERT OR REPLACE INTO chat_history
                (session_id, user_id, session_name, start_time, chat_history, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, user_id, session_name, start_time, json.dumps(messages), timestamp),
        )


def get_chat_history(user_id):
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM chat_history WHERE user_id = ? ORDER BY timestamp DESC",
            (user_id,),
        ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["chat_history"] = json.loads(item["chat_history"] or "[]")
            items.append(item)
        return items


# ---------- Feedback ----------

def save_feedback(user_id, timestamp, feedback_text):
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO feedback (user_id, timestamp, feedback) VALUES (?, ?, ?)",
            (user_id, timestamp, feedback_text),
        )
