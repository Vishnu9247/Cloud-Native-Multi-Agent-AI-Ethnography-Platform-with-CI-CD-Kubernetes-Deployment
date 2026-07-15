from __future__ import annotations

import argparse

from evals.agent_evals.common import (
    OllamaClient,
    RunLogger,
    add_common_arguments,
    combined_score,
    conversation_text,
    judge,
    judge_metrics,
    load_dataset,
    load_prompt_constants,
    phrase_recall,
    prompt_for,
    result_base,
    variants,
    write_results,
)


def _status(text: str) -> str:
    return "complete" if text.lower().strip(" .!\n") == "complete" else "incomplete"


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate interview-validation prompts.")
    add_common_arguments(parser)
    args = parser.parse_args()
    cases = load_dataset(args.dataset, args.case_id, args.case_limit)
    prompts = load_prompt_constants("interview_validation")
    run_logger = RunLogger(args.output_dir, "interview_validation", args.model)
    client = OllamaClient(args.model, args.host, args.timeout, call_logger=run_logger)
    client.check_model()
    rows = []

    for variant in variants(args.variant):
        for case in cases:
            oracle = case["interview_validation"]
            for validation_case in oracle["validation_cases"]:
                generation = client.generate(
                    prompt_for(prompts, "IDENTIFY_GAPS", variant).format(
                        problem=case["initial_problem"],
                        domain=oracle["domain"],
                        subdomain=oracle["subdomain"],
                        conversation_text=conversation_text(validation_case["conversation"]),
                    ),
                    purpose="interview_validation.answer_sufficiency",
                    metadata={"case_id": case["case_id"], "variant": variant, "task": "answer_sufficiency"},
                )
                predicted = _status(generation.text)
                accuracy = float(predicted == validation_case["gold_status"])
                format_valid = predicted == "complete" or (
                    generation.text.count("?") == 1 and "\n" not in generation.text.strip()
                )
                row = result_base(case, variant, "answer_sufficiency", generation)
                row.update(
                    {
                        "gold_status": validation_case["gold_status"],
                        "predicted_status": predicted,
                        "metric_format_valid": float(format_valid),
                        "metric_classification_accuracy": accuracy,
                    }
                )
                if args.no_judge:
                    scores = None
                else:
                    scores, judge_generation = judge(
                        client,
                        "First score decision_correctness against gold_status. If the output is a follow-up, also "
                        "score followup_necessity, relevance, simplicity, non_redundancy, and subdomain_focus. "
                        "If complete is correct, do not penalize absence of a follow-up.",
                        validation_case,
                        generation.text,
                        {"case_id": case["case_id"], "variant": variant, "task": "answer_sufficiency"},
                    )
                    row["judge_scores"] = scores
                    row["judge_prompt"] = judge_generation.prompt
                    row["judge_response"] = judge_generation.text
                    row["judge_elapsed_seconds"] = judge_generation.elapsed_seconds
                    row.update(judge_metrics(scores))
                row["metric_overall_score"] = combined_score(float(format_valid), accuracy, scores)
                rows.append(row)

            summary_generation = client.generate(
                prompt_for(prompts, "SUMMARY_PROMPT", variant).format(
                    problem=case["initial_problem"],
                    domain=oracle["domain"],
                    subdomain=oracle["subdomain"],
                    conversation_text=conversation_text(oracle["summary_conversation"]),
                ),
                purpose="interview_validation.summary",
                metadata={"case_id": case["case_id"], "variant": variant, "task": "subdomain_summary"},
            )
            recall = phrase_recall(summary_generation.text, oracle["summary_key_phrases"])
            mechanics_leak = any(
                phrase in summary_generation.text.lower()
                for phrase in ("assistant asked", "user answered", "when questioned", "interviewer")
            )
            summary_row = result_base(case, variant, "subdomain_summary", summary_generation)
            summary_row.update(
                {
                    "metric_format_valid": float(not mechanics_leak),
                    "metric_key_phrase_recall": recall,
                    "metric_no_interview_mechanics_leak": float(not mechanics_leak),
                }
            )
            if args.no_judge:
                scores = None
            else:
                scores, judge_generation = judge(
                    client,
                    "Score factual_faithfulness, coverage, narrative_quality, uncertainty_preservation, "
                    "and no_hallucination. Penalize any narration of interview mechanics.",
                    oracle,
                    summary_generation.text,
                    {"case_id": case["case_id"], "variant": variant, "task": "subdomain_summary"},
                )
                summary_row["judge_scores"] = scores
                summary_row["judge_prompt"] = judge_generation.prompt
                summary_row["judge_response"] = judge_generation.text
                summary_row["judge_elapsed_seconds"] = judge_generation.elapsed_seconds
                summary_row.update(judge_metrics(scores))
            deterministic = recall * (0.0 if mechanics_leak else 1.0)
            summary_row["metric_overall_score"] = combined_score(float(not mechanics_leak), deterministic, scores)
            rows.append(summary_row)

    write_results("interview_validation", args.output_dir, rows)


if __name__ == "__main__":
    main()
