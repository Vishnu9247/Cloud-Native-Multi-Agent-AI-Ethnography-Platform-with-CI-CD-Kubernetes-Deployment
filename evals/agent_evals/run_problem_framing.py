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


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate problem-framing prompts.")
    add_common_arguments(parser)
    args = parser.parse_args()
    cases = load_dataset(args.dataset, args.case_id, args.case_limit)
    prompts = load_prompt_constants("problem_framing")
    run_logger = RunLogger(args.output_dir, "problem_framing", args.model)
    client = OllamaClient(args.model, args.host, args.timeout, call_logger=run_logger)
    client.check_model()
    rows = []

    for variant in variants(args.variant):
        for case in cases:
            oracle = case["problem_framing"]
            initial = [{"role": "user", "content": case["initial_problem"]}]
            generation = client.generate(
                prompt_for(prompts, "CHECK_COMPLETENESS", variant).format(
                    name=case["persona"]["name"],
                    age=case["persona"]["age"],
                    conversation_text=conversation_text(initial),
                ),
                purpose="problem_framing.completeness",
                metadata={"case_id": case["case_id"], "variant": variant, "task": "completeness"},
            )
            predicted_complete = generation.text.lower().strip(" .!\n") == "complete"
            expected_complete = bool(oracle["initial_complete"])
            exact_contract = predicted_complete or (
                not predicted_complete
                and generation.text.count("?") == 1
                and "\n" not in generation.text.strip()
            )
            row = result_base(case, variant, "completeness", generation)
            row.update(
                {
                    "metric_format_valid": float(exact_contract),
                    "metric_classification_accuracy": float(predicted_complete == expected_complete),
                }
            )
            if not args.no_judge:
                scores, judge_generation = judge(
                    client,
                    "First score decision_correctness against initial_complete. If the output is a follow-up, "
                    "also score followup_relevance, warmth, atomicity, and non_redundancy; it must target only "
                    "the documented missing dimension. If Complete is correct, do not penalize absence of a follow-up.",
                    oracle,
                    generation.text,
                    {"case_id": case["case_id"], "variant": variant, "task": "completeness"},
                )
                row["judge_scores"] = scores
                row["judge_prompt"] = judge_generation.prompt
                row["judge_response"] = judge_generation.text
                row["judge_elapsed_seconds"] = judge_generation.elapsed_seconds
                row.update(judge_metrics(scores))
            else:
                scores = None
            row["metric_overall_score"] = combined_score(
                row["metric_format_valid"], row["metric_classification_accuracy"], scores
            )
            rows.append(row)

            full_conversation = list(initial)
            if not expected_complete:
                full_conversation.extend(
                    [
                        {"role": "assistant", "content": oracle["acceptable_followup"]},
                        {"role": "user", "content": oracle["clarification_answer"]},
                    ]
                )
            summary_generation = client.generate(
                prompt_for(prompts, "SUMMARIZE_PROBLEM", variant).format(
                    name=case["persona"]["name"],
                    age=case["persona"]["age"],
                    conversation_text=conversation_text(full_conversation),
                ),
                purpose="problem_framing.summary",
                metadata={"case_id": case["case_id"], "variant": variant, "task": "summary"},
            )
            format_valid = all(
                label in summary_generation.text
                for label in ("Problem Summary:", "Key Objectives:", "Primary Pain Points:", "Important Context:")
            )
            recall = phrase_recall(summary_generation.text, oracle["summary_key_phrases"])
            summary_row = result_base(case, variant, "summary", summary_generation)
            summary_row.update({"metric_format_valid": float(format_valid), "metric_key_phrase_recall": recall})
            if args.no_judge:
                scores = None
            else:
                scores, judge_generation = judge(
                    client,
                    "Score faithfulness, coverage, emotional_fidelity, concision, and no_hallucination. "
                    "Penalize any forbidden inference.",
                    oracle,
                    summary_generation.text,
                    {"case_id": case["case_id"], "variant": variant, "task": "summary"},
                )
                summary_row["judge_scores"] = scores
                summary_row["judge_prompt"] = judge_generation.prompt
                summary_row["judge_response"] = judge_generation.text
                summary_row["judge_elapsed_seconds"] = judge_generation.elapsed_seconds
                summary_row.update(judge_metrics(scores))
            summary_row["metric_overall_score"] = combined_score(float(format_valid), recall, scores)
            rows.append(summary_row)

    write_results("problem_framing", args.output_dir, rows)


if __name__ == "__main__":
    main()
