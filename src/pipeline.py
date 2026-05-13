from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.clients import ClientFactory
from src.pipeline_types import (
    AnalysisRecord,
    GenerationRecord,
    PipelineConfig,
    now_iso,
)
from src.storage import (
    append_analysis_record,
    append_generation_record,
    load_state,
    prepare_run_paths,
    read_analysis_records,
    read_generation_records,
    save_state,
)

STAGES_ORDER = ["generation", "analysis"]


def _new_run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


def _build_analysis_prompt(
    template: str,
    generation_output: str,
    fallacy_name: str,
    fallacy_description: str,
) -> str:
    return (
        template.replace("{{TEXT}}", generation_output)
        .replace("{{FALLACY_NAME}}", fallacy_name)
        .replace("{{FALLACY_DESCRIPTION}}", fallacy_description)
    )


def _stages_from(start: str) -> list[str]:
    if start == "all":
        return list(STAGES_ORDER)
    if start not in STAGES_ORDER:
        raise ValueError(f"Unknown stage: {start}. Valid: {STAGES_ORDER}")
    idx = STAGES_ORDER.index(start)
    return STAGES_ORDER[idx:]


class PipelineRunner:
    def __init__(self, config: PipelineConfig, run_id: str | None = None) -> None:
        self.config = config
        self.run_id = run_id or _new_run_id()
        self.paths = prepare_run_paths(self.run_id)
        self.clients = ClientFactory()

    def run(self, start_stage: str = "generation") -> None:
        state = load_state(self.paths.state_path)
        stages = _stages_from(start_stage)

        for stage in stages:
            if stage == "generation":
                self._run_generation(state)
            elif stage == "analysis":
                self._run_analysis(state)

    def run_stage(self, stage: str) -> None:
        state = load_state(self.paths.state_path)

        if stage == "generation":
            self._run_generation(state)
        elif stage == "analysis":
            self._run_analysis(state)
        else:
            raise ValueError(f"Unknown stage: {stage}. Valid: {STAGES_ORDER}")

    def _run_generation(self, state: dict[str, Any]) -> None:
        generation_state = state.setdefault("generation", {"status": "pending"})
        status = generation_state.get("status")
        if status == "completed":
            print("[generation] already completed, skipping")
            return
        if status in {"running", "completed_with_errors"}:
            print(f"[generation] resuming (previous status: {status})")

        generation_state["status"] = "running"
        save_state(self.paths.state_path, state)

        # Build set of already-generated items to support resume
        existing = read_generation_records(self.paths.generation_jsonl)
        generated_keys: set[tuple[int, str]] = set()
        for rec in existing:
            generated_keys.add((rec.fallacy_id, rec.model_key))

        errors: list[str] = []

        for model in self.config.models:
            client = self.clients.get(model.provider, model.server)

            for fallacy in self.config.fallacies:
                item_key = (fallacy.id, model.key)
                if item_key in generated_keys:
                    print(
                        f"[generation] already done fallacy={fallacy.name} "
                        f"model={model.key}, skipping"
                    )
                    continue

                try:
                    print(
                        f"[generation] fallacy={fallacy.name} "
                        f"model={model.key} provider={model.provider}"
                    )
                    output = client.generate(
                        model_key=model.key,
                        prompt=fallacy.generation_prompt,
                        config=model.config,
                        system_prompt=model.system_prompt,
                    )

                    record = GenerationRecord(
                        run_id=self.run_id,
                        created_at=now_iso(),
                        fallacy_id=fallacy.id,
                        fallacy_name=fallacy.name,
                        fallacy_description=fallacy.description,
                        topic=fallacy.topic,
                        generation_prompt=fallacy.generation_prompt,
                        model_id=model.id,
                        model_key=model.key,
                        provider=model.provider,
                        model_config=model.config,
                        generation_output=output,
                    )
                    append_generation_record(self.paths.generation_jsonl, record)

                except Exception as exc:
                    error_msg = f"fallacy={fallacy.name} model={model.key}: {exc}"
                    print(f"[generation] ERROR {error_msg}")
                    errors.append(error_msg)

        if errors:
            generation_state["status"] = "completed_with_errors"
            generation_state["errors"] = errors
        else:
            generation_state["status"] = "completed"

        save_state(self.paths.state_path, state)

    def _run_analysis(self, state: dict[str, Any]) -> None:
        analysis_state = state.setdefault("analysis", {"status": "pending"})
        status = analysis_state.get("status")
        if status == "completed":
            print("[analysis] already completed, skipping")
            return
        if status in {"running", "completed_with_errors"}:
            print(f"[analysis] resuming (previous status: {status})")

        if not self.config.analysis:
            print("[analysis] no analysis config found, skipping")
            analysis_state["status"] = "skipped"
            save_state(self.paths.state_path, state)
            return

        analysis_cfg = self.config.analysis
        analysis_state["status"] = "running"
        save_state(self.paths.state_path, state)

        generation_records = read_generation_records(self.paths.generation_jsonl)
        if not generation_records:
            print("[analysis] no generation records found, nothing to analyze")
            analysis_state["status"] = "completed"
            save_state(self.paths.state_path, state)
            return

        # Build set of already-analyzed items to support resume
        # Key: (fallacy_id, model_key, judge_key, analysis_type)
        existing = read_analysis_records(self.paths.analysis_jsonl)
        analyzed_keys: set[tuple[int, str, str, str]] = set()
        for rec in existing:
            analyzed_keys.add(
                (rec.fallacy_id, rec.model_key, rec.judge_model, rec.analysis_type)
            )

        # Detect orphaned generation records
        fallacy_ids = {f.id for f in self.config.fallacies}

        errors: list[str] = []

        for judge in analysis_cfg.judges:
            client = self.clients.get(judge.provider, judge.server)

            for gen_record in generation_records:
                if gen_record.fallacy_id not in fallacy_ids:
                    print(
                        f"[analysis] WARNING: no fallacy config for "
                        f"id={gen_record.fallacy_id}, skipping"
                    )
                    continue

                for (
                    analysis_type,
                    prompt_template,
                ) in analysis_cfg.evaluation_prompts.items():
                    item_key = (
                        gen_record.fallacy_id,
                        gen_record.model_key,
                        judge.key,
                        analysis_type,
                    )
                    if item_key in analyzed_keys:
                        print(
                            f"[analysis] already done fallacy={gen_record.fallacy_name} "
                            f"model={gen_record.model_key} judge={judge.key} "
                            f"type={analysis_type}, skipping"
                        )
                        continue

                    judge_prompt = _build_analysis_prompt(
                        template=prompt_template,
                        generation_output=gen_record.generation_output,
                        fallacy_name=gen_record.fallacy_name,
                        fallacy_description=gen_record.fallacy_description,
                    )

                    try:
                        print(
                            f"[analysis] fallacy={gen_record.fallacy_name} "
                            f"model={gen_record.model_key} judge={judge.key} "
                            f"type={analysis_type}"
                        )
                        judge_output = client.generate(
                            model_key=judge.key,
                            prompt=judge_prompt,
                            config=judge.config,
                        )

                        analysis_record = AnalysisRecord(
                            run_id=self.run_id,
                            created_at=now_iso(),
                            fallacy_id=gen_record.fallacy_id,
                            fallacy_name=gen_record.fallacy_name,
                            topic=gen_record.topic,
                            model_key=gen_record.model_key,
                            provider=gen_record.provider,
                            generation_prompt=gen_record.generation_prompt,
                            generation_output=gen_record.generation_output,
                            analysis_type=analysis_type,
                            judge_model=judge.key,
                            judge_provider=judge.provider,
                            judge_prompt=judge_prompt,
                            judge_output=judge_output,
                            status="ok",
                            error="",
                        )

                    except Exception as exc:
                        error_msg = (
                            f"fallacy={gen_record.fallacy_name} "
                            f"model={gen_record.model_key} judge={judge.key} "
                            f"type={analysis_type}: {exc}"
                        )
                        print(f"[analysis] ERROR {error_msg}")
                        errors.append(error_msg)

                        analysis_record = AnalysisRecord(
                            run_id=self.run_id,
                            created_at=now_iso(),
                            fallacy_id=gen_record.fallacy_id,
                            fallacy_name=gen_record.fallacy_name,
                            topic=gen_record.topic,
                            model_key=gen_record.model_key,
                            provider=gen_record.provider,
                            generation_prompt=gen_record.generation_prompt,
                            generation_output=gen_record.generation_output,
                            analysis_type=analysis_type,
                            judge_model=judge.key,
                            judge_provider=judge.provider,
                            judge_prompt=judge_prompt,
                            judge_output="",
                            status="error",
                            error=str(exc),
                        )

                    append_analysis_record(self.paths.analysis_jsonl, analysis_record)

        if errors:
            analysis_state["status"] = "completed_with_errors"
            analysis_state["errors"] = errors
        else:
            analysis_state["status"] = "completed"

        save_state(self.paths.state_path, state)
