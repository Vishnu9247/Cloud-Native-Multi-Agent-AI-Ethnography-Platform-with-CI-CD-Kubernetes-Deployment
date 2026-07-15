from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from evals.ethno_evals.metrics import deterministic_summary
from evals.ethno_evals.models import EvalResult


def write_workbook(results: list[EvalResult], output_path: Path) -> None:
    try:
        import pandas as pd
    except ImportError as error:
        raise RuntimeError(
            "pandas and openpyxl are required to write eval workbooks. Install "
            "backend/eval dependencies with `cd Backend; uv sync` or install "
            "evals/requirements.txt."
        ) from error

    output_path.parent.mkdir(parents=True, exist_ok=True)

    summary_rows = [_summary_row(result) for result in results]
    turn_rows = _turn_rows(results)
    retrieval_rows = _retrieval_rows(results)
    event_rows = _event_rows(results)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="summary", index=False)
        pd.DataFrame(turn_rows).to_excel(writer, sheet_name="turns", index=False)
        pd.DataFrame(retrieval_rows).to_excel(writer, sheet_name="retrieval", index=False)
        pd.DataFrame(event_rows).to_excel(writer, sheet_name="events", index=False)


def _summary_row(result: EvalResult) -> dict[str, Any]:
    row = deterministic_summary(result)
    judge = result.judge_scores
    row.update(
        {
            "problem": result.persona.problem,
            "expected_solution": result.persona.expected_solution,
            "problem_statement": result.problem_statement,
            "domains": json.dumps(result.domains, ensure_ascii=False),
            "patterns": _join_list(result.patterns),
            "recommendations": _join_list(result.recommendations),
            "answer_quality_causing_followups": judge.get(
                "answer_quality_causing_followups"
            ),
            "followup_relevance_necessity": judge.get("followup_relevance_necessity"),
            "domain_subdomain_accuracy": judge.get("domain_subdomain_accuracy"),
            "problem_summary_quality": judge.get("problem_summary_quality"),
            "recommendation_completeness_relevance": judge.get(
                "recommendation_completeness_relevance"
            ),
            "workflow_consistency": judge.get("workflow_consistency"),
            "hallucination_risk": judge.get("hallucination_risk"),
            "missing_outputs": _json_or_join(judge.get("missing_outputs")),
            "hallucinations_or_irrelevant_responses": _json_or_join(
                judge.get("hallucinations_or_irrelevant_responses")
            ),
            "failure_case_summary": judge.get("failure_case_summary"),
            "overall_summary": judge.get("overall_summary"),
            "error": result.error,
        }
    )
    return row


def _turn_rows(results: list[EvalResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results:
        for index, qa in enumerate(result.qa_history, start=1):
            rows.append(
                {
                    "persona_row": result.persona.row_number,
                    "name": result.persona.name,
                    "turn_index": index,
                    "domain": qa.get("domain", ""),
                    "subdomain": qa.get("subdomain", ""),
                    "question": qa.get("question", ""),
                    "answer": qa.get("answer", ""),
                    "validation_reason": qa.get("validation_reason", ""),
                    "carried_gap": qa.get("carried_gap", ""),
                    "caused_followup": bool(qa.get("carried_gap")),
                }
            )
    return rows


def _retrieval_rows(results: list[EvalResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results:
        for record in result.retrieval_records:
            rows.append(asdict(record))
    return rows


def _event_rows(results: list[EvalResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results:
        for index, event in enumerate(result.events, start=1):
            rows.append(
                {
                    "persona_row": result.persona.row_number,
                    "name": result.persona.name,
                    "event_index": index,
                    "event_type": event.get("type", ""),
                    "event": json.dumps(event, ensure_ascii=False),
                }
            )
    return rows


def _join_list(items: list[Any]) -> str:
    return "\n".join(str(item) for item in items)


def _json_or_join(value: Any) -> str:
    if isinstance(value, list):
        return " | ".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return "" if value is None else str(value)
