# AGENTS.md

## Mission

Guide for coding agents operating in this repository.
Project scope: TFG about controlled generation and evaluation of logical fallacies with LLMs.
Priorities:
- Reproducibility over speed.
- Explicit, versioned configuration.
- Minimal and auditable diffs.
- Safe handling of experiment artifacts.

## Repository Overview

```
TFG/
├── src/
│   ├── main.py             # CLI entry point (argparse, dotenv loading)
│   ├── __init__.py         # Package marker
│   ├── settings.json       # Runtime config (models, fallacies, analysis)
│   ├── pipeline_types.py   # Dataclasses: ModelConfig, FallacyConfig, JudgeConfig,
│   │                       #   AnalysisConfig, PipelineConfig, GenerationRecord,
│   │                       #   AnalysisRecord, RunPaths
│   ├── config.py           # JSON loading + validate_config()
│   ├── clients.py          # LLMClient ABC + LMStudioClient, OpenAIClient,
│   │                       #   AnthropicClient, ClientFactory
│   ├── pipeline.py         # PipelineRunner: _run_generation, _run_analysis
│   └── storage.py          # Atomic state save, JSONL read/write
├── tests/
│   ├── conftest.py         # sys.path setup
│   ├── test_clients.py     # 11 tests: OpenAI reasoning, Anthropic thinking
│   ├── test_config.py      # 22 tests: config loading and validation
│   └── test_pipeline.py    # 19 tests: stages, prompt building, generation, analysis
├── docs/
│   ├── guia.md             # High-level project guide
│   ├── aclaraciones.md     # Clarifications on methodology
│   ├── falacias.md         # Fallacy taxonomy
│   ├── indice-posible.md   # Possible thesis index
│   └── sintesis-papers.md  # Synthesis of MAFALDA and LOGIC papers
├── env/                    # Python 3.14 virtualenv (not committed)
├── output/runs/            # Runtime output: one dir per run_id (not committed)
├── requirements.txt        # Runtime dependencies (pinned)
├── requirements-dev.txt    # Dev dependencies: pytest, ruff, black (pinned)
├── .env                    # API keys (not committed)
├── .env.example            # Template: OPENAI_API_KEY, ANTHROPIC_API_KEY
└── .gitignore
```

## Pipeline Architecture

The pipeline has two stages that run in order: `generation` → `analysis`.

**Generation**: For each `(model, fallacy)` pair, calls the model with the
fallacy's `generation_prompt` and records the output as a `GenerationRecord`.

**Analysis**: For each `(judge, generation_record, analysis_type)` triple,
fills the prompt template with `{{TEXT}}`, `{{FALLACY_NAME}}`,
`{{FALLACY_DESCRIPTION}}` and records the judge's output as an `AnalysisRecord`.
Number of analysis records = N_generation × N_judges × N_analysis_types.

Both stages are **resumable per item**: re-running with the same `--run-id`
skips already-completed items. Errors are recorded per item and do not abort
the run; the stage ends with `completed_with_errors`.

**Loop ordering** (important for LM Studio performance): generation iterates
`model → fallacy`; analysis iterates `judge → generation_record → analysis_type`.
This ensures each model/judge is loaded once before moving to the next.

## Output Artifacts

Each run produces a directory at `output/runs/<run_id>/`:

- `state.json` — stage statuses (`pending` / `running` / `completed` /
  `completed_with_errors` / `skipped`) and per-stage error lists.
- `generation.jsonl` — one `GenerationRecord` JSON per line.
- `analysis.jsonl` — one `AnalysisRecord` JSON per line.

Resume key for generation: `(fallacy_id, model_key)`.
Resume key for analysis: `(fallacy_id, model_key, judge_model_key, analysis_type)`.

## Configuration (`src/settings.json`)

Top-level keys:

```json
{
  "models": [...],
  "fallacies": [...],
  "analysis": { "judges": [...], "evaluation_prompts": { ... } }
}
```

**Model fields**: `id` (int, unique), `key` (model identifier passed to the
provider), `provider` (`lmstudio` | `openai` | `anthropic`), `server`
(required for lmstudio, e.g. `"localhost:1234"`), `config` (pass-through
params: `temperature`, `maxTokens`, etc.), `system_prompt` (optional string;
`""` and `null` are both treated as no system prompt).

**Fallacy fields**: `id` (int, unique), `name`, `description`, `topic`,
`generation_prompt` (non-empty).

**Judge fields**: same as model fields except no `id` and no `system_prompt`.
`key` must be unique across judges.

**`evaluation_prompts`**: dict of `{ "type_name": "prompt template" }`.
At least one entry required; no blank values. Available placeholders:
`{{TEXT}}`, `{{FALLACY_NAME}}`, `{{FALLACY_DESCRIPTION}}`.

## LLM Client Interface

```python
class LLMClient(ABC):
    def generate(
        self,
        model_key: str,
        prompt: str,
        config: dict[str, Any],
        system_prompt: str | None = None,
    ) -> str: ...
```

- `LMStudioClient`: uses `lmstudio.Chat(system_prompt)` / `lmstudio.Chat()`.
- `OpenAIClient`: uses the Responses API (`client.responses.create`); passes
  `instructions=system_prompt` if set; reads output via `response.output_text`.
- `AnthropicClient`: passes `system=system_prompt` kwarg if set; defaults
  `max_tokens` to 2000 if not in config.
- `ClientFactory`: caches clients by `(provider, server)` — one instance per
  provider+server combination across the whole run.

Config keys are pass-through with alias mapping:
- `maxTokens` → `max_output_tokens` (OpenAI Responses API) / `max_tokens` (Anthropic).

**Reasoning / thinking (special config keys):**

- **OpenAI** — add `"reasoning": {"effort": "low"|"medium"|"high"}` to `config`.
  The client extracts it and passes it as a separate kwarg to `responses.create()`.
  When `effort` is anything other than `"none"`, `temperature` is automatically
  removed from the params (the Responses API rejects the combination).

- **Anthropic** — add `"thinking": {"type": "enabled", "budget_tokens": N}` to
  `config`. The client extracts it and passes it as a separate kwarg to
  `messages.create()`. When `type` is `"enabled"`, `temperature` is automatically
  removed (the API requires temperature=1; omitting it lets the API use the default).
  Response parsing already ignores `thinking` content blocks and returns only `text`
  blocks. LM Studio has no standardised reasoning API; no special handling is applied.

Example `settings.json` snippets:
```json
// OpenAI reasoning model
{ "key": "o4-mini", "provider": "openai",
  "config": { "reasoning": {"effort": "medium"}, "maxTokens": 8000 } }

// Anthropic extended thinking
{ "key": "claude-sonnet-4-6", "provider": "anthropic",
  "config": { "thinking": {"type": "enabled", "budget_tokens": 10000},
              "maxTokens": 16000 } }
```

## Providers and API Keys

| Provider   | Env var              | Notes                                    |
|------------|----------------------|------------------------------------------|
| lmstudio   | —                    | Requires `server` per model/judge        |
| openai     | `OPENAI_API_KEY`     | Set in `.env` or environment             |
| anthropic  | `ANTHROPIC_API_KEY`  | Set in `.env` or environment             |

Keys are loaded from `.env` at startup via `python-dotenv`.

## Environment Setup

```bash
python -m venv env
source env/bin/activate
pip install -U pip
pip install -r requirements.txt -r requirements-dev.txt
```

## Build / Lint / Test Commands

Run pipeline:
```bash
python src/main.py
python src/main.py --run-id my-run --from-stage generation
python src/main.py --run-id my-run --stage analysis
```

Lint:
```bash
ruff check src tests
```

Format check:
```bash
black --check src tests
```

Format in place:
```bash
black src tests
```

Type check:
```bash
mypy src
```

Run all tests:
```bash
pytest tests/ -v
```

Run a single test file:
```bash
pytest tests/test_<name>.py
```

Run a single test function:
```bash
pytest tests/test_<name>.py::ClassName::test_function_name
```

Run tests by keyword:
```bash
pytest -k "<keyword>"
```

Optional coverage:
```bash
pytest --cov=src --cov-report=term-missing
```

## Code Style Guidelines

General:
- Use modern Python style (3.11+ typing idioms).
- Keep functions focused and side effects explicit.
- Prefer deterministic behavior for experiments.
- Avoid hidden state and implicit globals.
- Do not swallow exceptions silently.

Imports:
- Group imports in this order: stdlib, third-party, local.
- Prefer explicit imports; avoid wildcard imports.
- Remove unused imports.

Formatting:
- Follow Black defaults (88-char width).
- Use 4 spaces, never tabs.
- Keep control flow readable; avoid compact one-liners for complex logic.

Types:
- Add type hints to public functions and non-trivial internals.
- Prefer concrete types: `list[str]`, `dict[str, Any]`, dataclasses, TypedDict.
- Validate external/untyped inputs at boundaries (JSON, files, network).

Naming:
- `snake_case` for variables and functions.
- `PascalCase` for classes and dataclasses.
- `UPPER_SNAKE_CASE` for constants.
- Prefer domain terms (`fallacy`, `generation_prompt`, `model_key`) over generic names.

Error handling:
- Raise specific exceptions (`FileNotFoundError`, `ValueError`, etc.).
- Include actionable context in errors (path, key, model id/key).
- Fail fast on invalid config; do not continue with partial state.

Paths and I/O:
- Use `pathlib.Path`.
- Use UTF-8 explicitly in text I/O.
- Keep generated artifacts under `output/` unless requirements say otherwise.
- Prefer atomic writes when practical.

Logging/output:
- Prefer structured and consistent logs over ad-hoc prints.
- Keep temporary `print` lines concise and grep-friendly.

## TFG Pipeline Guidance

When modifying pipeline logic:
- Keep taxonomy and prompt definitions explicit and versionable.
- Track metadata: timestamp, model key/id, generation config.
- Separate generation prompts from analysis/judge prompts.
- Do not mix raw model output with manual post-edits in the same field.

Stage boundaries:
1. Configuration loading and validation.
2. Generation (`generation_prompt` → `GenerationRecord`).
3. Analysis (`evaluation_prompts` × judges → `AnalysisRecord`).

## Testing Expectations

For logic changes:
1. Add/update tests in `tests/` when a suite exists.
2. Cover config parsing and one happy path.
3. Add regression tests for bug fixes.
4. Keep tests deterministic (fixed seeds, stable fixtures, mocked clients).

For LLM/network behavior:
- Mock model clients in unit tests using `MockClient(LLMClient)`.
- Keep integration tests explicit and optional.

## Change Checklist

Before finishing work:
- Run `black src tests`.
- Run `ruff check src tests`.
- Run `mypy src` when feasible.
- Run `pytest tests/ -v`.
- Document output schema changes in this file.
- Verify no secrets or machine-specific absolute paths are committed.

## Cursor / Copilot Rules

Scanned: `.cursorrules`, `.cursor/rules/`, `.github/copilot-instructions.md`.
Result: none found. If these files appear later, treat them as higher-priority
constraints and update this file.

## Agent Constraints

- Do not introduce unrelated refactors.
- Keep diffs minimal and aligned with current architecture.
- If key tooling is missing, propose canonical files explicitly.
- If adding `pyproject.toml`, `requirements*.txt`, `tests/`, or rule files,
  update this file.
