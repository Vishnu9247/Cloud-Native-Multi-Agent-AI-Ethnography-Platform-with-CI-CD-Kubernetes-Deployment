# Independent Agent Prompt Evaluations

This suite compares the revised prompt variants in
`Backend/App/prompt_utils/Test_Promps` with Ollama `llama3.2`:

- `a`: Tight / concise
- `b`: Few-shot heavy
- `c`: Checklist / structured
- `all`: run all three variants

Each of the five agent suites has 40 grounded test cases. Agents run
independently; the production workflow and vector database are not required.

## Prerequisites

In one PowerShell terminal, start Ollama:

```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" serve
```

If needed, install the model from another terminal:

```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" pull llama3.2
```

Run all commands below from the repository root with Python 3.11 or newer.
The evaluators themselves use only the Python standard library.

## Separate agent commands

```powershell
python -m evals.agent_evals.run_problem_framing --variant all
python -m evals.agent_evals.run_domain_selection --variant all
python -m evals.agent_evals.run_domain_interview --variant all
python -m evals.agent_evals.run_interview_validation --variant all
python -m evals.agent_evals.run_pattern_analysis --variant all
```

Running `--variant all` with LLM judging can take a while: each agent evaluates
40 cases across three prompt variants, and multi-task agents make several calls
per case.

## Useful options

```powershell
# Fast end-to-end smoke test with one case and all three variants
python -m evals.agent_evals.run_domain_selection --variant all --case-limit 1

# One prompt variant only
python -m evals.agent_evals.run_pattern_analysis --variant c

# One named case
python -m evals.agent_evals.run_pattern_analysis --variant a --case-id ETHNO-031

# Deterministic metrics only; skips LLM judge calls
python -m evals.agent_evals.run_domain_interview --variant all --no-judge

# Custom output directory
python -m evals.agent_evals.run_problem_framing --variant all --output-dir evals/agent_evals/results/run_01
```

## Results and complete logs

Each command writes an isolated result package:

```text
evals/agent_evals/results/<agent>/details.csv
evals/agent_evals/results/<agent>/summary.json
evals/agent_evals/results/<agent>/logs/calls.jsonl
evals/agent_evals/results/<agent>/logs/run.log
```

`details.csv` includes the complete rendered agent prompt, complete agent
response, complete judge prompt, complete judge response, token counts,
latency, deterministic metrics, judge metrics, and overall score.

`calls.jsonl` is the lossless machine-readable call audit. Each row contains
the run ID, timestamp, model, case, variant, task, call type, full prompt, full
response, latency, and token counts. `run.log` contains the same prompt/response
history in a readable transcript format.

## Metrics

All quality metrics are clamped to `0.0-1.0`:

- `metric_overall_score`
- `metric_groundedness`
- `metric_relevance`
- `metric_completeness`
- `metric_faithfulness`
- `metric_coherence`
- `metric_instruction_compliance`
- `metric_safety`
- `metric_confidence`
- `metric_format_valid`
- Task-specific deterministic metrics such as precision, recall, F1,
  classification accuracy, cue coverage, and empty-pattern accuracy

The LLM judge receives the gold case oracle, forbidden claims, the evaluated
response, and a task-specific rubric. The combined score weights deterministic
format/task checks, judge overall quality, groundedness, and judge confidence.
Latency and token counts are operational measurements and are not normalized
quality metrics.

## Dataset generation

The 40-case canonical dataset is generated deterministically from eight
carefully authored evidence-grounded archetypes crossed with five communication
styles:

```powershell
python -m evals.agent_evals.expand_dataset
```

The generated dataset is:

```text
evals/agent_evals/dataset/agent_eval_dataset_40.json
```
