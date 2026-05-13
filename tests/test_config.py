from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.config import load_pipeline_config


def _write_config(tmp_path: Path, data: dict) -> str:
    config_file = tmp_path / "settings.json"
    config_file.write_text(json.dumps(data), encoding="utf-8")
    return str(config_file)


def _valid_prompts() -> dict[str, str]:
    """Return a minimal valid evaluation_prompts dict."""
    return {
        "detection_explicit": "Explicit? {{TEXT}}",
        "detection_implicit": "Implicit? {{TEXT}}",
        "detection": "Fallacy? {{TEXT}}",
        "critique": "Agree? {{TEXT}}",
    }


@pytest.fixture()
def minimal_config_data() -> dict:
    return {
        "server": "localhost:1234",
        "models": [
            {
                "id": 1,
                "key": "test-model",
                "provider": "lmstudio",
                "server": "localhost:1234",
                "config": {"temperature": 0.5},
            }
        ],
        "fallacies": [
            {
                "id": 1,
                "name": "ad baculum",
                "description": "Appeal to fear",
                "topic": "immigration",
                "generation_prompt": "Write an argument with appeal to fear.",
            }
        ],
    }


class TestLoadConfig:
    def test_loads_minimal_config(self, tmp_path: Path, minimal_config_data: dict):
        path = _write_config(tmp_path, minimal_config_data)
        config = load_pipeline_config(path)

        assert len(config.models) == 1
        assert config.models[0].key == "test-model"
        assert config.models[0].provider == "lmstudio"
        assert len(config.fallacies) == 1
        assert config.fallacies[0].name == "ad baculum"
        assert config.analysis is None

    def test_loads_analysis_config(self, tmp_path: Path, minimal_config_data: dict):
        minimal_config_data["analysis"] = {
            "judges": [
                {
                    "key": "judge-model",
                    "provider": "lmstudio",
                    "server": "localhost:1234",
                    "config": {"temperature": 0.2},
                }
            ],
            "evaluation_prompts": _valid_prompts(),
        }
        path = _write_config(tmp_path, minimal_config_data)
        config = load_pipeline_config(path)

        assert config.analysis is not None
        assert len(config.analysis.judges) == 1
        assert config.analysis.judges[0].key == "judge-model"
        assert config.analysis.judges[0].provider == "lmstudio"
        assert len(config.analysis.evaluation_prompts) == 4
        for prompt_value in config.analysis.evaluation_prompts.values():
            assert "{{TEXT}}" in prompt_value

    def test_default_provider_is_lmstudio(
        self, tmp_path: Path, minimal_config_data: dict
    ):
        del minimal_config_data["models"][0]["provider"]
        path = _write_config(tmp_path, minimal_config_data)
        config = load_pipeline_config(path)

        assert config.models[0].provider == "lmstudio"

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_pipeline_config("/nonexistent/path.json")

    def test_empty_models_raises(self, tmp_path: Path, minimal_config_data: dict):
        minimal_config_data["models"] = []
        path = _write_config(tmp_path, minimal_config_data)

        with pytest.raises(ValueError, match="at least one model"):
            load_pipeline_config(path)

    def test_empty_fallacies_raises(self, tmp_path: Path, minimal_config_data: dict):
        minimal_config_data["fallacies"] = []
        path = _write_config(tmp_path, minimal_config_data)

        with pytest.raises(ValueError, match="at least one fallacy"):
            load_pipeline_config(path)

    def test_duplicate_model_id_raises(self, tmp_path: Path, minimal_config_data: dict):
        minimal_config_data["models"].append(
            {
                "id": 1,
                "key": "other-model",
                "provider": "lmstudio",
                "server": "localhost:1234",
                "config": {},
            }
        )
        path = _write_config(tmp_path, minimal_config_data)

        with pytest.raises(ValueError, match="Duplicate model id"):
            load_pipeline_config(path)

    def test_invalid_provider_raises(self, tmp_path: Path, minimal_config_data: dict):
        minimal_config_data["models"][0]["provider"] = "invalid_provider"
        path = _write_config(tmp_path, minimal_config_data)

        with pytest.raises(ValueError, match="unsupported provider"):
            load_pipeline_config(path)

    def test_empty_generation_prompt_raises(
        self, tmp_path: Path, minimal_config_data: dict
    ):
        minimal_config_data["fallacies"][0]["generation_prompt"] = ""
        path = _write_config(tmp_path, minimal_config_data)

        with pytest.raises(ValueError, match="empty generation_prompt"):
            load_pipeline_config(path)

    def test_lmstudio_without_server_raises(
        self, tmp_path: Path, minimal_config_data: dict
    ):
        del minimal_config_data["models"][0]["server"]
        path = _write_config(tmp_path, minimal_config_data)

        with pytest.raises(ValueError, match="no 'server' set"):
            load_pipeline_config(path)

    @pytest.mark.parametrize(
        "empty_key",
        [
            "detection_explicit",
            "detection_implicit",
            "detection",
            "critique",
        ],
    )
    def test_empty_evaluation_prompt_raises(
        self, tmp_path: Path, minimal_config_data: dict, empty_key: str
    ):
        prompts = _valid_prompts()
        prompts[empty_key] = ""
        minimal_config_data["analysis"] = {
            "judges": [
                {
                    "key": "judge-model",
                    "provider": "lmstudio",
                    "server": "localhost:1234",
                    "config": {},
                }
            ],
            "evaluation_prompts": prompts,
        }
        path = _write_config(tmp_path, minimal_config_data)

        with pytest.raises(ValueError, match=f"'{empty_key}' is empty"):
            load_pipeline_config(path)

    def test_no_evaluation_prompts_raises(
        self, tmp_path: Path, minimal_config_data: dict
    ):
        minimal_config_data["analysis"] = {
            "judges": [
                {
                    "key": "judge-model",
                    "provider": "lmstudio",
                    "server": "localhost:1234",
                    "config": {},
                }
            ],
            "evaluation_prompts": {},
        }
        path = _write_config(tmp_path, minimal_config_data)

        with pytest.raises(ValueError, match="at least one evaluation prompt"):
            load_pipeline_config(path)

    def test_loads_server_per_model(self, tmp_path: Path, minimal_config_data: dict):
        path = _write_config(tmp_path, minimal_config_data)
        config = load_pipeline_config(path)

        assert config.models[0].server == "localhost:1234"

    def test_empty_judges_list_raises(self, tmp_path: Path, minimal_config_data: dict):
        minimal_config_data["analysis"] = {
            "judges": [],
            "evaluation_prompts": _valid_prompts(),
        }
        path = _write_config(tmp_path, minimal_config_data)

        with pytest.raises(ValueError, match="at least one judge"):
            load_pipeline_config(path)

    def test_duplicate_judge_key_raises(
        self, tmp_path: Path, minimal_config_data: dict
    ):
        minimal_config_data["analysis"] = {
            "judges": [
                {
                    "key": "same-key",
                    "provider": "lmstudio",
                    "server": "localhost:1234",
                    "config": {},
                },
                {
                    "key": "same-key",
                    "provider": "openai",
                    "config": {},
                },
            ],
            "evaluation_prompts": _valid_prompts(),
        }
        path = _write_config(tmp_path, minimal_config_data)

        with pytest.raises(ValueError, match="Duplicate judge key"):
            load_pipeline_config(path)

    def test_judge_invalid_provider_raises(
        self, tmp_path: Path, minimal_config_data: dict
    ):
        minimal_config_data["analysis"] = {
            "judges": [
                {
                    "key": "judge-model",
                    "provider": "invalid_provider",
                    "config": {},
                }
            ],
            "evaluation_prompts": _valid_prompts(),
        }
        path = _write_config(tmp_path, minimal_config_data)

        with pytest.raises(ValueError, match="unsupported provider"):
            load_pipeline_config(path)

    def test_judge_lmstudio_without_server_raises(
        self, tmp_path: Path, minimal_config_data: dict
    ):
        minimal_config_data["analysis"] = {
            "judges": [
                {
                    "key": "judge-model",
                    "provider": "lmstudio",
                    "config": {},
                }
            ],
            "evaluation_prompts": _valid_prompts(),
        }
        path = _write_config(tmp_path, minimal_config_data)

        with pytest.raises(ValueError, match="no 'server' set"):
            load_pipeline_config(path)

    def test_loads_multiple_judges(self, tmp_path: Path, minimal_config_data: dict):
        minimal_config_data["analysis"] = {
            "judges": [
                {
                    "key": "judge-local",
                    "provider": "lmstudio",
                    "server": "localhost:1234",
                    "config": {"temperature": 0.2},
                },
                {
                    "key": "judge-openai",
                    "provider": "openai",
                    "config": {"temperature": 0.3},
                },
            ],
            "evaluation_prompts": _valid_prompts(),
        }
        path = _write_config(tmp_path, minimal_config_data)
        config = load_pipeline_config(path)

        assert config.analysis is not None
        assert len(config.analysis.judges) == 2
        assert config.analysis.judges[0].key == "judge-local"
        assert config.analysis.judges[0].provider == "lmstudio"
        assert config.analysis.judges[0].server == "localhost:1234"
        assert config.analysis.judges[1].key == "judge-openai"
        assert config.analysis.judges[1].provider == "openai"
        assert config.analysis.judges[1].server is None

    def test_loads_single_evaluation_prompt(
        self, tmp_path: Path, minimal_config_data: dict
    ):
        """A config with just one evaluation prompt is valid."""
        minimal_config_data["analysis"] = {
            "judges": [
                {
                    "key": "judge-model",
                    "provider": "lmstudio",
                    "server": "localhost:1234",
                    "config": {},
                }
            ],
            "evaluation_prompts": {
                "my_custom_check": "Check this: {{TEXT}}",
            },
        }
        path = _write_config(tmp_path, minimal_config_data)
        config = load_pipeline_config(path)

        assert config.analysis is not None
        assert len(config.analysis.evaluation_prompts) == 1
        assert "my_custom_check" in config.analysis.evaluation_prompts
