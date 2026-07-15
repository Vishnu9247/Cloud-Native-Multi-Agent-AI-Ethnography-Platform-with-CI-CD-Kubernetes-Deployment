from __future__ import annotations

from evals.ethno_evals.config import EvalConfig, bootstrap_backend
from evals.ethno_evals.metrics import score_result
from evals.ethno_evals.models import EvalResult, Persona
from evals.ethno_evals.report import write_workbook
from evals.ethno_evals.simulator import run_persona_session


def run_evaluations(personas: list[Persona], config: EvalConfig) -> list[EvalResult]:
    bootstrap_backend(config)

    results: list[EvalResult] = []
    for persona in personas:
        try:
            result = run_persona_session(persona, max_turns=config.max_turns)
            result = score_result(result)
        except Exception as error:
            result = EvalResult(persona=persona, error=f"{type(error).__name__}: {error}")
            result.failure_cases.append(result.error)
        results.append(result)

    write_workbook(results, config.output_path)
    return results
