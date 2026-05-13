from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class ModelConfig:
    id: int
    key: str
    provider: str
    server: str | None
    config: dict[str, Any]
    system_prompt: str | None = None


@dataclass(frozen=True)
class FallacyConfig:
    id: int
    name: str
    description: str
    topic: str
    generation_prompt: str


@dataclass(frozen=True)
class JudgeConfig:
    key: str
    provider: str
    server: str | None
    config: dict[str, Any]


@dataclass(frozen=True)
class AnalysisConfig:
    judges: list[JudgeConfig]
    evaluation_prompts: dict[str, str]


@dataclass(frozen=True)
class PipelineConfig:
    models: list[ModelConfig]
    fallacies: list[FallacyConfig]
    analysis: AnalysisConfig | None


@dataclass(frozen=True)
class GenerationRecord:
    run_id: str
    created_at: str
    fallacy_id: int
    fallacy_name: str
    fallacy_description: str
    topic: str
    generation_prompt: str
    model_id: int
    model_key: str
    provider: str
    model_config: dict[str, Any]
    generation_output: str


@dataclass(frozen=True)
class AnalysisRecord:
    run_id: str
    created_at: str
    fallacy_id: int
    fallacy_name: str
    topic: str
    model_key: str
    provider: str
    generation_prompt: str
    generation_output: str
    analysis_type: str
    judge_model: str
    judge_provider: str
    judge_prompt: str
    judge_output: str
    status: str
    error: str


@dataclass(frozen=True)
class RunPaths:
    run_dir: Path
    state_path: Path
    generation_jsonl: Path
    analysis_jsonl: Path
