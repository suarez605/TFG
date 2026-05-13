from __future__ import annotations

from unittest.mock import MagicMock

from src.clients import AnthropicClient, OpenAIClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_openai_client() -> OpenAIClient:
    """Build an OpenAIClient bypassing __init__, injecting a mock _client."""
    client = OpenAIClient.__new__(OpenAIClient)
    client._client = MagicMock()
    return client


def _make_anthropic_client() -> AnthropicClient:
    """Build an AnthropicClient bypassing __init__, injecting a mock _client."""
    client = AnthropicClient.__new__(AnthropicClient)
    client._client = MagicMock()
    return client


# ---------------------------------------------------------------------------
# OpenAIClient — reasoning
# ---------------------------------------------------------------------------


class TestOpenAIClientReasoning:
    def _make_response(self, text: str = "response text") -> MagicMock:
        response = MagicMock()
        response.output_text = text
        return response

    def test_reasoning_passed_as_kwarg(self):
        """When config contains 'reasoning', it is forwarded as a kwarg."""
        client = _make_openai_client()
        client._client.responses.create.return_value = self._make_response()

        client.generate(
            model_key="o4-mini",
            prompt="test prompt",
            config={"reasoning": {"effort": "medium"}, "maxTokens": 4000},
        )

        call_kwargs = client._client.responses.create.call_args.kwargs
        assert call_kwargs["reasoning"] == {"effort": "medium"}
        assert call_kwargs["max_output_tokens"] == 4000

    def test_reasoning_active_removes_temperature(self):
        """When reasoning effort != 'none', temperature must be stripped."""
        client = _make_openai_client()
        client._client.responses.create.return_value = self._make_response()

        client.generate(
            model_key="o4-mini",
            prompt="test prompt",
            config={"reasoning": {"effort": "high"}, "temperature": 0.7},
        )

        call_kwargs = client._client.responses.create.call_args.kwargs
        assert "temperature" not in call_kwargs
        assert call_kwargs["reasoning"] == {"effort": "high"}

    def test_reasoning_none_effort_keeps_temperature(self):
        """When reasoning effort == 'none', temperature is NOT removed."""
        client = _make_openai_client()
        client._client.responses.create.return_value = self._make_response()

        client.generate(
            model_key="gpt-4o",
            prompt="test prompt",
            config={"reasoning": {"effort": "none"}, "temperature": 0.5},
        )

        call_kwargs = client._client.responses.create.call_args.kwargs
        assert call_kwargs.get("temperature") == 0.5
        assert call_kwargs["reasoning"] == {"effort": "none"}

    def test_no_reasoning_passes_temperature_unchanged(self):
        """Without reasoning config, temperature is passed normally."""
        client = _make_openai_client()
        client._client.responses.create.return_value = self._make_response()

        client.generate(
            model_key="gpt-4o",
            prompt="test prompt",
            config={"temperature": 0.3},
        )

        call_kwargs = client._client.responses.create.call_args.kwargs
        assert call_kwargs.get("temperature") == 0.3
        assert "reasoning" not in call_kwargs

    def test_reasoning_not_present_in_resolved_params(self):
        """The 'reasoning' key must not appear in the flattened params dict."""
        client = _make_openai_client()
        client._client.responses.create.return_value = self._make_response()

        client.generate(
            model_key="o4-mini",
            prompt="test prompt",
            config={"reasoning": {"effort": "low"}},
        )

        # reasoning should appear as a top-level kwarg, not duplicated
        call_kwargs = client._client.responses.create.call_args.kwargs
        assert call_kwargs["reasoning"] == {"effort": "low"}


# ---------------------------------------------------------------------------
# AnthropicClient — thinking
# ---------------------------------------------------------------------------


class TestAnthropicClientThinking:
    def _make_response(self, text: str = "response text") -> MagicMock:
        block = MagicMock()
        block.text = text
        response = MagicMock()
        response.content = [block]
        return response

    def test_thinking_passed_as_kwarg(self):
        """When config contains 'thinking', it is forwarded as a kwarg."""
        client = _make_anthropic_client()
        client._client.messages.create.return_value = self._make_response()

        client.generate(
            model_key="claude-opus-4-6",
            prompt="test prompt",
            config={
                "thinking": {"type": "enabled", "budget_tokens": 10000},
                "maxTokens": 16000,
            },
        )

        call_kwargs = client._client.messages.create.call_args.kwargs
        assert call_kwargs["thinking"] == {"type": "enabled", "budget_tokens": 10000}
        assert call_kwargs["max_tokens"] == 16000

    def test_thinking_enabled_removes_temperature(self):
        """When thinking type='enabled', temperature must be stripped."""
        client = _make_anthropic_client()
        client._client.messages.create.return_value = self._make_response()

        client.generate(
            model_key="claude-sonnet-4-6",
            prompt="test prompt",
            config={
                "thinking": {"type": "enabled", "budget_tokens": 5000},
                "temperature": 0.7,
                "maxTokens": 10000,
            },
        )

        call_kwargs = client._client.messages.create.call_args.kwargs
        assert "temperature" not in call_kwargs
        assert call_kwargs["thinking"] == {"type": "enabled", "budget_tokens": 5000}

    def test_thinking_disabled_keeps_temperature(self):
        """When thinking type='disabled', temperature is NOT removed."""
        client = _make_anthropic_client()
        client._client.messages.create.return_value = self._make_response()

        client.generate(
            model_key="claude-sonnet-4-6",
            prompt="test prompt",
            config={
                "thinking": {"type": "disabled"},
                "temperature": 0.5,
                "maxTokens": 4000,
            },
        )

        call_kwargs = client._client.messages.create.call_args.kwargs
        assert call_kwargs.get("temperature") == 0.5
        assert call_kwargs["thinking"] == {"type": "disabled"}

    def test_no_thinking_passes_temperature_unchanged(self):
        """Without thinking config, temperature is passed normally."""
        client = _make_anthropic_client()
        client._client.messages.create.return_value = self._make_response()

        client.generate(
            model_key="claude-3-haiku",
            prompt="test prompt",
            config={"temperature": 0.3, "maxTokens": 2000},
        )

        call_kwargs = client._client.messages.create.call_args.kwargs
        assert call_kwargs.get("temperature") == 0.3
        assert "thinking" not in call_kwargs

    def test_thinking_not_present_in_resolved_params(self):
        """The 'thinking' key must not appear duplicated in params."""
        client = _make_anthropic_client()
        client._client.messages.create.return_value = self._make_response()

        client.generate(
            model_key="claude-opus-4-6",
            prompt="test prompt",
            config={
                "thinking": {"type": "enabled", "budget_tokens": 8000},
                "maxTokens": 12000,
            },
        )

        call_kwargs = client._client.messages.create.call_args.kwargs
        # thinking appears exactly once as a top-level kwarg
        assert call_kwargs["thinking"] == {"type": "enabled", "budget_tokens": 8000}

    def test_thinking_response_extracts_only_text_blocks(self):
        """Response parsing ignores non-text blocks (e.g. thinking blocks)."""
        client = _make_anthropic_client()

        thinking_block = MagicMock(spec=[])  # no 'text' attribute
        text_block = MagicMock()
        text_block.text = "actual answer"

        response = MagicMock()
        response.content = [thinking_block, text_block]
        client._client.messages.create.return_value = response

        result = client.generate(
            model_key="claude-opus-4-6",
            prompt="test prompt",
            config={
                "thinking": {"type": "enabled", "budget_tokens": 5000},
                "maxTokens": 10000,
            },
        )

        assert result == "actual answer"
