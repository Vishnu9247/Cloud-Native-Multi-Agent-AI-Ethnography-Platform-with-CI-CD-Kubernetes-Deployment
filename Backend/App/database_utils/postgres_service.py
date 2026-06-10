from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any
from urllib.parse import urlparse, urlunparse


def _postgres_config(database: str | None = None) -> dict[str, Any]:
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname": database or os.getenv("POSTGRES_DB", "ethnography_ai"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    }


def _database_url(database: str | None = None) -> str | None:
    url = os.getenv("DATABASE_URL")
    if not url or not database:
        return url

    parsed = urlparse(url)
    return urlunparse(parsed._replace(path=f"/{database}"))


def _target_database_name() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        return os.getenv("POSTGRES_DB", "ethnography_ai")

    parsed = urlparse(url)
    return parsed.path.lstrip("/") or os.getenv("POSTGRES_DB", "ethnography_ai")


def _driver():
    try:
        import psycopg2
        from psycopg2 import sql
        from psycopg2.extras import Json, RealDictCursor
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "Postgres support requires psycopg2-binary. "
            "Install it or include it in the backend Docker image."
        ) from error

    return psycopg2, sql, Json, RealDictCursor


def connect(database: str | None = None):
    psycopg2, _, _, RealDictCursor = _driver()
    url = _database_url(database)
    if url:
        return psycopg2.connect(url, cursor_factory=RealDictCursor)
    return psycopg2.connect(**_postgres_config(database), cursor_factory=RealDictCursor)


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
    _, sql, _, _ = _driver()
    database_name = _target_database_name()
    admin_database = os.getenv("POSTGRES_ADMIN_DB", "postgres")

    connection = connect(database=admin_database)
    connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (database_name,),
            )
            exists = cursor.fetchone()
            if not exists:
                cursor.execute(
                    sql.SQL("CREATE DATABASE {}").format(
                        sql.Identifier(database_name)
                    )
                )
    finally:
        connection.close()


def ensure_database() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    age INTEGER NOT NULL,
                    problem_statement TEXT,
                    stage TEXT NOT NULL DEFAULT 'awaiting_problem',
                    domains JSONB NOT NULL DEFAULT '[]'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id BIGSERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES sessions(session_id)
                        ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    stage TEXT,
                    domain TEXT,
                    subdomain TEXT,
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS interview_turns (
                    id BIGSERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES sessions(session_id)
                        ON DELETE CASCADE,
                    domain TEXT NOT NULL,
                    subdomain TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    validation_reason TEXT,
                    carried_gap TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS subdomain_summaries (
                    id BIGSERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES sessions(session_id)
                        ON DELETE CASCADE,
                    domain TEXT NOT NULL,
                    subdomain TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    evidence_quality TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (session_id, domain, subdomain)
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS session_results (
                    session_id TEXT PRIMARY KEY REFERENCES sessions(session_id)
                        ON DELETE CASCADE,
                    patterns JSONB NOT NULL DEFAULT '[]'::jsonb,
                    recommendations JSONB NOT NULL DEFAULT '[]'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
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
    _, _, Json, _ = _driver()
    ensure_database()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
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
                VALUES (%s, %s, %s, %s, %s, COALESCE(%s::jsonb, '[]'::jsonb), NOW())
                ON CONFLICT (session_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    age = EXCLUDED.age,
                    problem_statement = COALESCE(
                        EXCLUDED.problem_statement,
                        sessions.problem_statement
                    ),
                    stage = EXCLUDED.stage,
                    domains = COALESCE(EXCLUDED.domains, sessions.domains),
                    updated_at = NOW()
                """,
                (
                    session_id,
                    name,
                    age,
                    problem_statement,
                    stage,
                    Json(domains) if domains is not None else None,
                ),
            )


def update_session_problem(session_id: str, problem_statement: str) -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE sessions
                SET problem_statement = %s,
                    updated_at = NOW()
                WHERE session_id = %s
                """,
                (problem_statement, session_id),
            )


def update_session_stage(
    session_id: str,
    stage: str,
    domains: list[dict[str, Any]] | None = None,
) -> None:
    _, _, Json, _ = _driver()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE sessions
                SET stage = %s,
                    domains = COALESCE(%s::jsonb, domains),
                    updated_at = NOW()
                WHERE session_id = %s
                """,
                (
                    stage,
                    Json(domains) if domains is not None else None,
                    session_id,
                ),
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
    _, _, Json, _ = _driver()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
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
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                RETURNING id
                """,
                (
                    session_id,
                    role,
                    content,
                    stage,
                    domain,
                    subdomain,
                    Json(metadata or {}),
                ),
            )
            row = cursor.fetchone()
            return int(row["id"])


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
        with connection.cursor() as cursor:
            cursor.execute(
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
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
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
            row = cursor.fetchone()
            return int(row["id"])


def upsert_subdomain_summary(
    session_id: str,
    domain: str,
    subdomain: str,
    summary: str,
    evidence_quality: str | None = None,
) -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO subdomain_summaries (
                    session_id,
                    domain,
                    subdomain,
                    summary,
                    evidence_quality,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (session_id, domain, subdomain) DO UPDATE SET
                    summary = EXCLUDED.summary,
                    evidence_quality = EXCLUDED.evidence_quality,
                    updated_at = NOW()
                """,
                (session_id, domain, subdomain, summary, evidence_quality),
            )


def upsert_session_results(
    session_id: str,
    patterns: list[str],
    recommendations: list[str],
) -> None:
    _, _, Json, _ = _driver()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO session_results (
                    session_id,
                    patterns,
                    recommendations,
                    updated_at
                )
                VALUES (%s, %s::jsonb, %s::jsonb, NOW())
                ON CONFLICT (session_id) DO UPDATE SET
                    patterns = EXCLUDED.patterns,
                    recommendations = EXCLUDED.recommendations,
                    updated_at = NOW()
                """,
                (session_id, Json(patterns), Json(recommendations)),
            )


def fetch_session_messages(session_id: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT role, content, stage, domain, subdomain, metadata, created_at
                FROM conversation_messages
                WHERE session_id = %s
                ORDER BY created_at, id
                """,
                (session_id,),
            )
            return list(cursor.fetchall())
