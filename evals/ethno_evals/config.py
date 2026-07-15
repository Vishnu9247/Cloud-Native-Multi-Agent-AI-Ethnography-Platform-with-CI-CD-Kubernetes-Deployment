from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVALS_ROOT = PROJECT_ROOT / "evals"
BACKEND_ROOT = PROJECT_ROOT / "Backend"


@dataclass(frozen=True)
class EvalConfig:
    input_path: Path
    output_path: Path
    max_turns: int = 80
    llm_model: str = "llama3.2"
    sqlite_path: Path = EVALS_ROOT / ".runtime" / "evals.sqlite3"
    chroma_path: Path = EVALS_ROOT / ".runtime" / "chroma"


def bootstrap_backend(config: EvalConfig) -> None:
    """Prepare imports and eval-local persistence before backend modules load."""

    runtime_dir = EVALS_ROOT / ".runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    config.chroma_path.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("LLM_MODEL", config.llm_model)
    os.environ.setdefault("DATABASE_BACKEND", "sqlite")
    os.environ.setdefault("SQLITE_DATABASE_PATH", str(config.sqlite_path))
    os.environ.setdefault("CHROMA_PERSIST_PATH", str(config.chroma_path))

    backend_path = str(BACKEND_ROOT)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)


def default_output_path() -> Path:
    return EVALS_ROOT / "evaluation_results.xlsx"
