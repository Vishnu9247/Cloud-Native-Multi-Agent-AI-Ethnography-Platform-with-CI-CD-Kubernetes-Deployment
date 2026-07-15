from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Persona:
    row_number: int
    name: str
    problem: str
    person_details: str
    expected_solution: str


@dataclass
class RetrievalRecord:
    persona_row: int
    query: str
    rank: int
    document_id: str = ""
    domain: str = ""
    subdomain: str = ""
    document_type: str = ""
    distance: float | None = None
    confidence_score: float | None = None
    document: str = ""


@dataclass
class EvalResult:
    persona: Persona
    session_id: str = ""
    final_stage: str = ""
    problem_statement: str = ""
    domains: list[dict[str, Any]] = field(default_factory=list)
    subdomain_summaries: dict[str, str] = field(default_factory=dict)
    patterns: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    qa_history: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    retrieved_context: list[dict[str, Any]] = field(default_factory=list)
    retrieval_records: list[RetrievalRecord] = field(default_factory=list)
    generated_answer: str = ""
    semantic_similarity_score: float | None = None
    similarity_method: str = ""
    judge_scores: dict[str, Any] = field(default_factory=dict)
    failure_cases: list[str] = field(default_factory=list)
    error: str = ""
