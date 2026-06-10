from __future__ import annotations

from typing import Any

from App.database_utils import postgres_service
from App.rag_utils.chroma_service import (
    add_conversation_message,
    add_doc,
    add_problem,
    create_vector_store,
)
from App.unified_chat.schemas import QARecord, UnifiedChatState


def initialize_session_storage(state: UnifiedChatState) -> None:
    postgres_service.ensure_database()
    create_vector_store(state["session_id"])
    postgres_service.upsert_session(
        session_id=state["session_id"],
        name=state["name"],
        age=state["age"],
        problem_statement=state.get("problem_statement") or None,
        stage=state.get("stage", "awaiting_problem"),
        domains=state.get("domains") or [],
    )


def persist_session_state(state: UnifiedChatState) -> None:
    postgres_service.upsert_session(
        session_id=state["session_id"],
        name=state["name"],
        age=state["age"],
        problem_statement=state.get("problem_statement") or None,
        stage=state.get("stage", "awaiting_problem"),
        domains=state.get("domains") or [],
    )


def persist_conversation_message(
    state: UnifiedChatState,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    postgres_service.insert_conversation_message(
        session_id=state["session_id"],
        role=role,
        content=content,
        stage=state.get("stage"),
        domain=state.get("current_domain") or None,
        subdomain=state.get("current_subdomain") or None,
        metadata=metadata or {},
    )
    add_conversation_message(
        session_id=state["session_id"],
        role=role,
        content=content,
        stage=state.get("stage", ""),
        domain=state.get("current_domain", ""),
        subdomain=state.get("current_subdomain", ""),
        metadata=metadata or {},
    )


def persist_problem_statement(state: UnifiedChatState) -> None:
    problem_statement = state.get("problem_statement", "")
    if not problem_statement:
        return

    postgres_service.update_session_problem(state["session_id"], problem_statement)
    add_problem(state["session_id"], problem_statement)


def persist_interview_turn(
    state: UnifiedChatState,
    qa: QARecord,
) -> None:
    postgres_service.insert_interview_turn(
        session_id=state["session_id"],
        domain=qa.get("domain", ""),
        subdomain=qa.get("subdomain", ""),
        question=qa.get("question", ""),
        answer=qa.get("answer", ""),
        validation_reason=qa.get("validation_reason"),
        carried_gap=qa.get("carried_gap"),
    )


def persist_subdomain_summary(
    state: UnifiedChatState,
    domain: str,
    subdomain: str,
    summary: str,
    evidence_quality: str | None = None,
) -> None:
    postgres_service.upsert_subdomain_summary(
        session_id=state["session_id"],
        domain=domain,
        subdomain=subdomain,
        summary=summary,
        evidence_quality=evidence_quality,
    )
    add_doc(
        state["session_id"],
        {
            "domain": domain,
            "tags": [domain, subdomain],
            "summary": summary,
        },
    )


def persist_results(state: UnifiedChatState) -> None:
    postgres_service.upsert_session_results(
        session_id=state["session_id"],
        patterns=state.get("patterns", []),
        recommendations=state.get("recommendations", []),
    )
