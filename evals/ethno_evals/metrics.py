from __future__ import annotations

import json
import re
from statistics import mean
from typing import Any

from evals.ethno_evals.models import EvalResult


JUDGE_PROMPT = """
You are evaluating an ethnographic AI interviewer workflow.

Persona:
Name: {name}
Problem: {problem}
Person details: {person_details}
Expected ethnographic solution: {expected_solution}

Generated problem statement:
{problem_statement}

Selected domains and subdomains:
{domains}

Interview question/answer history:
{qa_history}

Subdomain summaries:
{subdomain_summaries}

Generated patterns:
{patterns}

Generated recommendations:
{recommendations}

Known deterministic failures:
{failure_cases}

Score each dimension from 0.0 to 1.0.
Return only valid JSON with this schema:
{{
  "answer_quality_causing_followups": 0.0,
  "followup_relevance_necessity": 0.0,
  "domain_subdomain_accuracy": 0.0,
  "problem_summary_quality": 0.0,
  "recommendation_completeness_relevance": 0.0,
  "workflow_consistency": 0.0,
  "hallucination_risk": 0.0,
  "failure_case_summary": "Short summary.",
  "missing_outputs": ["missing item"],
  "hallucinations_or_irrelevant_responses": ["issue"],
  "overall_summary": "Short evaluator summary."
}}
"""


SEMANTIC_SIMILARITY_PROMPT = """
Compare the expected ethnographic solution with the generated recommendations.

Expected solution:
{expected}

Generated recommendations:
{actual}

Return only valid JSON:
{{
  "semantic_similarity_score": 0.0,
  "reason": "Short reason."
}}

Score from 0.0 to 1.0, where 1.0 means the generated recommendations capture
the same intent, behavioral insight, and practical direction as the expected
solution, even if wording differs.
"""


def score_result(result: EvalResult) -> EvalResult:
    result.semantic_similarity_score, result.similarity_method = semantic_similarity(
        result.persona.expected_solution,
        result.generated_answer,
    )
    result.judge_scores = judge_result(result)
    return result


def semantic_similarity(expected: str, actual: str) -> tuple[float | None, str]:
    expected = expected.strip()
    actual = actual.strip()
    if not expected or not actual:
        return None, "not_available"

    score = _llm_similarity(expected, actual)
    if score is not None:
        return score, "llama3.2_judge"

    score = _sentence_transformer_similarity(expected, actual)
    if score is not None:
        return score, "sentence_transformers"

    score = _tfidf_similarity(expected, actual)
    if score is not None:
        return score, "tfidf_cosine"

    return None, "not_available"


def judge_result(result: EvalResult) -> dict[str, Any]:
    from App.llm_utils.llm_client import invoke_llm

    prompt = JUDGE_PROMPT.format(
        name=result.persona.name,
        problem=result.persona.problem,
        person_details=result.persona.person_details,
        expected_solution=result.persona.expected_solution,
        problem_statement=result.problem_statement,
        domains=json.dumps(result.domains, ensure_ascii=False, indent=2),
        qa_history=json.dumps(result.qa_history, ensure_ascii=False, indent=2),
        subdomain_summaries=json.dumps(
            result.subdomain_summaries,
            ensure_ascii=False,
            indent=2,
        ),
        patterns=json.dumps(result.patterns, ensure_ascii=False, indent=2),
        recommendations=json.dumps(result.recommendations, ensure_ascii=False, indent=2),
        failure_cases=json.dumps(result.failure_cases, ensure_ascii=False, indent=2),
    )
    response = invoke_llm(prompt, purpose="evals.judge")
    return _parse_json_object(response)


def deterministic_summary(result: EvalResult) -> dict[str, Any]:
    retrieval_scores = [
        record.confidence_score
        for record in result.retrieval_records
        if record.confidence_score is not None
    ]
    completed_subdomains = [
        event for event in result.events if event.get("type") == "subdomain_completed"
    ]
    problem_followups = [
        event for event in result.events if event.get("type") == "problem_followup"
    ]
    interview_questions = [
        qa for qa in result.qa_history if str(qa.get("question", "")).strip()
    ]

    return {
        "persona_row": result.persona.row_number,
        "name": result.persona.name,
        "session_id": result.session_id,
        "final_stage": result.final_stage,
        "problem_followup_count": len(problem_followups),
        "interview_followup_count": len(interview_questions),
        "total_agent_questions": len(problem_followups) + len(interview_questions),
        "selected_domain_count": len(result.domains),
        "selected_subdomain_count": sum(
            len(domain.get("subdomains", [])) for domain in result.domains
        ),
        "completed_subdomain_count": len(completed_subdomains),
        "retrieved_context_count": len(result.retrieval_records),
        "avg_retrieval_confidence": mean(retrieval_scores) if retrieval_scores else None,
        "min_retrieval_confidence": min(retrieval_scores) if retrieval_scores else None,
        "semantic_similarity_score": result.semantic_similarity_score,
        "similarity_method": result.similarity_method,
        "failure_count": len(result.failure_cases),
        "failure_cases": " | ".join(result.failure_cases),
    }


def _sentence_transformer_similarity(expected: str, actual: str) -> float | None:
    import os

    if os.getenv("EVAL_USE_SENTENCE_TRANSFORMERS", "").lower() not in {"1", "true", "yes"}:
        return None

    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        return None

    try:
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        embeddings = model.encode([expected, actual], normalize_embeddings=True)
        return float(embeddings[0] @ embeddings[1])
    except Exception:
        return None


def _llm_similarity(expected: str, actual: str) -> float | None:
    try:
        from App.llm_utils.llm_client import invoke_llm

        response = invoke_llm(
            SEMANTIC_SIMILARITY_PROMPT.format(expected=expected, actual=actual),
            purpose="evals.semantic_similarity",
        )
        parsed = _parse_json_object(response)
        score = parsed.get("semantic_similarity_score")
        if score is None:
            match = re.search(r"0(?:\.\d+)?|1(?:\.0+)?", response)
            score = match.group(0) if match else None
        if score is None:
            return None
        return max(0.0, min(1.0, float(score)))
    except Exception:
        return None


def _tfidf_similarity(expected: str, actual: str) -> float | None:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        matrix = TfidfVectorizer(ngram_range=(1, 2), stop_words="english").fit_transform(
            [expected, actual]
        )
        return float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])
    except Exception:
        return None


def _parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.removeprefix("```json").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").strip()
    if cleaned.endswith("```"):
        cleaned = cleaned.removesuffix("```").strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        cleaned = cleaned[start : end + 1]

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "answer_quality_causing_followups": None,
            "followup_relevance_necessity": None,
            "domain_subdomain_accuracy": None,
            "problem_summary_quality": None,
            "recommendation_completeness_relevance": None,
            "workflow_consistency": None,
            "hallucination_risk": None,
            "failure_case_summary": "Judge response could not be parsed.",
            "missing_outputs": [],
            "hallucinations_or_irrelevant_responses": [],
            "overall_summary": text[:1000],
        }
    return parsed if isinstance(parsed, dict) else {}
