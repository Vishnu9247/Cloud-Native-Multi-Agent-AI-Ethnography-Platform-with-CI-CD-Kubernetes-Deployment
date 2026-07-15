from __future__ import annotations

import argparse
from pathlib import Path

from evals.ethno_evals.config import EVALS_ROOT, EvalConfig, default_output_path
from evals.ethno_evals.personas import load_personas, select_personas
from evals.ethno_evals.runner import run_evaluations


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run persona evals for the Ethnography AI Interviewer agents."
    )
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        "--row",
        type=int,
        help="Excel row number to evaluate, including the header row offset.",
    )
    selection.add_argument(
        "--all",
        action="store_true",
        help="Evaluate every persona row in the workbook.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=EVALS_ROOT / "personas.xlsx",
        help="Path to personas.xlsx.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output_path(),
        help="Path for the generated results workbook.",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=80,
        help="Safety cap for simulated conversation turns per persona.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    personas = load_personas(args.input)
    selected = personas if args.all else select_personas(personas, args.row)

    config = EvalConfig(
        input_path=args.input,
        output_path=args.output,
        max_turns=args.max_turns,
    )
    results = run_evaluations(selected, config)

    print(f"Evaluated {len(results)} persona(s).")
    print(f"Results written to: {config.output_path}")
