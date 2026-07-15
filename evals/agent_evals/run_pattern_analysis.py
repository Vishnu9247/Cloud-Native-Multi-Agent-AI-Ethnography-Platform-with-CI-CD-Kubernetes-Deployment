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


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate pattern-analysis prompts.")
    add_common_arguments(parser)
    args = parser.parse_args()
    cases = load_dataset(args.dataset, args.case_id, args.case_limit)
    prompts = load_prompt_constants("pattern_analysis")
    run_logger = RunLogger(args.output_dir, "pattern_analysis", args.model)
    client = OllamaClient(args.model, args.host, args.timeout, call_logger=run_logger)
    client.check_model()
    rows = []

    for variant in variants(args.variant):
        for case in cases:
            oracle = case["pattern_analysis"]
            questions_generation = client.generate(
                prompt_for(prompts, "PATTERN_DISCOVERY_QUESTION_GENERATOR", variant).format(
                    problem=case["initial_problem"],
                    domains=json.dumps(case["domain_selection"]["required"], ensure_ascii=False),
                ),
                purpose="pattern_analysis.questions",
                metadata={"case_id": case["case_id"], "variant": variant, "task": "pattern_questions"},
            )
            questions_parsed = parse_json_value(questions_generation.text)
            questions = _string_list(questions_parsed)
            questions_valid = isinstance(questions_parsed, list) and len(questions) == len(questions_parsed)
            question_mark_rate = (
                sum(question.endswith("?") for question in questions) / len(questions)
                if questions else 0.0
            )
            cue_recall = phrase_recall(" ".join(questions), oracle["question_target_cues"])
            question_row = result_base(case, variant, "pattern_questions", questions_generation)
            question_row.update(
                {
                    "metric_format_valid": float(questions_valid),
                    "metric_question_mark_rate": question_mark_rate,
                    "metric_target_cue_recall": cue_recall,
                }
            )
            if args.no_judge:
                scores = None
            else:
                scores, judge_generation = judge(
                    client,
                    "Score problem_specificity, sequence_trigger_rhythm_coverage, exception_coverage, "
                    "open_endedness, atomicity, and non_redundancy.",
                    oracle,
                    questions,
                    {"case_id": case["case_id"], "variant": variant, "task": "pattern_questions"},
                )
                question_row["judge_scores"] = scores
                question_row["judge_prompt"] = judge_generation.prompt
                question_row["judge_response"] = judge_generation.text
                question_row["judge_elapsed_seconds"] = judge_generation.elapsed_seconds
                question_row.update(judge_metrics(scores))
            deterministic = 0.35 * question_mark_rate + 0.65 * cue_recall
            question_row["metric_overall_score"] = combined_score(float(questions_valid), deterministic, scores)
            rows.append(question_row)

            patterns_generation = client.generate(
                prompt_for(prompts, "IDENTIFY_SOLID_PATTERNS", variant).format(
                    problem=case["initial_problem"],
                    pattern_questions=json.dumps(questions, ensure_ascii=False, indent=2),
                    pattern_context=json.dumps(oracle["context"], ensure_ascii=False, indent=2),
                ),
                purpose="pattern_analysis.identify_patterns",
                metadata={"case_id": case["case_id"], "variant": variant, "task": "identify_patterns"},
            )
            patterns_parsed = parse_json_value(patterns_generation.text)
            patterns = _string_list(patterns_parsed)
            patterns_valid = isinstance(patterns_parsed, list) and len(patterns) == len(patterns_parsed)
            empty_accuracy = (
                float(not patterns) if oracle["expect_empty_patterns"] else float(bool(patterns))
            )
            pattern_cues = [cue for pattern in oracle["supported_patterns"] for cue in pattern["cues"]]
            pattern_recall = phrase_recall(" ".join(patterns), pattern_cues) if pattern_cues else empty_accuracy
            pattern_row = result_base(case, variant, "identify_patterns", patterns_generation)
            pattern_row.update(
                {
                    "metric_format_valid": float(patterns_valid),
                    "metric_empty_decision_accuracy": empty_accuracy,
                    "metric_pattern_cue_recall": pattern_recall,
                }
            )
            if args.no_judge:
                scores = None
            else:
                scores, judge_generation = judge(
                    client,
                    "Score evidence_precision, supported_pattern_recall, recurrence_support, mechanism_clarity, "
                    "problem_connection, and evidentiary_restraint. A single observation is not a pattern.",
                    oracle,
                    patterns,
                    {"case_id": case["case_id"], "variant": variant, "task": "identify_patterns"},
                )
                pattern_row["judge_scores"] = scores
                pattern_row["judge_prompt"] = judge_generation.prompt
                pattern_row["judge_response"] = judge_generation.text
                pattern_row["judge_elapsed_seconds"] = judge_generation.elapsed_seconds
                pattern_row.update(judge_metrics(scores))
            deterministic = 0.45 * empty_accuracy + 0.55 * pattern_recall
            pattern_row["metric_overall_score"] = combined_score(float(patterns_valid), deterministic, scores)
            rows.append(pattern_row)

            recommendations_generation = client.generate(
                prompt_for(prompts, "GENERATE_RECOMMENDATIONS", variant).format(
                    problem=case["initial_problem"],
                    patterns=json.dumps(patterns, ensure_ascii=False, indent=2),
                    pattern_context=json.dumps(oracle["context"], ensure_ascii=False, indent=2),
                ),
                purpose="pattern_analysis.recommendations",
                metadata={"case_id": case["case_id"], "variant": variant, "task": "recommendations"},
            )
            recommendations_parsed = parse_json_value(recommendations_generation.text)
            recommendations = _string_list(recommendations_parsed)
            recommendations_valid = (
                isinstance(recommendations_parsed, list)
                and len(recommendations) == len(recommendations_parsed)
            )
            recommendation_recall = phrase_recall(
                " ".join(recommendations), oracle["recommendation_cues"]
            )
            recommendation_row = result_base(case, variant, "recommendations", recommendations_generation)
            recommendation_row.update(
                {
                    "metric_format_valid": float(recommendations_valid),
                    "metric_recommendation_cue_recall": recommendation_recall,
                }
            )
            if args.no_judge:
                scores = None
            else:
                scores, judge_generation = judge(
                    client,
                    "Score pattern_traceability, personalization, actionability, feasibility, rationale_quality, "
                    "and constraint_sensitivity. Penalize generic, unsafe, or unsupported advice.",
                    oracle,
                    recommendations,
                    {"case_id": case["case_id"], "variant": variant, "task": "recommendations"},
                )
                recommendation_row["judge_scores"] = scores
                recommendation_row["judge_prompt"] = judge_generation.prompt
                recommendation_row["judge_response"] = judge_generation.text
                recommendation_row["judge_elapsed_seconds"] = judge_generation.elapsed_seconds
                recommendation_row.update(judge_metrics(scores))
            recommendation_row["metric_overall_score"] = combined_score(
                float(recommendations_valid), recommendation_recall, scores
            )
            rows.append(recommendation_row)

    write_results("pattern_analysis", args.output_dir, rows)


if __name__ == "__main__":
    main()
