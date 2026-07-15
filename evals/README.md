# Ethnography AI Interviewer Evals

Evaluation framework for running persona-based end-to-end tests against the
backend unified chat workflow.

The runner reads `personas.xlsx`, simulates a user for each persona with the same
backend LLM configuration (`llama3.2` by default), drives the real backend
workflow, scores the session, and writes comparison-ready Excel results.

## Expected Input

`personas.xlsx` must contain:

- `Name`
- `Problem`
- `Person Details`
- `Ethnographic Solution`

## Run

From the repository root:

```powershell
Backend\.venv\Scripts\python.exe -m evals.run --all
```

Run one Excel row:

```powershell
Backend\.venv\Scripts\python.exe -m evals.run --row 2
```

Optional arguments:

```powershell
Backend\.venv\Scripts\python.exe -m evals.run --all --input evals\personas.xlsx --output evals\results.xlsx --max-turns 80
```

The evaluator stores temporary runtime data under `evals/.runtime` by default:

- `evals/.runtime/evals.sqlite3`
- `evals/.runtime/chroma`

This keeps eval sessions separate from normal backend sessions. Override paths
with `SQLITE_DATABASE_PATH` and `CHROMA_PERSIST_PATH` if needed.

## Output Workbook

The generated workbook contains:

- `summary`: one row per persona with high-level scores and diagnostics
- `turns`: every simulated Q/A turn with domain, subdomain, validation, and gaps
- `retrieval`: retrieved context records and confidence scores when available
- `events`: backend workflow events for debugging consistency and failures

## Dependencies

The framework uses the backend package and its dependency set. If the backend
virtualenv is incomplete, install/sync backend dependencies first:

```powershell
cd Backend
uv sync
```

For Excel support, ensure `pandas` and `openpyxl` are installed in the Python
environment used to run the evals.
