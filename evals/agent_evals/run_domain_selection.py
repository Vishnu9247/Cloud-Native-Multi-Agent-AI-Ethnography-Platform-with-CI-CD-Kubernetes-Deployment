from __future__ import annotations

import argparse

from evals.agent_evals.common import (
    OllamaClient,
    RunLogger,
    add_common_arguments,
    combined_score,
    flatten_domains,
    judge,
    judge_metrics,
    load_dataset,
    load_prompt_constants,
    parse_json_value,
    precision_recall_f1,
    prompt_for,
    result_base,
    variants,
    write_results,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate domain-selection prompts.")
    add_common_arguments(parser)
    args = parser.parse_args()
    cases = load_dataset(args.dataset, args.case_id, args.case_limit)
    prompts = load_prompt_constants("domain_selection")
    run_logger = RunLogger(args.output_dir, "domain_selection", args.model)
    client = OllamaClient(args.model, args.host, args.timeout, call_logger=run_logger)
    client.check_model()
    rows = []

    for variant in variants(args.variant):
        for case in cases:
            oracle = case["domain_selection"]
            generation = client.generate(
                prompt_for(prompts, "DOMAIN_SELECTION", variant).format(problem=case["initial_problem"]),
                purpose="domain_selection.select",
                metadata={"case_id": case["case_id"], "variant": variant, "task": "domain_selection"},
            )
            parsed = parse_json_value(generation.text)
            valid = isinstance(parsed, dict) and all(isinstance(value, list) for value in parsed.values())
            actual = flatten_domains(parsed) if valid else set()
            required = flatten_domains(oracle["required"])
            precision, recall, f1 = precision_recall_f1(actual, required)
            irrelevant = flatten_domains(oracle.get("irrelevant", {}))
            irrelevant_rate = len(actual & irrelevant) / len(actual) if actual else 0.0
            row = result_base(case, variant, "domain_selection", generation)
            row.update(
                {
                    "metric_format_valid": float(valid),
                    "metric_precision": precision,
                    "metric_recall": recall,
                    "metric_f1": f1,
                    "metric_focus": 1.0 - irrelevant_rate,
                }
            )
            if args.no_judge:
                scores = None
            else:
                scores, judge_generation = judge(
                    client,
                    "Score relevance, coverage, focus, and priority_order. Required entries are gold; "
                    "acceptable_optional entries may receive credit and must not be treated as errors.",
                    oracle,
                    parsed if valid else generation.text,
                    {"case_id": case["case_id"], "variant": variant, "task": "domain_selection"},
                )
                row["judge_scores"] = scores
                row["judge_prompt"] = judge_generation.prompt
                row["judge_response"] = judge_generation.text
                row["judge_elapsed_seconds"] = judge_generation.elapsed_seconds
                row.update(judge_metrics(scores))
            deterministic = 0.35 * precision + 0.35 * recall + 0.20 * f1 + 0.10 * (1.0 - irrelevant_rate)
            row["metric_overall_score"] = combined_score(float(valid), deterministic, scores)
            rows.append(row)

    write_results("domain_selection", args.output_dir, rows)


if __name__ == "__main__":
    main()
