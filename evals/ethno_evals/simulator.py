from __future__ import annotations

from typing import Any

from evals.ethno_evals.models import EvalResult, Persona, RetrievalRecord


SIMULATED_USER_PROMPT = """
You are simulating a real participant in an ethnographic interview.

Persona name:
{name}

Problem:
{problem}

Person details:
{person_details}

Expected ethnographic solution, hidden from the interviewer:
{expected_solution}

Current interview stage: {stage}
Current domain: {domain}
Current subdomain: {subdomain}

Conversation so far:
{conversation}

Interviewer question:
{question}

Answer as the persona in first person.
Rules:
- Be natural and specific.
- Reveal only what a participant would plausibly say in response to this question.
- Do not mention that you are a simulation or that an expected solution exists.
- Include concrete details, tradeoffs, feelings, behaviors, or examples when relevant.
- Keep the answer to 2 to 5 sentences.
"""


def run_persona_session(persona: Persona, max_turns: int) -> EvalResult:
    from App.llm_utils.llm_client import invoke_llm
    from App.rag_utils.chroma_service import query_docs
    from App.unified_chat.workflow import create_session, generate_results, handle_user_message

    result = EvalResult(persona=persona)

    state = create_session(name=persona.name, age=35)
    all_events = list(state.get("events", []))
    turns = 0

    while state.get("stage") not in {"ready_for_results", "results"}:
        turns += 1
        if turns > max_turns:
            result.failure_cases.append(f"Exceeded max_turns={max_turns}.")
            break

        question = _latest_assistant_message(state)
        answer = _simulate_answer(invoke_llm, persona, state, question)
        state = handle_user_message(state, answer)
        all_events.extend(state.get("events", []))

    if state.get("stage") == "ready_for_results":
        state = generate_results(state)
        all_events.extend(state.get("events", []))

    result.session_id = state.get("session_id", "")
    result.final_stage = state.get("stage", "")
    result.problem_statement = state.get("problem_statement", "")
    result.domains = state.get("domains", [])
    result.subdomain_summaries = state.get("subdomain_summaries", {})
    result.patterns = state.get("patterns", [])
    result.recommendations = state.get("recommendations", [])
    result.qa_history = state.get("qa_history", [])
    result.events = all_events
    result.retrieved_context = state.get("retrieved_context", [])
    result.generated_answer = "\n".join(result.recommendations)
    result.retrieval_records = _collect_retrieval_records(query_docs, persona, state)
    result.failure_cases.extend(_detect_failures(result))
    return result


def _simulate_answer(invoke_llm, persona: Persona, state: dict[str, Any], question: str) -> str:
    prompt = SIMULATED_USER_PROMPT.format(
        name=persona.name,
        problem=persona.problem,
        person_details=persona.person_details,
        expected_solution=persona.expected_solution,
        stage=state.get("stage", ""),
        domain=state.get("current_domain", ""),
        subdomain=state.get("current_subdomain", ""),
        conversation=_format_conversation(state.get("conversation", [])),
        question=question,
    )
    return invoke_llm(prompt, purpose="evals.simulated_user")


def _latest_assistant_message(state: dict[str, Any]) -> str:
    for message in reversed(state.get("conversation", [])):
        if message.get("role") == "assistant":
            return str(message.get("content", "")).strip()
    return "What problem would you like to talk about today?"


def _format_conversation(messages: list[dict[str, str]], limit: int = 14) -> str:
    relevant = messages[-limit:]
    if not relevant:
        return "No prior messages."
    return "\n".join(
        f"{message.get('role', '').upper()}: {message.get('content', '')}"
        for message in relevant
    )


def _collect_retrieval_records(query_docs, persona: Persona, state: dict[str, Any]) -> list[RetrievalRecord]:
    records: list[RetrievalRecord] = []
    session_id = state.get("session_id", "")
    if not session_id:
        return records

    for query in state.get("pattern_queries", []):
        if not str(query).strip():
            continue
        try:
            raw = query_docs(session_id, query, n_results=5)
        except Exception:
            continue

        ids = raw.get("ids", [[]])[0]
        documents = raw.get("documents", [[]])[0]
        metadatas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]
        for index, document in enumerate(documents):
            distance = _float_or_none(distances[index] if index < len(distances) else None)
            metadata = metadatas[index] if index < len(metadatas) else {}
            records.append(
                RetrievalRecord(
                    persona_row=persona.row_number,
                    query=str(query),
                    rank=index + 1,
                    document_id=str(ids[index]) if index < len(ids) else "",
                    domain=str(metadata.get("domain", "")),
                    subdomain=str(metadata.get("subdomain", "")),
                    document_type=str(metadata.get("document_type", "")),
                    distance=distance,
                    confidence_score=_distance_to_confidence(distance),
                    document=str(document)[:1200],
                )
            )
    return records


def _float_or_none(value: object) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _distance_to_confidence(distance: float | None) -> float | None:
    if distance is None:
        return None
    return 1.0 / (1.0 + max(distance, 0.0))


def _detect_failures(result: EvalResult) -> list[str]:
    failures: list[str] = []
    if result.final_stage != "results":
        failures.append(f"Final stage was {result.final_stage!r}, expected 'results'.")
    if not result.problem_statement:
        failures.append("Missing problem statement.")
    if not result.domains:
        failures.append("Missing selected domains.")
    if not result.qa_history:
        failures.append("No interview Q/A turns were recorded.")
    if not result.subdomain_summaries:
        failures.append("Missing subdomain summaries.")
    if not result.recommendations:
        failures.append("Missing final recommendations.")
    return failures
