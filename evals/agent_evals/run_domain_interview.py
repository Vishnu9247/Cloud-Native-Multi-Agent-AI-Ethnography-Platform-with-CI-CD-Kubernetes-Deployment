from __future__ import annotations

import argparse
import json

from evals.agent_evals.common import (
    OllamaClient,
    RunLogger,
    add_common_arguments,
    combined_score,
    judge,
    judge_metrics,
    load_dataset,
    load_prompt_constants,
    parse_json_value,
    phrase_recall,
    prompt_for,
    result_base,
    variants,
    write_results,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate domain-interview prompts.")
    add_common_arguments(parser)
    args = parser.parse_args()
    cases = load_dataset(args.dataset, args.case_id, args.case_limit)
    prompts = load_prompt_constants("domain_interview")
    run_logger = RunLogger(args.output_dir, "domain_interview", args.model)
    client = OllamaClient(args.model, args.host, args.timeout, call_logger=run_logger)
    client.check_model()
    rows = []

    for variant in variants(args.variant):
        for case in cases:
            oracle = case["domain_interview"]
            generation = client.generate(
                prompt_for(prompts, "DOMAIN_EXPLORER", variant).format(
                    problem=case["initial_problem"],
                    domain=oracle["domain"],
                    subdomain=oracle["subdomain"],
                ),
                purpose="domain_interview.questions",
                metadata={"case_id": case["case_id"], "variant": variant, "task": "question_generation"},
            )
            parsed = parse_json_value(generation.text)
            questions = parsed.get("questions", []) if isinstance(parsed, dict) else []
            valid = (
                isinstance(parsed, dict)
                and parsed.get("domain") == oracle["domain"]
                and parsed.get("subdomain") == oracle["subdomain"]
                and isinstance(questions, list)
                and all(isinstance(question, str) for question in questions)
            )
            question_count_valid = 5 <= len(questions) <= 8
            question_mark_rate = (
                sum(question.strip().endswith("?") for question in questions) / len(questions)
                if questions else 0.0
            )
            combined = " ".join(questions)
            target_recall = phrase_recall(combined, oracle["target_cues"])
            row = result_base(case, variant, "question_generation", generation)
            row.update(
                {
                    "metric_format_valid": float(valid),
                    "metric_question_count_valid": float(question_count_valid),
                    "metric_question_mark_rate": question_mark_rate,
                    "metric_target_cue_recall": target_recall,
                }
            )
            if args.no_judge:
                scores = None
            else:
                scores, judge_generation = judge(
                    client,
                    "Score subdomain_relevance, target_coverage, open_endedness, atomicity, "
                    "conversational_tone, specificity, and non_redundancy. Penalize advice and compound questions.",
                    oracle,
                    questions,
                    {"case_id": case["case_id"], "variant": variant, "task": "question_generation"},
                )
                row["judge_scores"] = scores
                row["judge_prompt"] = judge_generation.prompt
                row["judge_response"] = judge_generation.text
                row["judge_elapsed_seconds"] = judge_generation.elapsed_seconds
                row.update(judge_metrics(scores))
            deterministic = 0.30 * float(question_count_valid) + 0.25 * question_mark_rate + 0.45 * target_recall
            row["metric_overall_score"] = combined_score(
                float(valid), deterministic, scores
            )
            rows.append(row)

            for rephrase_case in oracle["rephrase_cases"]:
                rephrase_generation = client.generate(
                    prompt_for(prompts, "QUERY_AND_REPHRASE", variant).format(
                        domain=oracle["domain"],
                        subdomain=oracle["subdomain"],
                        question=rephrase_case["original_question"],
                        context=rephrase_case["context"],
                    ),
                    purpose="domain_interview.rephrase",
                    metadata={"case_id": case["case_id"], "variant": variant, "task": "rephrase"},
                )
                one_question = (
                    rephrase_generation.text.count("?") == 1
                    and "\n" not in rephrase_generation.text.strip()
                )
                if rephrase_case["expected_move"] == "KEEP":
                    move_proxy = float(
                        rephrase_generation.text.strip().lower()
                        == rephrase_case["original_question"].strip().lower()
                    )
                else:
                    move_proxy = phrase_recall(
                        rephrase_generation.text,
                        rephrase_case["expected_cues"],
                    )
                rephrase_row = result_base(case, variant, "rephrase", rephrase_generation)
                rephrase_row.update(
                    {
                        "expected_move": rephrase_case["expected_move"],
                        "metric_format_valid": float(one_question),
                        "metric_move_proxy_score": move_proxy,
                    }
                )
                if args.no_judge:
                    scores = None
                else:
                    scores, judge_generation = judge(
                        client,
                        "Score move_accuracy (KEEP, DEEPEN, or SHARPEN), contextual_continuity, "
                        "novelty_without_repetition, open_endedness, and atomicity.",
                        rephrase_case,
                        rephrase_generation.text,
                        {"case_id": case["case_id"], "variant": variant, "task": "rephrase"},
                    )
                    rephrase_row["judge_scores"] = scores
                    rephrase_row["judge_prompt"] = judge_generation.prompt
                    rephrase_row["judge_response"] = judge_generation.text
                    rephrase_row["judge_elapsed_seconds"] = judge_generation.elapsed_seconds
                    rephrase_row.update(judge_metrics(scores))
                rephrase_row["metric_overall_score"] = combined_score(float(one_question), move_proxy, scores)
                rows.append(rephrase_row)

    write_results("domain_interview", args.output_dir, rows)


if __name__ == "__main__":
    main()
