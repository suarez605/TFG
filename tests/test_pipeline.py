from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.clients import ClientFactory, LLMClient
from src.pipeline import PipelineRunner, _build_analysis_prompt, _stages_from
from src.pipeline_types import (
    AnalysisConfig,
    FallacyConfig,
    JudgeConfig,
    ModelConfig,
    PipelineConfig,
)
from src.storage import (
    load_state,
    read_analysis_records,
    read_generation_records,
    save_state,
)


class MockClient(LLMClient):
    """Deterministic mock client for testing."""

    def __init__(self, response: str = "mock output") -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def generate(
        self,
        model_key: str,
        prompt: str,
        config: dict[str, Any],
        system_prompt: str | None = None,
    ) -> str:
        self.calls.append({"model_key": model_key, "prompt": prompt, "config": config})
        return self.response


class FailingClient(LLMClient):
    """Client that always raises an error."""

    def generate(
        self,
        model_key: str,
        prompt: str,
        config: dict[str, Any],
        system_prompt: str | None = None,
    ) -> str:
        raise RuntimeError("simulated failure")


@pytest.fixture()
def base_config() -> PipelineConfig:
    return PipelineConfig(
        models=[
            ModelConfig(
                id=1,
                key="model-a",
                provider="lmstudio",
                server="localhost:1234",
                config={"temperature": 0.5},
            ),
        ],
        fallacies=[
            FallacyConfig(
                id=1,
                name="ad baculum",
                description="Appeal to fear",
                topic="immigration",
                generation_prompt="Write fear argument.",
            ),
        ],
        analysis=AnalysisConfig(
            judges=[
                JudgeConfig(
                    key="judge-model",
                    provider="lmstudio",
                    server="localhost:1234",
                    config={"temperature": 0.2},
                ),
            ],
            evaluation_prompts={
                "detection_explicit": "Fallacy {{FALLACY_NAME}}: {{FALLACY_DESCRIPTION}}. Does this text commit it? {{TEXT}}",
                "detection_implicit": "Is there {{FALLACY_NAME}} in this? {{TEXT}}",
                "detection": "Any fallacy here? {{TEXT}}",
                "critique": "Do you agree with this? {{TEXT}}",
            },
        ),
    )


class TestStagesFrom:
    def test_all(self):
        assert _stages_from("all") == ["generation", "analysis"]

    def test_from_generation(self):
        assert _stages_from("generation") == ["generation", "analysis"]

    def test_from_analysis(self):
        assert _stages_from("analysis") == ["analysis"]

    def test_invalid_stage(self):
        with pytest.raises(ValueError, match="Unknown stage"):
            _stages_from("invalid")


class TestBuildAnalysisPrompt:
    def test_replaces_text_placeholder(self):
        result = _build_analysis_prompt(
            template="Argument: {{TEXT}}",
            generation_output="some generated text",
            fallacy_name="ad baculum",
            fallacy_description="Appeal to fear",
        )
        assert result == "Argument: some generated text"

    def test_replaces_fallacy_placeholders(self):
        result = _build_analysis_prompt(
            template="Fallacy: {{FALLACY_NAME}} — {{FALLACY_DESCRIPTION}}. Text: {{TEXT}}",
            generation_output="the argument",
            fallacy_name="ad baculum",
            fallacy_description="Appeal to fear",
        )
        assert result == "Fallacy: ad baculum — Appeal to fear. Text: the argument"

    def test_no_placeholder_returns_template_unchanged(self):
        result = _build_analysis_prompt(
            template="No placeholder here.",
            generation_output="irrelevant",
            fallacy_name="x",
            fallacy_description="y",
        )
        assert result == "No placeholder here."


class TestRunStage:
    def test_run_stage_generation_only(
        self, tmp_path: Path, base_config: PipelineConfig, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "output").mkdir()

        mock = MockClient("generated text")
        runner = PipelineRunner(config=base_config, run_id="test-stage-gen")
        runner.clients = MagicMock(spec=ClientFactory)
        runner.clients.get.return_value = mock

        runner.run_stage("generation")

        # Generation ran
        records = read_generation_records(runner.paths.generation_jsonl)
        assert len(records) == 1

        # Analysis was NOT run
        assert not runner.paths.analysis_jsonl.exists()

    def test_run_stage_invalid_raises(
        self, tmp_path: Path, base_config: PipelineConfig, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "output").mkdir()

        runner = PipelineRunner(config=base_config, run_id="test-stage-invalid")
        with pytest.raises(ValueError, match="Unknown stage"):
            runner.run_stage("invalid")


class TestPipelineGeneration:
    def test_generation_creates_records(
        self, tmp_path: Path, base_config: PipelineConfig, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "output").mkdir()

        mock = MockClient("generated fallacy text")
        runner = PipelineRunner(config=base_config, run_id="test-001")
        runner.clients = MagicMock(spec=ClientFactory)
        runner.clients.get.return_value = mock

        runner.run(start_stage="generation")

        records = read_generation_records(runner.paths.generation_jsonl)
        assert len(records) == 1
        assert records[0].generation_output == "generated fallacy text"
        assert records[0].model_key == "model-a"
        assert records[0].fallacy_name == "ad baculum"
        assert records[0].fallacy_description == "Appeal to fear"

    def test_generation_handles_error_per_item(
        self, tmp_path: Path, base_config: PipelineConfig, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "output").mkdir()

        runner = PipelineRunner(config=base_config, run_id="test-err")
        runner.clients = MagicMock(spec=ClientFactory)
        runner.clients.get.return_value = FailingClient()

        runner.run(start_stage="generation")

        state = load_state(runner.paths.state_path)
        assert state["generation"]["status"] == "completed_with_errors"
        assert len(state["generation"]["errors"]) == 1

    def test_generation_resumes_skipping_done_items(
        self, tmp_path: Path, base_config: PipelineConfig, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "output").mkdir()

        # Use config without analysis to isolate generation behavior
        config_no_analysis = PipelineConfig(
            models=base_config.models,
            fallacies=base_config.fallacies,
            analysis=None,
        )

        mock = MockClient("first run output")
        runner = PipelineRunner(config=config_no_analysis, run_id="test-resume")
        runner.clients = MagicMock(spec=ClientFactory)
        runner.clients.get.return_value = mock

        # First run: generation (1 fallacy x 1 model = 1 call)
        runner.run(start_stage="generation")
        assert len(mock.calls) == 1

        # Second run with same run_id - should skip already generated items
        mock2 = MockClient("second run output")
        runner2 = PipelineRunner(config=config_no_analysis, run_id="test-resume")
        runner2.clients = MagicMock(spec=ClientFactory)
        runner2.clients.get.return_value = mock2

        runner2.run(start_stage="generation")
        assert len(mock2.calls) == 0  # nothing generated, all skipped


class TestPipelineAnalysis:
    def test_full_pipeline_generates_analysis(
        self, tmp_path: Path, base_config: PipelineConfig, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "output").mkdir()

        mock = MockClient("mock output")
        runner = PipelineRunner(config=base_config, run_id="test-full")
        runner.clients = MagicMock(spec=ClientFactory)
        runner.clients.get.return_value = mock

        runner.run(start_stage="all")

        analysis_records = read_analysis_records(runner.paths.analysis_jsonl)
        # One generation record x four analysis types = 4 analysis records
        assert len(analysis_records) == 4
        types = {r.analysis_type for r in analysis_records}
        assert types == {
            "detection_explicit",
            "detection_implicit",
            "detection",
            "critique",
        }
        assert all(r.status == "ok" for r in analysis_records)
        assert all(r.judge_model == "judge-model" for r in analysis_records)
        assert all(r.judge_output == "mock output" for r in analysis_records)

    def test_analysis_detection_prompt_uses_text_placeholder(
        self, tmp_path: Path, base_config: PipelineConfig, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "output").mkdir()

        mock = MockClient("mock output")
        runner = PipelineRunner(config=base_config, run_id="test-prompt")
        runner.clients = MagicMock(spec=ClientFactory)
        runner.clients.get.return_value = mock

        runner.run(start_stage="all")

        analysis_records = read_analysis_records(runner.paths.analysis_jsonl)

        det_explicit = next(
            r for r in analysis_records if r.analysis_type == "detection_explicit"
        )
        det_implicit = next(
            r for r in analysis_records if r.analysis_type == "detection_implicit"
        )
        detection = next(r for r in analysis_records if r.analysis_type == "detection")
        critique = next(r for r in analysis_records if r.analysis_type == "critique")

        # All prompts should have generation output substituted
        assert "mock output" in det_explicit.judge_prompt
        assert "mock output" in det_implicit.judge_prompt
        assert "mock output" in detection.judge_prompt
        assert "mock output" in critique.judge_prompt

        # detection_explicit has fallacy name, description, and the explicit phrasing
        assert "ad baculum" in det_explicit.judge_prompt
        assert "Appeal to fear" in det_explicit.judge_prompt
        assert "Does this text commit it?" in det_explicit.judge_prompt

        # detection_implicit has fallacy name but not the full description text
        assert "ad baculum" in det_implicit.judge_prompt

        # detection has no specific fallacy info (generic detection)
        assert "Any fallacy here?" in detection.judge_prompt

        # critique is opinion-only
        assert "Do you agree with this?" in critique.judge_prompt

    def test_analysis_resumes_per_analysis_type(
        self, tmp_path: Path, base_config: PipelineConfig, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "output").mkdir()

        mock = MockClient("mock output")
        runner = PipelineRunner(config=base_config, run_id="test-resume-analysis")
        runner.clients = MagicMock(spec=ClientFactory)
        runner.clients.get.return_value = mock

        runner.run(start_stage="all")

        # First run: 1 generation call + 4 analysis calls
        assert mock.calls[0]["prompt"] == "Write fear argument."
        assert len(mock.calls) == 5

        # Second run with same run_id: all analysis already done, no new calls
        mock2 = MockClient("second output")
        runner2 = PipelineRunner(config=base_config, run_id="test-resume-analysis")
        runner2.clients = MagicMock(spec=ClientFactory)
        runner2.clients.get.return_value = mock2

        runner2.run(start_stage="analysis")
        assert len(mock2.calls) == 0  # all skipped

    def test_analysis_skipped_without_config(
        self, tmp_path: Path, base_config: PipelineConfig, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "output").mkdir()

        config_no_analysis = PipelineConfig(
            models=base_config.models,
            fallacies=base_config.fallacies,
            analysis=None,
        )

        mock = MockClient("mock output")
        runner = PipelineRunner(config=config_no_analysis, run_id="test-noanalysis")
        runner.clients = MagicMock(spec=ClientFactory)
        runner.clients.get.return_value = mock

        runner.run(start_stage="all")

        state = load_state(runner.paths.state_path)
        assert state["analysis"]["status"] == "skipped"

    def test_analysis_handles_error_per_item(
        self, tmp_path: Path, base_config: PipelineConfig, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "output").mkdir()

        # Generation succeeds, analysis fails
        gen_mock = MockClient("generated text")
        runner = PipelineRunner(config=base_config, run_id="test-analysis-err")
        runner.clients = MagicMock(spec=ClientFactory)

        call_count = 0

        def side_effect(provider, server):
            nonlocal call_count
            call_count += 1
            # First call (generation stage) succeeds
            if call_count == 1:
                return gen_mock
            return FailingClient()

        runner.clients.get.side_effect = side_effect
        runner.run(start_stage="all")

        state = load_state(runner.paths.state_path)
        assert state["analysis"]["status"] == "completed_with_errors"
        # All four analysis types failed → 4 errors
        assert len(state["analysis"]["errors"]) == 4

        analysis_records = read_analysis_records(runner.paths.analysis_jsonl)
        assert all(r.status == "error" for r in analysis_records)

    def test_multi_judge_produces_records_per_judge(self, tmp_path: Path, monkeypatch):
        """1 gen record × 2 judges × 4 analysis types = 8 analysis records."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "output").mkdir()

        multi_judge_config = PipelineConfig(
            models=[
                ModelConfig(
                    id=1,
                    key="model-a",
                    provider="lmstudio",
                    server="localhost:1234",
                    config={"temperature": 0.5},
                ),
            ],
            fallacies=[
                FallacyConfig(
                    id=1,
                    name="ad baculum",
                    description="Appeal to fear",
                    topic="immigration",
                    generation_prompt="Write fear argument.",
                ),
            ],
            analysis=AnalysisConfig(
                judges=[
                    JudgeConfig(
                        key="judge-a",
                        provider="lmstudio",
                        server="localhost:1234",
                        config={"temperature": 0.2},
                    ),
                    JudgeConfig(
                        key="judge-b",
                        provider="openai",
                        server=None,
                        config={"temperature": 0.3},
                    ),
                ],
                evaluation_prompts={
                    "detection_explicit": "Detect explicit: {{TEXT}}",
                    "detection_implicit": "Detect implicit: {{TEXT}}",
                    "detection": "Detect: {{TEXT}}",
                    "critique": "Critique: {{TEXT}}",
                },
            ),
        )

        mock = MockClient("mock output")
        runner = PipelineRunner(config=multi_judge_config, run_id="test-multi-judge")
        runner.clients = MagicMock(spec=ClientFactory)
        runner.clients.get.return_value = mock

        runner.run(start_stage="all")

        analysis_records = read_analysis_records(runner.paths.analysis_jsonl)
        assert len(analysis_records) == 8

        # Each judge has all four analysis types
        judge_a_records = [r for r in analysis_records if r.judge_model == "judge-a"]
        judge_b_records = [r for r in analysis_records if r.judge_model == "judge-b"]
        assert len(judge_a_records) == 4
        assert len(judge_b_records) == 4
        assert {r.analysis_type for r in judge_a_records} == {
            "detection_explicit",
            "detection_implicit",
            "detection",
            "critique",
        }
        assert {r.analysis_type for r in judge_b_records} == {
            "detection_explicit",
            "detection_implicit",
            "detection",
            "critique",
        }

        # Judge providers are preserved
        assert all(r.judge_provider == "lmstudio" for r in judge_a_records)
        assert all(r.judge_provider == "openai" for r in judge_b_records)

    def test_multi_judge_resume_per_judge(self, tmp_path: Path, monkeypatch):
        """Resume correctly distinguishes items by judge key."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "output").mkdir()

        judge_a = JudgeConfig(
            key="judge-a",
            provider="lmstudio",
            server="localhost:1234",
            config={"temperature": 0.2},
        )
        judge_b = JudgeConfig(
            key="judge-b",
            provider="openai",
            server=None,
            config={"temperature": 0.3},
        )

        # First run: only judge-a
        config_one_judge = PipelineConfig(
            models=[
                ModelConfig(
                    id=1,
                    key="model-a",
                    provider="lmstudio",
                    server="localhost:1234",
                    config={"temperature": 0.5},
                ),
            ],
            fallacies=[
                FallacyConfig(
                    id=1,
                    name="ad baculum",
                    description="Appeal to fear",
                    topic="immigration",
                    generation_prompt="Write fear argument.",
                ),
            ],
            analysis=AnalysisConfig(
                judges=[judge_a],
                evaluation_prompts={
                    "detection_explicit": "Detect explicit: {{TEXT}}",
                    "detection_implicit": "Detect implicit: {{TEXT}}",
                    "detection": "Detect: {{TEXT}}",
                    "critique": "Critique: {{TEXT}}",
                },
            ),
        )

        mock = MockClient("first run")
        runner = PipelineRunner(config=config_one_judge, run_id="test-mj-resume")
        runner.clients = MagicMock(spec=ClientFactory)
        runner.clients.get.return_value = mock

        runner.run(start_stage="all")

        # 1 generation + 4 analysis (judge-a × 4 types) = 5 calls
        assert len(mock.calls) == 5

        # Second run: two judges — judge-a should be skipped, judge-b is new.
        # Reset analysis stage status so the runner re-enters the analysis loop.
        state = load_state(runner.paths.state_path)
        state["analysis"]["status"] = "running"
        save_state(runner.paths.state_path, state)

        config_two_judges = PipelineConfig(
            models=config_one_judge.models,
            fallacies=config_one_judge.fallacies,
            analysis=AnalysisConfig(
                judges=[judge_a, judge_b],
                evaluation_prompts={
                    "detection_explicit": "Detect explicit: {{TEXT}}",
                    "detection_implicit": "Detect implicit: {{TEXT}}",
                    "detection": "Detect: {{TEXT}}",
                    "critique": "Critique: {{TEXT}}",
                },
            ),
        )

        mock2 = MockClient("second run")
        runner2 = PipelineRunner(config=config_two_judges, run_id="test-mj-resume")
        runner2.clients = MagicMock(spec=ClientFactory)
        runner2.clients.get.return_value = mock2

        runner2.run_stage("analysis")

        # Only judge-b × 4 types = 4 new calls
        assert len(mock2.calls) == 4

        # Total analysis records: 4 (judge-a) + 4 (judge-b) = 8
        analysis_records = read_analysis_records(runner2.paths.analysis_jsonl)
        assert len(analysis_records) == 8
