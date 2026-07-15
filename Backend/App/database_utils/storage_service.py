from __future__ import annotations

import os
from typing import Any


def get_database_backend() -> str:
    return os.getenv("DATABASE_BACKEND", "sqlite").strip().lower()


def _service():
    if get_database_backend() == "postgres":
        from App.database_utils import postgres_service

        return postgres_service

    from App.database_utils import sqlite_storage_service

    return sqlite_storage_service


def create_database_if_needed() -> None:
    _service().create_database_if_needed()


def ensure_database() -> None:
    _service().ensure_database()


def upsert_session(
    session_id: str,
    name: str,
    age: int,
    problem_statement: str | None = None,
    stage: str = "awaiting_problem",
    domains: list[dict[str, Any]] | None = None,
) -> None:
    _service().upsert_session(
        session_id=session_id,
        name=name,
        age=age,
        problem_statement=problem_statement,
        stage=stage,
        domains=domains,
    )


def update_session_problem(session_id: str, problem_statement: str) -> None:
    _service().update_session_problem(session_id, problem_statement)


def update_session_stage(
    session_id: str,
    stage: str,
    domains: list[dict[str, Any]] | None = None,
) -> None:
    _service().update_session_stage(session_id, stage, domains)


def insert_conversation_message(
    session_id: str,
    role: str,
    content: str,
    stage: str | None = None,
    domain: str | None = None,
    subdomain: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> int:
    return _service().insert_conversation_message(
        session_id=session_id,
        role=role,
        content=content,
        stage=stage,
        domain=domain,
        subdomain=subdomain,
        metadata=metadata,
    )


def insert_interview_turn(
    session_id: str,
    domain: str,
    subdomain: str,
    question: str,
    answer: str,
    validation_reason: str | None = None,
    carried_gap: str | None = None,
) -> int:
    return _service().insert_interview_turn(
        session_id=session_id,
        domain=domain,
        subdomain=subdomain,
        question=question,
        answer=answer,
        validation_reason=validation_reason,
        carried_gap=carried_gap,
    )


def upsert_subdomain_summary(
    session_id: str,
    domain: str,
    subdomain: str,
    summary: str,
    evidence_quality: str | None = None,
) -> None:
    _service().upsert_subdomain_summary(
        session_id=session_id,
        domain=domain,
        subdomain=subdomain,
        summary=summary,
        evidence_quality=evidence_quality,
    )


def upsert_session_results(
    session_id: str,
    patterns: list[str],
    recommendations: list[str],
) -> None:
    _service().upsert_session_results(
        session_id=session_id,
        patterns=patterns,
        recommendations=recommendations,
    )


def fetch_session_messages(session_id: str) -> list[dict[str, Any]]:
    return _service().fetch_session_messages(session_id)
