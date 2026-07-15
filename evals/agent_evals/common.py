from __future__ import annotations

import argparse
import ast
import csv
import json
import math
import re
import statistics
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = Path(__file__).parent / "dataset" / "agent_eval_dataset_40.json"
DEFAULT_RESULTS = Path(__file__).parent / "results"
PROMPT_DIR = PROJECT_ROOT / "Backend" / "App" / "prompt_utils" / "Test_Promps"

PROMPT_FILES = {
    "problem_framing": PROMPT_DIR / "problem_framing_prompts_variants.py",
    "domain_selection": PROMPT_DIR / "domain_selection_prompts_variants.py",
    "domain_interview": PROMPT_DIR / "domain_interview_prompts_variants.py",
    "interview_validation": PROMPT_DIR / "interview_validation_prompts_variants.py",
    "pattern_analysis": PROMPT_DIR / "pattern_analysis_prompts_variants.py",
}


@dataclass
class Generation:
    prompt: str
    text: str
    elapsed_seconds: float
    prompt_tokens: int | None
    output_tokens: int | None


class RunLogger:
    """Write lossless machine-readable and human-readable LLM call logs."""

    def __init__(self, output_dir: Path, agent: str, model: str) -> None:
        self.run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
        self.agent = agent
        self.model = model
        self.log_dir = output_dir / agent / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.jsonl_path = self.log_dir / "calls.jsonl"
        self.text_path = self.log_dir / "run.log"
        self.jsonl_path.write_text("", encoding="utf-8")
        self.text_path.write_text("", encoding="utf-8")

    def write_call(self, record: dict[str, Any]) -> None:
        payload = {
            "run_id": self.run_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "agent": self.agent,
            "model": self.model,
            **record,
        }
        with self.jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        with self.text_path.open("a", encoding="utf-8") as handle:
            handle.write(
                "=" * 88
                + "\n"
                + f"CALL: {payload.get('call_type')} | CASE: {payload.get('case_id')} | "
                + f"VARIANT: {payload.get('variant')} | TASK: {payload.get('task')}\n"
                + f"PURPOSE: {payload.get('purpose')}\n"
                + "-" * 88
                + "\nPROMPT\n"
                + str(payload.get("prompt", ""))
                + "\n"
                + "-" * 88
                + "\nRESPONSE\n"
                + str(payload.get("response", ""))
                + "\n"
                + f"ELAPSED_SECONDS: {payload.get('elapsed_seconds')} | "
                + f"PROMPT_TOKENS: {payload.get('prompt_tokens')} | "
                + f"OUTPUT_TOKENS: {payload.get('output_tokens')}\n"
            )


class OllamaClient:
    def __init__(
        self,
        model: str = "llama3.2",
        host: str = "http://127.0.0.1:11434",
        timeout: float = 180.0,
        seed: int = 42,
        call_logger: RunLogger | None = None,
    ) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.seed = seed
        self.call_logger = call_logger

    def check_model(self) -> None:
        try:
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=5) as response:
                payload = json.load(response)
        except (OSError, urllib.error.URLError) as error:
            raise RuntimeError(
                f"Cannot reach Ollama at {self.host}. Start it with `ollama serve`."
            ) from error

        available = {
            str(item.get("name", "")).split(":", 1)[0]
            for item in payload.get("models", [])
        }
        requested = self.model.split(":", 1)[0]
        if requested not in available:
            raise RuntimeError(
                f"Ollama model {self.model!r} is unavailable. Run `ollama pull {self.model}`."
            )

    def generate(
        self,
        prompt: str,
        *,
        call_type: str = "agent",
        purpose: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Generation:
        body = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0, "seed": self.seed},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.host}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama returned HTTP {error.code}: {detail}") from error
        except (OSError, urllib.error.URLError) as error:
            raise RuntimeError(f"Ollama request failed: {error}") from error

        generation = Generation(
            prompt=prompt,
            text=str(payload.get("response", "")).strip(),
            elapsed_seconds=time.perf_counter() - started,
            prompt_tokens=_int_or_none(payload.get("prompt_eval_count")),
            output_tokens=_int_or_none(payload.get("eval_count")),
        )
        if self.call_logger is not None:
            self.call_logger.write_call(
                {
                    **(metadata or {}),
                    "call_type": call_type,
                    "purpose": purpose,
                    "prompt": generation.prompt,
                    "response": generation.text,
                    "elapsed_seconds": round(generation.elapsed_seconds, 6),
                    "prompt_tokens": generation.prompt_tokens,
                    "output_tokens": generation.output_tokens,
                }
            )
        return generation


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--variant", choices=("a", "b", "c", "all"), default="all")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--model", default="llama3.2")
    parser.add_argument("--host", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--case-limit", type=int)
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument(
        "--no-judge",
        action="store_true",
        help="Skip semantic LLM judging and run deterministic checks only.",
    )


def variants(value: str) -> list[str]:
    return ["a", "b", "c"] if value == "all" else [value]


def load_dataset(path: Path, case_ids: list[str], case_limit: int | None) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Dataset root must be a JSON array.")
    if case_ids:
        wanted = set(case_ids)
        data = [case for case in data if case.get("case_id") in wanted]
    if case_limit is not None:
        data = data[: max(0, case_limit)]
    if not data:
        raise ValueError("No dataset cases selected.")
    return data


def load_prompt_constants(agent: str) -> dict[str, str]:
    path = PROMPT_FILES[agent]
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    constants: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str):
                constants[target.id] = node.value.value
    return constants


def prompt_for(constants: dict[str, str], base: str, variant: str) -> str:
    suffixes = {"a": "A_TIGHT", "b": "B_FEWSHOT", "c": "C_CHECKLIST"}
    name = f"{base}_{suffixes[variant]}"
    try:
        return constants[name]
    except KeyError as error:
        raise KeyError(f"Prompt constant {name} was not found.") from error


def conversation_text(messages: list[dict[str, str]]) -> str:
    return "\n\n".join(
        f"{message['role'].upper()}: {message['content']}" for message in messages
    )


def parse_json_value(text: str) -> Any:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    for opener, closer in (("{", "}"), ("[", "]")):
        start = cleaned.find(opener)
        end = cleaned.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                pass
    return None


def judge(
    client: OllamaClient,
    rubric: str,
    gold: Any,
    output: Any,
    metadata: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], Generation]:
    prompt = f"""
You are a strict, evidence-focused evaluator. Evaluate an output from an
ethnographic AI workflow. Treat the reference data as the only source of truth.
Do not reward extra detail when it is unsupported.

RUBRIC:
{rubric}

REFERENCE DATA:
{json.dumps(gold, ensure_ascii=False, indent=2)}

MODEL OUTPUT:
{json.dumps(output, ensure_ascii=False, indent=2) if not isinstance(output, str) else output}

Return ONLY a valid JSON object using this exact schema. Every score must be a
number between 0.0 and 1.0 inclusive:
{{
  "groundedness": 0.0,
  "relevance": 0.0,
  "completeness": 0.0,
  "faithfulness": 0.0,
  "coherence": 0.0,
  "instruction_compliance": 0.0,
  "safety": 0.0,
  "overall": 0.0,
  "confidence": 0.0,
  "unsupported_claims": ["claim"],
  "missing_items": ["item"],
  "reason": "Concise evidence-based explanation."
}}
Groundedness measures whether every material claim is supported by the reference.
Confidence measures confidence in this evaluation, not confidence in the model output.
Do not use markdown.
""".strip()
    generation = client.generate(
        prompt,
        call_type="judge",
        purpose="llm_judge",
        metadata=metadata,
    )
    parsed = parse_json_value(generation.text)
    if not isinstance(parsed, dict):
        parsed = {"overall": 0.0, "reason": "Judge output was not valid JSON."}
    for key in (
        "groundedness",
        "relevance",
        "completeness",
        "faithfulness",
        "coherence",
        "instruction_compliance",
        "safety",
        "overall",
        "confidence",
    ):
        parsed[key] = clamp_score(parsed.get(key))
    return parsed, generation


def clamp_score(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def judge_metrics(scores: dict[str, Any]) -> dict[str, float]:
    """Flatten the common judge schema into normalized result columns."""
    mapping = {
        "groundedness": "groundedness",
        "relevance": "relevance",
        "completeness": "completeness",
        "faithfulness": "faithfulness",
        "coherence": "coherence",
        "instruction_compliance": "instruction_compliance",
        "safety": "safety",
        "confidence": "confidence",
        "judge_overall": "overall",
    }
    return {
        f"metric_{column}": clamp_score(scores.get(source))
        for column, source in mapping.items()
    }


def combined_score(
    format_valid: float,
    deterministic_score: float,
    judge_scores: dict[str, Any] | None,
) -> float:
    """Combine normalized deterministic and judge metrics into a 0-1 score."""
    format_valid = clamp_score(format_valid)
    deterministic_score = clamp_score(deterministic_score)
    if not judge_scores:
        return round(0.35 * format_valid + 0.65 * deterministic_score, 4)
    return round(
        0.15 * format_valid
        + 0.15 * deterministic_score
        + 0.40 * clamp_score(judge_scores.get("overall"))
        + 0.20 * clamp_score(judge_scores.get("groundedness"))
        + 0.10 * clamp_score(judge_scores.get("confidence")),
        4,
    )


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def phrase_recall(text: str, phrases: Iterable[str]) -> float:
    phrases = list(phrases)
    if not phrases:
        return 1.0
    normalized = norm(text)
    hits = sum(1 for phrase in phrases if norm(str(phrase)) in normalized)
    return hits / len(phrases)


def flatten_domains(domains: dict[str, list[str]]) -> set[tuple[str, str]]:
    return {
        (norm(str(domain)), norm(str(subdomain)))
        for domain, subdomains in domains.items()
        if isinstance(subdomains, list)
        for subdomain in subdomains
    }


def precision_recall_f1(actual: set[Any], expected: set[Any]) -> tuple[float, float, float]:
    intersection = len(actual & expected)
    precision = intersection / len(actual) if actual else (1.0 if not expected else 0.0)
    recall = intersection / len(expected) if expected else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def mean(values: Iterable[Any]) -> float:
    numeric = [float(value) for value in values if isinstance(value, (int, float)) and math.isfinite(value)]
    return statistics.fmean(numeric) if numeric else 0.0


def result_base(case: dict[str, Any], variant: str, task: str, generation: Generation) -> dict[str, Any]:
    return {
        "case_id": case["case_id"],
        "split": case["split"],
        "difficulty": case["difficulty"],
        "variant": variant,
        "task": task,
        "elapsed_seconds": round(generation.elapsed_seconds, 4),
        "prompt_tokens": generation.prompt_tokens,
        "output_tokens": generation.output_tokens,
        "agent_prompt": generation.prompt,
        "agent_response": generation.text,
    }


def write_results(agent: str, output_dir: Path, rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    agent_dir = output_dir / agent
    agent_dir.mkdir(parents=True, exist_ok=True)
    csv_path = agent_dir / "details.csv"
    json_path = agent_dir / "summary.json"

    flattened = [_csv_row(row) for row in rows]
    fieldnames = sorted({key for row in flattened for key in row})
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flattened)

    summary: dict[str, Any] = {
        "agent": agent,
        "rows": len(rows),
        "metric_range": [0.0, 1.0],
        "variants": {},
    }
    for variant in sorted({str(row.get("variant")) for row in rows}):
        selected = [row for row in rows if row.get("variant") == variant]
        metric_keys = sorted(
            key for key in {key for row in selected for key in row} if key.startswith("metric_")
        )
        summary["variants"][variant] = {
            "row_count": len(selected),
            "metrics": {
                key: round(mean(row.get(key) for row in selected), 4) for key in metric_keys
            },
            "mean_elapsed_seconds": round(mean(row.get("elapsed_seconds") for row in selected), 4),
            "mean_output_tokens": round(mean(row.get("output_tokens") for row in selected), 2),
        }
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Details: {csv_path}")
    print(f"Summary: {json_path}")
    return csv_path, json_path


def _csv_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
        for key, value in row.items()
    }


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
