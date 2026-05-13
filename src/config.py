from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.pipeline_types import (
    AnalysisConfig,
    FallacyConfig,
    JudgeConfig,
    ModelConfig,
    PipelineConfig,
)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be an object: {path}")
    return data


def load_pipeline_config(path: str) -> PipelineConfig:
    raw = _read_json(Path(path))

    models_raw = raw.get("models", [])
    if not isinstance(models_raw, list):
        raise ValueError("'models' must be a list")

    fallacies_raw = raw.get("fallacies", [])
    if not isinstance(fallacies_raw, list):
        raise ValueError("'fallacies' must be a list")

    models: list[ModelConfig] = []
    for model in models_raw:
        if not isinstance(model, dict):
            raise ValueError("Each model entry must be an object")
        provider = str(model.get("provider", "lmstudio"))
        config = model.get("config", {})
        if not isinstance(config, dict):
            raise ValueError("'config' in model must be an object")
        server = model.get("server")
        models.append(
            ModelConfig(
                id=int(model["id"]),
                key=str(model["key"]),
                provider=provider,
                server=str(server) if server is not None else None,
                config=config,
                system_prompt=model.get("system_prompt") or None,
            )
        )

    fallacies: list[FallacyConfig] = []
    for fallacy in fallacies_raw:
        if not isinstance(fallacy, dict):
            raise ValueError("Each fallacy entry must be an object")
        fallacies.append(
            FallacyConfig(
                id=int(fallacy["id"]),
                name=str(fallacy["name"]),
                description=str(fallacy.get("description", "")),
                topic=str(fallacy.get("topic", "")),
                generation_prompt=str(fallacy.get("generation_prompt", "")),
            )
        )

    analysis: AnalysisConfig | None = None
    analysis_raw = raw.get("analysis")
    if isinstance(analysis_raw, dict):
        judges_raw = analysis_raw.get("judges", [])
        if not isinstance(judges_raw, list):
            raise ValueError("'analysis.judges' must be a list")

        judges: list[JudgeConfig] = []
        for judge in judges_raw:
            if not isinstance(judge, dict):
                raise ValueError("Each judge entry must be an object")
            j_provider = str(judge.get("provider", "lmstudio"))
            j_config = judge.get("config", {})
            if not isinstance(j_config, dict):
                raise ValueError("'config' in judge must be an object")
            j_server = judge.get("server")
            judges.append(
                JudgeConfig(
                    key=str(judge["key"]),
                    provider=j_provider,
                    server=str(j_server) if j_server is not None else None,
                    config=j_config,
                )
            )

        prompts_raw = analysis_raw.get("evaluation_prompts", {})
        if not isinstance(prompts_raw, dict):
            raise ValueError("'analysis.evaluation_prompts' must be an object")
        evaluation_prompts: dict[str, str] = {
            str(k): str(v) for k, v in prompts_raw.items()
        }

        analysis = AnalysisConfig(
            judges=judges,
            evaluation_prompts=evaluation_prompts,
        )

    config = PipelineConfig(
        models=models,
        fallacies=fallacies,
        analysis=analysis,
    )
    validate_config(config)
    return config


VALID_PROVIDERS = {"lmstudio", "openai", "anthropic"}


def validate_config(config: PipelineConfig) -> None:
    """Validate pipeline config eagerly so errors surface before execution."""
    if not config.models:
        raise ValueError("Config must define at least one model")
    if not config.fallacies:
        raise ValueError("Config must define at least one fallacy")

    seen_model_ids: set[int] = set()
    for model in config.models:
        if model.id in seen_model_ids:
            raise ValueError(f"Duplicate model id: {model.id}")
        seen_model_ids.add(model.id)

        if not model.key.strip():
            raise ValueError(f"Model id={model.id} has empty key")

        if model.provider not in VALID_PROVIDERS:
            raise ValueError(
                f"Model '{model.key}' has unsupported provider '{model.provider}'. "
                f"Valid: {VALID_PROVIDERS}"
            )

        if model.provider == "lmstudio" and not model.server:
            raise ValueError(
                f"Model '{model.key}' uses provider 'lmstudio' but has no 'server' set. "
                f"Add a 'server' field (e.g. 'localhost:1234') to this model entry."
            )

    seen_fallacy_ids: set[int] = set()
    for fallacy in config.fallacies:
        if fallacy.id in seen_fallacy_ids:
            raise ValueError(f"Duplicate fallacy id: {fallacy.id}")
        seen_fallacy_ids.add(fallacy.id)

        if not fallacy.name.strip():
            raise ValueError(f"Fallacy id={fallacy.id} has empty name")
        if not fallacy.generation_prompt.strip():
            raise ValueError(f"Fallacy '{fallacy.name}' has empty generation_prompt")

    if config.analysis:
        if not config.analysis.judges:
            raise ValueError("Analysis must define at least one judge")

        if not config.analysis.evaluation_prompts:
            raise ValueError(
                "Analysis must define at least one evaluation prompt "
                "in 'evaluation_prompts'"
            )
        for prompt_key, prompt_value in config.analysis.evaluation_prompts.items():
            if not prompt_key.strip():
                raise ValueError("An evaluation prompt has an empty key")
            if not prompt_value.strip():
                raise ValueError(f"Evaluation prompt '{prompt_key}' is empty")

        seen_judge_keys: set[str] = set()
        for judge in config.analysis.judges:
            if not judge.key.strip():
                raise ValueError("A judge has an empty key")
            if judge.key in seen_judge_keys:
                raise ValueError(f"Duplicate judge key: {judge.key}")
            seen_judge_keys.add(judge.key)

            if judge.provider not in VALID_PROVIDERS:
                raise ValueError(
                    f"Judge '{judge.key}' has unsupported provider '{judge.provider}'. "
                    f"Valid: {VALID_PROVIDERS}"
                )
            if judge.provider == "lmstudio" and not judge.server:
                raise ValueError(
                    f"Judge '{judge.key}' uses provider 'lmstudio' but has no 'server' set. "
                    f"Add a 'server' field (e.g. 'localhost:1234') to this judge entry."
                )
