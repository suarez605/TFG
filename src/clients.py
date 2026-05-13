from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

# Alias mapping: config key -> API parameter name per provider.
# Only listed aliases are renamed; everything else passes through as-is.
_OPENAI_ALIASES: dict[str, str] = {
    "maxTokens": "max_output_tokens",
    "max_tokens": "max_output_tokens",
}

_ANTHROPIC_ALIASES: dict[str, str] = {
    "maxTokens": "max_tokens",
}


def _resolve_aliases(config: dict[str, Any], aliases: dict[str, str]) -> dict[str, Any]:
    """Translate alias keys in *config* and return a clean param dict."""
    resolved: dict[str, Any] = {}
    for key, value in config.items():
        resolved[aliases.get(key, key)] = value
    return resolved


class LLMClient(ABC):
    """Base interface for all LLM providers."""

    @abstractmethod
    def generate(
        self,
        model_key: str,
        prompt: str,
        config: dict[str, Any],
        system_prompt: str | None = None,
    ) -> str:
        raise NotImplementedError


class LMStudioClient(LLMClient):
    """Client for local models via LM Studio."""

    def __init__(self, server: str) -> None:
        try:
            import lmstudio as lms
        except ImportError as exc:
            raise ImportError(
                "lmstudio package is required for provider 'lmstudio'. "
                "Install with: pip install lmstudio"
            ) from exc
        self._lms = lms
        lms.configure_default_client(server)

    def generate(
        self,
        model_key: str,
        prompt: str,
        config: dict[str, Any],
        system_prompt: str | None = None,
    ) -> str:
        model = self._lms.llm(model_key)
        if system_prompt is not None:
            chat = self._lms.Chat(system_prompt)
        else:
            chat = self._lms.Chat()
        chat.add_user_message(prompt)
        result = model.respond(chat, config=config)
        return str(result)


class OpenAIClient(LLMClient):
    """Client for OpenAI API (GPT-4o, GPT-4o-mini, etc.)."""

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "Missing API key for provider 'openai'. Set env var OPENAI_API_KEY."
            )
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "openai package is required for provider 'openai'. "
                "Install with: pip install openai"
            ) from exc
        self._client = OpenAI(api_key=api_key)

    def generate(
        self,
        model_key: str,
        prompt: str,
        config: dict[str, Any],
        system_prompt: str | None = None,
    ) -> str:
        params = _resolve_aliases(config, _OPENAI_ALIASES)

        # Extract reasoning config if present and pass as a separate kwarg.
        # When reasoning is active (effort != "none"), temperature must be
        # omitted — the Responses API rejects the combination.
        reasoning = params.pop("reasoning", None)
        if reasoning is not None:
            effort = (
                reasoning.get("effort", "none")
                if isinstance(reasoning, dict)
                else "none"
            )
            if effort != "none":
                params.pop("temperature", None)

        kwargs: dict[str, Any] = {"model": model_key, "input": prompt, **params}
        if reasoning is not None:
            kwargs["reasoning"] = reasoning
        if system_prompt is not None:
            kwargs["instructions"] = system_prompt
        response = self._client.responses.create(**kwargs)
        if not response.output_text:
            raise ValueError(f"OpenAI returned empty content for model={model_key}")
        return response.output_text


class AnthropicClient(LLMClient):
    """Client for Anthropic API (Claude models)."""

    def __init__(self) -> None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "Missing API key for provider 'anthropic'. "
                "Set env var ANTHROPIC_API_KEY."
            )
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "anthropic package is required for provider 'anthropic'. "
                "Install with: pip install anthropic"
            ) from exc
        self._client = anthropic.Anthropic(api_key=api_key)

    def generate(
        self,
        model_key: str,
        prompt: str,
        config: dict[str, Any],
        system_prompt: str | None = None,
    ) -> str:
        params = _resolve_aliases(config, _ANTHROPIC_ALIASES)
        # Anthropic requires max_tokens; use a sensible default if not provided.
        params.setdefault("max_tokens", 400)

        # Extract thinking config if present and pass as a separate kwarg.
        # When thinking is enabled (type="enabled"), temperature must be omitted
        # (the API requires temperature=1, so we drop it and let the API default).
        thinking = params.pop("thinking", None)
        if thinking is not None:
            thinking_type = (
                thinking.get("type", "disabled")
                if isinstance(thinking, dict)
                else "disabled"
            )
            if thinking_type == "enabled":
                params.pop("temperature", None)

        if system_prompt is not None:
            params["system"] = system_prompt
        if thinking is not None:
            params["thinking"] = thinking
        response = self._client.messages.create(
            model=model_key,
            messages=[{"role": "user", "content": prompt}],
            **params,
        )
        text_blocks = [
            block.text for block in response.content if hasattr(block, "text")
        ]
        if not text_blocks:
            raise ValueError(
                f"Anthropic returned no text content for model={model_key}"
            )
        return "\n".join(text_blocks)


class ClientFactory:
    """Creates and caches LLM clients by (provider, server) key."""

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str | None], LLMClient] = {}

    def get(self, provider: str, server: str | None = None) -> LLMClient:
        normalized = provider.lower().strip()
        cache_key = (normalized, server)

        if cache_key in self._cache:
            return self._cache[cache_key]

        if normalized == "lmstudio":
            if not server:
                raise ValueError(
                    "Provider 'lmstudio' requires a 'server' address (e.g. 'localhost:1234')."
                )
            client: LLMClient = LMStudioClient(server)
        elif normalized == "openai":
            client = OpenAIClient()
        elif normalized == "anthropic":
            client = AnthropicClient()
        else:
            raise ValueError(
                f"Unsupported provider: '{provider}'. "
                f"Valid providers: lmstudio, openai, anthropic"
            )

        self._cache[cache_key] = client
        return client
