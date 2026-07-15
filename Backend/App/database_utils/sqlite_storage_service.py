from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any


DATABASE_PATH = Path(
    os.getenv(
        "SQLITE_DATABASE_PATH",
        Path(__file__).resolve().parents[1] / "ethnography_ai.db",
    )
)


def _serialize(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _deserialize(value: Any):
    if not isinstance(value, str):
        return value

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def connect():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def get_connection():
    connection = connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def create_database_if_needed() -> None:
    ensure_database()


def ensure_database() -> None:
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                problem_statement TEXT,
                stage TEXT NOT NULL DEFAULT 'awaiting_problem',
                domains TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                stage TEXT,
                domain TEXT,
                subdomain TEXT,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                    ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS interview_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                subdomain TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                validation_reason TEXT,
                carried_gap TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                    ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS subdomain_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                subdomain TEXT NOT NULL,
                summary TEXT NOT NULL,
                evidence_quality TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (session_id, domain, subdomain),
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                    ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS session_results (
                session_id TEXT PRIMARY KEY,
                patterns TEXT NOT NULL DEFAULT '[]',
                recommendations TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                    ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_conversation_messages_session
            ON conversation_messages (session_id, created_at)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_interview_turns_session_domain
            ON interview_turns (session_id, domain, subdomain)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_subdomain_summaries_session
            ON subdomain_summaries (session_id)
            """
        )


def upsert_session(
    session_id: str,
    name: str,
    age: int,
    problem_statement: str | None = None,
    stage: str = "awaiting_problem",
    domains: list[dict[str, Any]] | None = None,
) -> None:
    ensure_database()

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO sessions (
                session_id,
                name,
                age,
                problem_statement,
                stage,
                domains,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(session_id) DO UPDATE SET
                name = excluded.name,
                age = excluded.age,
                problem_statement = COALESCE(
                    excluded.problem_statement,
                    sessions.problem_statement
                ),
                stage = excluded.stage,
                domains = excluded.domains,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                session_id,
                name,
                age,
                problem_statement,
                stage,
                _serialize(domains or []),
            ),
        )


def update_session_problem(session_id: str, problem_statement: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE sessions
            SET problem_statement = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
            """,
            (problem_statement, session_id),
        )


def update_session_stage(
    session_id: str,
    stage: str,
    domains: list[dict[str, Any]] | None = None,
) -> None:
    with get_connection() as connection:
        if domains is None:
            connection.execute(
                """
                UPDATE sessions
                SET stage = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
                """,
                (stage, session_id),
            )
            return

        connection.execute(
            """
            UPDATE sessions
            SET stage = ?,
                domains = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
            """,
            (stage, _serialize(domains), session_id),
        )


def insert_conversation_message(
    session_id: str,
    role: str,
    content: str,
    stage: str | None = None,
    domain: str | None = None,
    subdomain: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO conversation_messages (
                session_id,
                role,
                content,
                stage,
                domain,
                subdomain,
                metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                role,
                content,
                stage,
                domain,
                subdomain,
                _serialize(metadata or {}),
            ),
        )
        return int(cursor.lastrowid)


def insert_interview_turn(
    session_id: str,
    domain: str,
    subdomain: str,
    question: str,
    answer: str,
    validation_reason: str | None = None,
    carried_gap: str | None = None,
) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO interview_turns (
                session_id,
                domain,
                subdomain,
                question,
                answer,
                validation_reason,
                carried_gap
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                domain,
                subdomain,
                question,
                answer,
                validation_reason,
                carried_gap,
            ),
        )
        return int(cursor.lastrowid)


def upsert_subdomain_summary(
    session_id: str,
    domain: str,
    subdomain: str,
    summary: str,
    evidence_quality: str | None = None,
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO subdomain_summaries (
                session_id,
                domain,
                subdomain,
                summary,
                evidence_quality,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(session_id, domain, subdomain) DO UPDATE SET
                summary = excluded.summary,
                evidence_quality = excluded.evidence_quality,
                updated_at = CURRENT_TIMESTAMP
            """,
            (session_id, domain, subdomain, summary, evidence_quality),
        )


def upsert_session_results(
    session_id: str,
    patterns: list[str],
    recommendations: list[str],
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
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
            """,
            (session_id, _serialize(patterns), _serialize(recommendations)),
        )


def fetch_session_messages(session_id: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT role, content, stage, domain, subdomain, metadata, created_at
            FROM conversation_messages
            WHERE session_id = ?
            ORDER BY created_at, id
            """,
            (session_id,),
        ).fetchall()

    messages = []
    for row in rows:
        item = dict(row)
        item["metadata"] = _deserialize(item.get("metadata")) or {}
        messages.append(item)
    return messages
