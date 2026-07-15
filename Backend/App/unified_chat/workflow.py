from __future__ import annotations

import json
import uuid
from copy import deepcopy
from difflib import SequenceMatcher
from typing import Any, TypeVar

from langgraph.graph import END, StateGraph
from pydantic import BaseModel

from App.llm_utils.llm_client import invoke_llm
from App.prompt_utils.unified_chat_prompts import (
    ANSWER_VALIDATION_PROMPT,
    DOMAIN_SELECTION_PROMPT,
    PATTERN_RECOMMENDATION_PROMPT,
    PROBLEM_COMPLETENESS_PROMPT,
    QUERY_EXPANSION_PROMPT,
    QUESTION_PLANNING_PROMPT,
    SUBDOMAIN_SUMMARY_PROMPT,
)
from App.rag_utils.chroma_service import parse_query_result, query_docs
from App.unified_chat.persistence import (
    initialize_session_storage,
    persist_conversation_message,
    persist_interview_turn,
    persist_problem_statement,
    persist_results,
    persist_session_state,
    persist_subdomain_summary,
)
from App.unified_chat.schemas import (
    AnswerValidationOutput,
    ChatMessage,
    DomainItem,
    DomainSelectionOutput,
    PatternRecommendationOutput,
    ProblemCheckOutput,
    QARecord,
    QueryExpansionOutput,
    QuestionPlanOutput,
    SubdomainSummaryOutput,
    UnifiedChatState,
)


MAX_QUESTIONS_PER_SUBDOMAIN = 4
MAX_CONTEXT_DOCS = 4
MAX_CONTEXT_CHARS = 6000

ModelT = TypeVar("ModelT", bound=BaseModel)


def create_session(name: str, age: int | str) -> UnifiedChatState:
    session_id = str(uuid.uuid4())
    age_value = int(age)

    state: UnifiedChatState = {
        "session_id": session_id,
        "name": name.strip(),
        "age": age_value,
        "stage": "awaiting_problem",
        "conversation": [],
        "problem_conversation": [],
        "problem_statement": "",
        "domains": [],
        "domain_index": 0,
        "subdomain_index": 0,
        "current_domain": "",
        "current_subdomain": "",
        "current_question": "",
        "current_subdomain_complete": False,
        "pending_gap": "",
        "active_subdomain_qas": [],
        "qa_history": [],
        "completed_subdomains": [],
        "subdomain_summaries": {},
        "pattern_queries": [],
        "retrieved_context": [],
        "patterns": [],
        "recommendations": [],
        "last_user_input": "",
        "events": [],
        "last_event": {},
    }

    initialize_session_storage(state)

    greeting = (
        f"Hello, {state['name']}. I am here to understand your experience. "
        "What problem would you like to talk about today?"
    )
    _append_assistant_message(state, greeting)
    _push_event(
        state,
        {
            "type": "session_created",
            "session_id": session_id,
            "message": greeting,
        },
    )
    return state


def handle_user_message(state: UnifiedChatState, message: str) -> UnifiedChatState:
    next_state = _ensure_state_defaults(deepcopy(state))
    next_state["events"] = []

    user_message = message.strip()
    if not user_message:
        prompt = "Please share a little detail so I can continue."
        _append_assistant_message(next_state, prompt)
        _push_event(next_state, {"type": "empty_message", "message": prompt})
        return next_state

    next_state["last_user_input"] = user_message
    _append_user_message(next_state, user_message)

    if next_state["stage"] in {"awaiting_problem", "problem_followup"}:
        next_state["problem_conversation"].append(
            {"role": "user", "content": user_message}
        )

    elif next_state["stage"] == "interview" and next_state["current_question"]:
        qa: QARecord = {
            "domain": next_state["current_domain"],
            "subdomain": next_state["current_subdomain"],
            "question": next_state["current_question"],
            "answer": user_message,
        }
        next_state["active_subdomain_qas"].append(qa)
        next_state["qa_history"].append(qa)

    return conversation_app.invoke(next_state)


def generate_results(state: UnifiedChatState) -> UnifiedChatState:
    next_state = _ensure_state_defaults(deepcopy(state))
    next_state["events"] = []
    return results_app.invoke(next_state)


def _ensure_state_defaults(state: UnifiedChatState) -> UnifiedChatState:
    state.setdefault("session_id", str(uuid.uuid4()))
    state.setdefault("name", "")
    state.setdefault("age", 0)
    state.setdefault("stage", "awaiting_problem")
    state.setdefault("conversation", [])
    state.setdefault("problem_conversation", [])
    state.setdefault("problem_statement", "")
    state.setdefault("domains", [])
    state.setdefault("domain_index", 0)
    state.setdefault("subdomain_index", 0)
    state.setdefault("current_domain", "")
    state.setdefault("current_subdomain", "")
    state.setdefault("current_question", "")
    state.setdefault("current_subdomain_complete", False)
    state.setdefault("pending_gap", "")
    state.setdefault("active_subdomain_qas", [])
    state.setdefault("qa_history", [])
    state.setdefault("completed_subdomains", [])
    state.setdefault("subdomain_summaries", {})
    state.setdefault("pattern_queries", [])
    state.setdefault("retrieved_context", [])
    state.setdefault("patterns", [])
    state.setdefault("recommendations", [])
    state.setdefault("last_user_input", "")
    state.setdefault("events", [])
    state.setdefault("last_event", {})
    return state


def _append_user_message(state: UnifiedChatState, content: str) -> None:
    state["conversation"].append({"role": "user", "content": content})
    persist_conversation_message(state, "user", content)


def _append_assistant_message(state: UnifiedChatState, content: str) -> None:
    state["conversation"].append({"role": "assistant", "content": content})
    persist_conversation_message(state, "assistant", content)


def _push_event(state: UnifiedChatState, event: dict[str, Any]) -> None:
    state["events"].append(event)
    state["last_event"] = event


def _format_messages(messages: list[ChatMessage]) -> str:
    if not messages:
        return "No messages yet."
    return "\n\n".join(
        f"{message['role'].upper()}: {message['content']}" for message in messages
    )


def _format_qas(qas: list[QARecord]) -> str:
    if not qas:
        return "No question-answer evidence yet."

    blocks = []
    for index, qa in enumerate(qas, start=1):
        blocks.append(
            "\n".join(
                [
                    f"{index}. Question: {qa.get('question', '')}",
                    f"Answer: {qa.get('answer', '')}",
                ]
            )
        )
    return "\n\n".join(blocks)


def _question_texts(qas: list[QARecord], limit: int | None = None) -> list[str]:
    questions = [
        qa.get("question", "").strip()
        for qa in qas
        if qa.get("question", "").strip()
    ]
    if limit is None:
        return questions
    return questions[-limit:]


def _normalize_question_text(question: str) -> str:
    return " ".join(
        "".join(
            character.lower() if character.isalnum() or character.isspace() else " "
            for character in question
        ).split()
    )


def _is_repetitive_question(question: str, previous_questions: list[str]) -> bool:
    normalized_question = _normalize_question_text(question)
    if not normalized_question:
        return False

    for previous_question in previous_questions:
        normalized_previous = _normalize_question_text(previous_question)
        if not normalized_previous:
            continue

        if normalized_question == normalized_previous:
            return True

        similarity = SequenceMatcher(
            None,
            normalized_question,
            normalized_previous,
        ).ratio()
        if similarity >= 0.64:
            return True

    return False


def _fallback_question_for_subdomain(
    subdomain: str,
    pending_gap: str = "",
) -> str:
    subdomain_key = subdomain.strip().lower()
    questions = {
        "stress": (
            "When the alarm rings on a morning without obligations, what kind "
            "of pressure, tension, or mental resistance do you notice?"
        ),
        "emotions": (
            "What emotions show up before bed and right after the alarm when "
            "you know no one is waiting for you?"
        ),
        "identity": (
            "What does waking up early, or not waking up early, make you "
            "believe about yourself?"
        ),
        "routine": (
            "Walk me through the last hour before sleep and the first ten "
            "minutes after your alarm on days you sleep in."
        ),
        "productivity": (
            "How does waking up late change what you do next, and how does "
            "that affect the rest of your day?"
        ),
        "motivation": (
            "What usually makes waking up early feel worth it to you, and what "
            "makes that reason fade after a few days?"
        ),
        "goals": (
            "What larger goal do you connect with waking up early, and how "
            "clear does that goal feel when the alarm actually rings?"
        ),
    }
    base_question = questions.get(
        subdomain_key,
        f"What part of {subdomain.lower()} most affects this problem in your day-to-day life?",
    )

    if pending_gap:
        return f"Keeping this gap in mind: {pending_gap} {base_question}"

    return base_question


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _clean_json_text(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.removeprefix("```json").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").strip()
    if cleaned.endswith("```"):
        cleaned = cleaned.removesuffix("```").strip()

    first_object = cleaned.find("{")
    last_object = cleaned.rfind("}")
    if first_object != -1 and last_object != -1 and last_object > first_object:
        return cleaned[first_object : last_object + 1]

    return cleaned


def _parse_model(response: str, model_type: type[ModelT], fallback: ModelT) -> ModelT:
    cleaned = _clean_json_text(response)
    try:
        return model_type.model_validate_json(cleaned)
    except Exception:
        try:
            return model_type.model_validate(json.loads(cleaned))
        except Exception:
            return fallback


def _problem_statement_from_state(state: UnifiedChatState) -> str:
    user_messages = [
        message["content"]
        for message in state["problem_conversation"]
        if message["role"] == "user"
    ]
    return "\n".join(user_messages).strip()


def _safe_add_problem(state: UnifiedChatState) -> None:
    if state["session_id"] and state["problem_statement"]:
        persist_problem_statement(state)


def _safe_add_summary(
    state: UnifiedChatState,
    domain: str,
    subdomain: str,
    summary: str,
    evidence_quality: str | None = None,
) -> None:
    if not summary:
        return

    persist_subdomain_summary(state, domain, subdomain, summary, evidence_quality)


def _safe_query_context(
    state: UnifiedChatState,
    query: str,
    n_results: int = MAX_CONTEXT_DOCS,
) -> list[dict[str, Any]]:
    if not state["session_id"] or not query.strip():
        return []

    try:
        result = query_docs(state["session_id"], query, n_results=n_results)
        return parse_query_result(result)
    except Exception:
        return []


def _trim_context(context: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trimmed = []
    total_chars = 0

    for item in context:
        document = str(item.get("document", ""))
        remaining = MAX_CONTEXT_CHARS - total_chars
        if remaining <= 0:
            break

        limited_document = document[:remaining]
        total_chars += len(limited_document)
        trimmed.append(
            {
                "id": item.get("id"),
                "domain": item.get("domain"),
                "subdomain": item.get("subdomain"),
                "document_type": item.get("document_type"),
                "document": limited_document,
            }
        )

    return trimmed


def _fallback_domains() -> list[DomainItem]:
    return [
        {"name": "Psychological", "subdomains": ["Stress", "Emotions"]},
        {"name": "Behavioral", "subdomains": ["Routine", "Productivity"]},
        {"name": "Aspirational", "subdomains": ["Goals", "Motivation"]},
    ]


def _format_domain_plan(domains: list[DomainItem]) -> str:
    lines = ["Here are the areas we will explore:"]
    for domain in domains:
        subdomains = ", ".join(domain["subdomains"])
        lines.append(f"- {domain['name']}: {subdomains}")
    return "\n".join(lines)


def _normalize_domains(output: DomainSelectionOutput) -> list[DomainItem]:
    normalized: list[DomainItem] = []
    seen_domains = set()

    for domain in output.domains:
        name = domain.name.strip()
        key = name.lower()
        if not name or key in seen_domains or not domain.subdomains:
            continue
        normalized.append({"name": name, "subdomains": domain.subdomains})
        seen_domains.add(key)

    return normalized or _fallback_domains()


def _set_current_subdomain(state: UnifiedChatState) -> tuple[str, str]:
    domains = state["domains"]

    while state["domain_index"] < len(domains):
        domain = domains[state["domain_index"]]
        subdomains = domain.get("subdomains", [])

        if state["subdomain_index"] < len(subdomains):
            current_domain = domain["name"]
            current_subdomain = subdomains[state["subdomain_index"]]
            state["current_domain"] = current_domain
            state["current_subdomain"] = current_subdomain
            return current_domain, current_subdomain

        state["domain_index"] += 1
        state["subdomain_index"] = 0

    state["current_domain"] = ""
    state["current_subdomain"] = ""
    return "", ""


def _current_subdomain_key(state: UnifiedChatState) -> str:
    if not state["current_domain"] or not state["current_subdomain"]:
        return ""
    return f"{state['current_domain']}::{state['current_subdomain']}"


def _advance_subdomain(state: UnifiedChatState) -> None:
    key = _current_subdomain_key(state)
    if key and key not in state["completed_subdomains"]:
        state["completed_subdomains"].append(key)

    state["subdomain_index"] += 1
    state["current_domain"] = ""
    state["current_subdomain"] = ""
    state["current_question"] = ""
    state["current_subdomain_complete"] = False
    state["pending_gap"] = ""
    state["active_subdomain_qas"] = []


def _mark_ready_for_results(state: UnifiedChatState) -> UnifiedChatState:
    state["stage"] = "ready_for_results"
    persist_session_state(state)
    state["current_question"] = ""
    message = (
        "We have explored the selected domains. You can generate results now."
    )
    _append_assistant_message(state, message)
    _push_event(
        state,
        {
            "type": "ready_for_results",
            "message": message,
            "can_generate_results": True,
        },
    )
    return state


def _route_turn(state: UnifiedChatState) -> str:
    stage = state.get("stage", "awaiting_problem")

    if stage in {"awaiting_problem", "problem_followup"}:
        return "check_problem"

    if stage == "interview":
        if state.get("current_question"):
            return "validate_answer"
        return "prepare_next_question"

    return "done"


def check_problem_node(state: UnifiedChatState) -> UnifiedChatState:
    prompt = PROBLEM_COMPLETENESS_PROMPT.format(
        name=state["name"],
        age=state["age"],
        conversation_text=_format_messages(state["problem_conversation"]),
    )

    response = invoke_llm(prompt, purpose="unified_chat.problem_check")
    output = _parse_model(
        response,
        ProblemCheckOutput,
        ProblemCheckOutput(
            is_complete=False,
            reason="The response could not be parsed.",
            followup_question="Could you tell me a little more about what you want to improve?",
        ),
    )

    problem_attempts = len(
        [
            message
            for message in state["problem_conversation"]
            if message["role"] == "user"
        ]
    )

    if output.is_complete or problem_attempts >= 3:
        state["problem_statement"] = _problem_statement_from_state(state)
        state["stage"] = "domain_selection"
        _safe_add_problem(state)
        persist_session_state(state)
        _push_event(
            state,
            {
                "type": "problem_complete",
                "reason": output.reason,
                "problem_statement": state["problem_statement"],
            },
        )
        return state

    followup = output.followup_question.strip()
    if not followup:
        followup = "What feels most important for me to understand about this problem?"

    state["stage"] = "problem_followup"
    persist_session_state(state)
    state["problem_conversation"].append({"role": "assistant", "content": followup})
    _append_assistant_message(state, followup)
    _push_event(
        state,
        {
            "type": "problem_followup",
            "reason": output.reason,
            "message": followup,
        },
    )
    return state


def route_after_problem_check(state: UnifiedChatState) -> str:
    if state["stage"] == "domain_selection":
        return "select_domains"
    return "done"


def select_domains_node(state: UnifiedChatState) -> UnifiedChatState:
    prompt = DOMAIN_SELECTION_PROMPT.format(
        problem_statement=state["problem_statement"],
    )
    response = invoke_llm(prompt, purpose="unified_chat.domain_selection")
    output = _parse_model(
        response,
        DomainSelectionOutput,
        DomainSelectionOutput(domains=[]),
    )

    state["domains"] = _normalize_domains(output)
    state["domain_index"] = 0
    state["subdomain_index"] = 0
    state["stage"] = "interview"
    persist_session_state(state)

    message = _format_domain_plan(state["domains"])
    _append_assistant_message(state, message)
    _push_event(
        state,
        {
            "type": "domains_selected",
            "domains": state["domains"],
            "message": message,
        },
    )
    return state


def prepare_next_question_node(state: UnifiedChatState) -> UnifiedChatState:
    for _ in range(_remaining_subdomain_count(state) + 1):
        domain, subdomain = _set_current_subdomain(state)
        if not domain or not subdomain:
            return _mark_ready_for_results(state)

        asked_questions = _question_texts(state["active_subdomain_qas"])
        all_prior_questions = _question_texts(state["qa_history"], limit=16)
        query = "\n".join(
            [
                state["problem_statement"],
                f"Domain: {domain}",
                f"Subdomain: {subdomain}",
                state.get("pending_gap", ""),
            ]
        )
        context = _trim_context(_safe_query_context(state, query))

        prompt = QUESTION_PLANNING_PROMPT.format(
            problem_statement=state["problem_statement"],
            domain=domain,
            subdomain=subdomain,
            pending_gap=state.get("pending_gap") or "No pending gap.",
            asked_questions=_compact_json(asked_questions),
            all_prior_questions=_compact_json(all_prior_questions),
            subdomain_conversation=_format_qas(state["active_subdomain_qas"]),
            retrieved_context=_compact_json(context),
        )
        response = invoke_llm(prompt, purpose="unified_chat.question_planning")
        output = _parse_model(
            response,
            QuestionPlanOutput,
            QuestionPlanOutput(
                action="ask",
                question=_fallback_question_for_subdomain(
                    subdomain,
                    state.get("pending_gap", ""),
                ),
                reason="Fallback question.",
                carries_gap=state.get("pending_gap", ""),
            ),
        )

        if output.action == "complete_subdomain" and (
            context or state["active_subdomain_qas"]
        ):
            summary = _summary_from_existing_context(domain, subdomain, context)
            _complete_subdomain_from_summary(state, domain, subdomain, summary)
            continue

        question = output.question.strip()
        if not question or _is_repetitive_question(question, all_prior_questions):
            question = _fallback_question_for_subdomain(
                subdomain,
                state.get("pending_gap", ""),
            )
            output.reason = (
                "Fallback question used because the generated question was "
                "empty or too similar to a prior question."
            )

        state["current_question"] = question
        state["current_subdomain_complete"] = False
        _append_assistant_message(state, question)
        _push_event(
            state,
            {
                "type": "question",
                "domain": domain,
                "subdomain": subdomain,
                "question": question,
                "reason": output.reason,
                "carries_gap": output.carries_gap,
            },
        )
        return state

    return _mark_ready_for_results(state)


def _remaining_subdomain_count(state: UnifiedChatState) -> int:
    remaining = 0
    for domain_index, domain in enumerate(state["domains"]):
        subdomains = domain.get("subdomains", [])
        if domain_index < state["domain_index"]:
            continue
        if domain_index == state["domain_index"]:
            remaining += max(0, len(subdomains) - state["subdomain_index"])
        else:
            remaining += len(subdomains)
    return remaining


def _summary_from_existing_context(
    domain: str,
    subdomain: str,
    context: list[dict[str, Any]],
) -> str:
    documents = [
        str(item.get("document", "")).strip()
        for item in context
        if str(item.get("document", "")).strip()
    ]
    if not documents:
        return f"{domain} / {subdomain} was already covered by earlier answers."
    return " ".join(documents)[:MAX_CONTEXT_CHARS]


def _complete_subdomain_from_summary(
    state: UnifiedChatState,
    domain: str,
    subdomain: str,
    summary: str,
) -> None:
    key = f"{domain}::{subdomain}"
    state["subdomain_summaries"][key] = summary
    _safe_add_summary(state, domain, subdomain, summary, "moderate")
    _push_event(
        state,
        {
            "type": "subdomain_completed",
            "domain": domain,
            "subdomain": subdomain,
            "summary": summary,
        },
    )
    _advance_subdomain(state)


def validate_answer_node(state: UnifiedChatState) -> UnifiedChatState:
    if not state["active_subdomain_qas"]:
        state["current_question"] = ""
        state["current_subdomain_complete"] = False
        return state

    latest_qa = state["active_subdomain_qas"][-1]
    prompt = ANSWER_VALIDATION_PROMPT.format(
        problem_statement=state["problem_statement"],
        domain=state["current_domain"],
        subdomain=state["current_subdomain"],
        current_question=latest_qa.get("question", ""),
        latest_answer=latest_qa.get("answer", ""),
        subdomain_conversation=_format_qas(state["active_subdomain_qas"]),
    )

    response = invoke_llm(prompt, purpose="unified_chat.answer_validation")
    output = _parse_model(
        response,
        AnswerValidationOutput,
        AnswerValidationOutput(
            is_subdomain_complete=False,
            reason="The response could not be parsed.",
            gap_to_carry_forward="Ask for one concrete example or missing detail.",
        ),
    )

    if len(state["active_subdomain_qas"]) >= MAX_QUESTIONS_PER_SUBDOMAIN:
        output.is_subdomain_complete = True
        output.gap_to_carry_forward = ""

    latest_qa["validation_reason"] = output.reason
    latest_qa["carried_gap"] = output.gap_to_carry_forward
    persist_interview_turn(state, latest_qa)

    state["current_subdomain_complete"] = output.is_subdomain_complete
    state["pending_gap"] = output.gap_to_carry_forward.strip()
    state["current_question"] = ""

    _push_event(
        state,
        {
            "type": "answer_validated",
            "domain": state["current_domain"],
            "subdomain": state["current_subdomain"],
            "is_subdomain_complete": output.is_subdomain_complete,
            "reason": output.reason,
            "gap_to_carry_forward": state["pending_gap"],
        },
    )
    return state


def route_after_validation(state: UnifiedChatState) -> str:
    if state.get("current_subdomain_complete"):
        return "summarize_subdomain"
    return "prepare_next_question"


def summarize_subdomain_node(state: UnifiedChatState) -> UnifiedChatState:
    domain = state["current_domain"]
    subdomain = state["current_subdomain"]
    query = "\n".join([state["problem_statement"], domain, subdomain])
    context = _trim_context(_safe_query_context(state, query))

    prompt = SUBDOMAIN_SUMMARY_PROMPT.format(
        problem_statement=state["problem_statement"],
        domain=domain,
        subdomain=subdomain,
        subdomain_conversation=_format_qas(state["active_subdomain_qas"]),
        retrieved_context=_compact_json(context),
    )
    response = invoke_llm(prompt, purpose="unified_chat.subdomain_summary")
    output = _parse_model(
        response,
        SubdomainSummaryOutput,
        SubdomainSummaryOutput(
            summary=_format_qas(state["active_subdomain_qas"]),
            evidence_quality="thin",
        ),
    )

    summary = output.summary.strip() or _format_qas(state["active_subdomain_qas"])
    key = _current_subdomain_key(state)
    state["subdomain_summaries"][key] = summary
    _safe_add_summary(state, domain, subdomain, summary, output.evidence_quality)

    message = (
        f"Thanks, that gives me enough about {subdomain}. "
        "I will move to the next area."
    )
    _append_assistant_message(state, message)
    _push_event(
        state,
        {
            "type": "subdomain_completed",
            "domain": domain,
            "subdomain": subdomain,
            "summary": summary,
            "evidence_quality": output.evidence_quality,
            "message": message,
        },
    )
    return state


def advance_after_summary_node(state: UnifiedChatState) -> UnifiedChatState:
    _advance_subdomain(state)
    if _remaining_subdomain_count(state) <= 0:
        return _mark_ready_for_results(state)
    return state


def route_after_advance(state: UnifiedChatState) -> str:
    if state["stage"] == "ready_for_results":
        return "done"
    return "prepare_next_question"


def query_expansion_node(state: UnifiedChatState) -> UnifiedChatState:
    prompt = QUERY_EXPANSION_PROMPT.format(
        problem_statement=state["problem_statement"],
        domains=_compact_json(state["domains"]),
        subdomain_summaries=_compact_json(state["subdomain_summaries"]),
    )
    response = invoke_llm(prompt, purpose="unified_chat.query_expansion")
    output = _parse_model(
        response,
        QueryExpansionOutput,
        QueryExpansionOutput(queries=[]),
    )

    queries = output.queries or _fallback_pattern_queries(state)
    state["pattern_queries"] = queries
    _push_event(
        state,
        {
            "type": "pattern_queries_generated",
            "queries": queries,
        },
    )
    return state


def _fallback_pattern_queries(state: UnifiedChatState) -> list[str]:
    queries = [state["problem_statement"]]
    for domain in state["domains"]:
        for subdomain in domain["subdomains"]:
            queries.append(
                f"{state['problem_statement']} {domain['name']} {subdomain} patterns"
            )
    return [query for query in queries if query.strip()][:8]


def retrieve_pattern_context_node(state: UnifiedChatState) -> UnifiedChatState:
    seen = set()
    context: list[dict[str, Any]] = []

    for query in state["pattern_queries"]:
        for item in _safe_query_context(state, query):
            key = item.get("id") or item.get("document")
            if key in seen:
                continue
            seen.add(key)
            context.append(item)

    if not context:
        for key, summary in state["subdomain_summaries"].items():
            domain, _, subdomain = key.partition("::")
            context.append(
                {
                    "id": key,
                    "domain": domain,
                    "subdomain": subdomain,
                    "document_type": "subdomain_summary",
                    "document": summary,
                }
            )

    state["retrieved_context"] = _trim_context(context)
    _push_event(
        state,
        {
            "type": "pattern_context_retrieved",
            "context_count": len(state["retrieved_context"]),
        },
    )
    return state


def pattern_recommendation_node(state: UnifiedChatState) -> UnifiedChatState:
    prompt = PATTERN_RECOMMENDATION_PROMPT.format(
        problem_statement=state["problem_statement"],
        domains=_compact_json(state["domains"]),
        subdomain_summaries=_compact_json(state["subdomain_summaries"]),
        expanded_queries=_compact_json(state["pattern_queries"]),
        retrieved_context=_compact_json(state["retrieved_context"]),
    )
    response = invoke_llm(prompt, purpose="unified_chat.pattern_recommendation")
    output = _parse_model(
        response,
        PatternRecommendationOutput,
        PatternRecommendationOutput(patterns=[], recommendations=[]),
    )

    state["patterns"] = output.patterns
    state["recommendations"] = output.recommendations
    state["stage"] = "results"
    persist_results(state)
    persist_session_state(state)

    message = _format_results_message(state["patterns"], state["recommendations"])
    _append_assistant_message(state, message)
    _push_event(
        state,
        {
            "type": "results_ready",
            "patterns": state["patterns"],
            "recommendations": state["recommendations"],
            "message": message,
        },
    )
    return state


def _format_results_message(patterns: list[str], recommendations: list[str]) -> str:
    pattern_lines = [
        f"- {pattern}" for pattern in patterns
    ] or ["- No strong patterns were found from the available evidence."]
    recommendation_lines = [
        f"- {recommendation}" for recommendation in recommendations
    ] or ["- No specific recommendations were generated from the available evidence."]

    return "\n".join(
        [
            "Patterns",
            *pattern_lines,
            "",
            "Recommendations",
            *recommendation_lines,
        ]
    )


conversation_graph = StateGraph(UnifiedChatState)
conversation_graph.add_node("check_problem", check_problem_node)
conversation_graph.add_node("select_domains", select_domains_node)
conversation_graph.add_node("prepare_next_question", prepare_next_question_node)
conversation_graph.add_node("validate_answer", validate_answer_node)
conversation_graph.add_node("summarize_subdomain", summarize_subdomain_node)
conversation_graph.add_node("advance_after_summary", advance_after_summary_node)
conversation_graph.add_node("route_turn", lambda state: state)

conversation_graph.set_entry_point("route_turn")
conversation_graph.add_conditional_edges(
    "route_turn",
    _route_turn,
    {
        "check_problem": "check_problem",
        "validate_answer": "validate_answer",
        "prepare_next_question": "prepare_next_question",
        "done": END,
    },
)
conversation_graph.add_conditional_edges(
    "check_problem",
    route_after_problem_check,
    {
        "select_domains": "select_domains",
        "done": END,
    },
)
conversation_graph.add_edge("select_domains", "prepare_next_question")
conversation_graph.add_edge("prepare_next_question", END)
conversation_graph.add_conditional_edges(
    "validate_answer",
    route_after_validation,
    {
        "summarize_subdomain": "summarize_subdomain",
        "prepare_next_question": "prepare_next_question",
    },
)
conversation_graph.add_edge("summarize_subdomain", "advance_after_summary")
conversation_graph.add_conditional_edges(
    "advance_after_summary",
    route_after_advance,
    {
        "prepare_next_question": "prepare_next_question",
        "done": END,
    },
)

conversation_app = conversation_graph.compile()


results_graph = StateGraph(UnifiedChatState)
results_graph.add_node("query_expansion", query_expansion_node)
results_graph.add_node("retrieve_pattern_context", retrieve_pattern_context_node)
results_graph.add_node("pattern_recommendation", pattern_recommendation_node)

results_graph.set_entry_point("query_expansion")
results_graph.add_edge("query_expansion", "retrieve_pattern_context")
results_graph.add_edge("retrieve_pattern_context", "pattern_recommendation")
results_graph.add_edge("pattern_recommendation", END)

results_app = results_graph.compile()
