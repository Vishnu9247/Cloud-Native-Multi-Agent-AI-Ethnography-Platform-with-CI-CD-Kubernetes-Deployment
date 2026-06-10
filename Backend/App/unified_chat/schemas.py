from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator
from typing_extensions import TypedDict


class ChatMessage(TypedDict):
    role: str
    content: str


class QARecord(TypedDict, total=False):
    domain: str
    subdomain: str
    question: str
    answer: str
    validation_reason: str
    carried_gap: str


class DomainItem(TypedDict):
    name: str
    subdomains: list[str]


class UnifiedChatState(TypedDict, total=False):
    session_id: str
    name: str
    age: int
    stage: str
    conversation: list[ChatMessage]
    problem_conversation: list[ChatMessage]
    problem_statement: str
    domains: list[DomainItem]
    domain_index: int
    subdomain_index: int
    current_domain: str
    current_subdomain: str
    current_question: str
    current_subdomain_complete: bool
    pending_gap: str
    active_subdomain_qas: list[QARecord]
    qa_history: list[QARecord]
    completed_subdomains: list[str]
    subdomain_summaries: dict[str, str]
    pattern_queries: list[str]
    retrieved_context: list[dict[str, Any]]
    patterns: list[str]
    recommendations: list[str]
    last_user_input: str
    last_event: dict[str, Any]
    events: list[dict[str, Any]]


class ProblemCheckOutput(BaseModel):
    is_complete: bool = False
    reason: str = ""
    followup_question: str = ""


class DomainSpec(BaseModel):
    name: str
    subdomains: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("subdomains")
    @classmethod
    def clean_subdomains(cls, value: list[str]) -> list[str]:
        cleaned = []
        seen = set()
        for item in value:
            text = str(item).strip()
            key = text.lower()
            if text and key not in seen:
                cleaned.append(text)
                seen.add(key)
        return cleaned


class DomainSelectionOutput(BaseModel):
    domains: list[DomainSpec] = Field(default_factory=list)


class QuestionPlanOutput(BaseModel):
    action: Literal["ask", "complete_subdomain"] = "ask"
    question: str = ""
    reason: str = ""
    carries_gap: str = ""


class AnswerValidationOutput(BaseModel):
    is_subdomain_complete: bool = False
    reason: str = ""
    gap_to_carry_forward: str = ""


class SubdomainSummaryOutput(BaseModel):
    summary: str = ""
    evidence_quality: Literal["thin", "moderate", "strong"] = "thin"


class QueryExpansionOutput(BaseModel):
    queries: list[str] = Field(default_factory=list)

    @field_validator("queries")
    @classmethod
    def clean_queries(cls, value: list[str]) -> list[str]:
        cleaned = []
        seen = set()
        for item in value:
            text = str(item).strip()
            key = text.lower()
            if text and key not in seen:
                cleaned.append(text)
                seen.add(key)
        return cleaned


class PatternRecommendationOutput(BaseModel):
    patterns: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    @field_validator("patterns", "recommendations")
    @classmethod
    def clean_strings(cls, value: list[str]) -> list[str]:
        return [str(item).strip() for item in value if str(item).strip()]
