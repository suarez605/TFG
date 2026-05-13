from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.pipeline_types import AnalysisRecord, GenerationRecord, RunPaths


def prepare_run_paths(run_id: str) -> RunPaths:
    run_dir = Path("output") / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    return RunPaths(
        run_dir=run_dir,
        state_path=run_dir / "state.json",
        generation_jsonl=run_dir / "generation.jsonl",
        analysis_jsonl=run_dir / "analysis.jsonl",
    )


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "generation": {"status": "pending"},
            "analysis": {"status": "pending"},
        }

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid state format in {path}")
    return data


def save_state(path: Path, state: dict[str, Any]) -> None:
    tmp_path = path.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as file:
        json.dump(state, file, indent=2, ensure_ascii=False)
    tmp_path.replace(path)


def append_generation_record(path: Path, record: GenerationRecord) -> None:
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def read_generation_records(path: Path) -> list[GenerationRecord]:
    if not path.exists():
        return []

    records: list[GenerationRecord] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            records.append(GenerationRecord(**data))
    return records


def append_analysis_record(path: Path, record: AnalysisRecord) -> None:
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def read_analysis_records(path: Path) -> list[AnalysisRecord]:
    if not path.exists():
        return []

    records: list[AnalysisRecord] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            records.append(AnalysisRecord(**data))
    return records
