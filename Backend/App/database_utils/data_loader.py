import json
import sqlite3
from pathlib import Path
from typing import Any


DATABASE_PATH = Path(__file__).resolve().parents[1] / "ethnography_ai.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def serialize_value(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, str):
        return value

    return json.dumps(value, ensure_ascii=False)


def deserialize_value(value: Any):
    if not isinstance(value, str):
        return value

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def ensure_database():
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS session_details (
            session_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            problem TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS problem_conversation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            domain TEXT,
            subdomain TEXT,
            questions TEXT,
            answers TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id)
            REFERENCES session_details(session_id)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS session_results (
            session_id TEXT PRIMARY KEY,
            patterns TEXT,
            recommendations TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id)
            REFERENCES session_details(session_id)
        )
        """)

        ensure_column(cursor, "session_details", "created_at", "TEXT")
        ensure_column(cursor, "session_details", "updated_at", "TEXT")
        ensure_column(cursor, "problem_conversation", "created_at", "TEXT")
        ensure_column(cursor, "session_results", "created_at", "TEXT")
        ensure_column(cursor, "session_results", "updated_at", "TEXT")

        connection.commit()


def ensure_column(cursor, table_name: str, column_name: str, column_type: str):
    columns = {
        row["name"]
        for row in cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
    }

    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def insert_session_details(data):
    ensure_database()

    with get_connection() as connection:
        connection.execute("""
        INSERT INTO session_details (
            session_id,
            name,
            age,
            problem,
            updated_at
        )
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(session_id) DO UPDATE SET
            name = excluded.name,
            age = excluded.age,
            problem = COALESCE(excluded.problem, session_details.problem),
            updated_at = CURRENT_TIMESTAMP
        """, (
            data["session_id"],
            data["name"],
            data["age"],
            data.get("problem"),
        ))

        connection.commit()


def insert_problem_conversation(data):
    ensure_database()

    with get_connection() as connection:
        connection.execute("""
        INSERT INTO problem_conversation (
            session_id,
            domain,
            subdomain,
            questions,
            answers
        )
        VALUES (?, ?, ?, ?, ?)
        """, (
            data["session_id"],
            data.get("domain"),
            data.get("subdomain"),
            serialize_value(data.get("questions")),
            serialize_value(data.get("answers")),
        ))

        connection.commit()


def insert_session_results(data):
    ensure_database()

    with get_connection() as connection:
        connection.execute("""
        INSERT INTO session_results (
            session_id,
            patterns,
            recommendations,
            updated_at
        )
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(session_id) DO UPDATE SET
            patterns = excluded.patterns,
            recommendations = excluded.recommendations,
            updated_at = CURRENT_TIMESTAMP
        """, (
            data["session_id"],
            serialize_value(data.get("patterns")),
            serialize_value(data.get("recommendations")),
        ))

        connection.commit()


def get_session_results(session_id: str):
    ensure_database()

    with get_connection() as connection:
        row = connection.execute("""
        SELECT session_id, patterns, recommendations, created_at, updated_at
        FROM session_results
        WHERE session_id = ?
        """, (session_id,)).fetchone()

    if row is None:
        return None

    result = dict(row)
    result["patterns"] = deserialize_value(result.get("patterns")) or []
    result["recommendations"] = deserialize_value(result.get("recommendations")) or []
    return result
