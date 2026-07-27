"""Provider-agnostic LLM client. Swap providers via LLM_PROVIDER env var — no
call-site changes. Exists because live model access on the bank laptop is not
guaranteed by hackathon day; CachedReplayClient lets the whole app run with
zero network dependency using responses recorded during development.
"""
from __future__ import annotations

import abc
import os
from typing import Any

from pydantic import BaseModel

from app.llm.cache import load_fixture, save_fixture


class LLMResponse(BaseModel):
    content: dict[str, Any]
    model: str
    source: str  # "live" | "cache" — surfaced in the UI/audit log, never hidden


class LLMClient(abc.ABC):
    @abc.abstractmethod
    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
        cache_key: str,
    ) -> LLMResponse:
        """Return a response conforming to response_schema (JSON schema)."""


class AnthropicClient(LLMClient):
    """Live calls — used during development on a machine with real API access."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-5"):
        import anthropic

        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
        cache_key: str,
    ) -> LLMResponse:
        required_fields = response_schema.get("required", [])
        last_error: Exception | None = None

        # Forced tool-use isn't a hard schema guarantee — occasionally the
        # model returns a tool_use.input missing a required field (seen in
        # practice: claims/citations arrays collapsed into the adjacent
        # string field, with stray tag-like text appended). That's silent
        # data corruption downstream (frontend .map() on undefined, citation
        # validator treating a real argument as having zero claims) unless
        # it's caught here. One bounded retry, then fail loudly rather than
        # ever caching or returning a response missing required fields.
        for attempt in range(3):
            message = await self._client.messages.create(
                model=self._model,
                max_tokens=6144,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                tools=[
                    {
                        "name": "emit_result",
                        "description": "Return the structured investigation result.",
                        "input_schema": response_schema,
                    }
                ],
                tool_choice={"type": "tool", "name": "emit_result"},
            )
            tool_use = next(b for b in message.content if b.type == "tool_use")
            missing = [f for f in required_fields if f not in tool_use.input]
            if not missing:
                response = LLMResponse(content=tool_use.input, model=self._model, source="live")
                # Every live response is persisted as a fixture — this is
                # what makes offline replay mode possible later without a
                # separate recording step.
                save_fixture(cache_key, response.model_dump())
                return response
            last_error = ValueError(f"Model response for {cache_key!r} missing required field(s): {missing} (attempt {attempt + 1}/3)")

        raise RuntimeError(str(last_error))


class EnterpriseGatewayClient(LLMClient):
    """Stub for the bank's internal LLM gateway. Fill in base_url/auth once
    access is confirmed — most enterprise gateways expose an OpenAI-compatible
    REST surface behind an API-key header, so this is the expected shape.
    Deliberately fails loudly rather than silently falling back, so a missing
    gateway config is caught in setup, not mid-demo.
    """

    def __init__(self, base_url: str, api_key: str, model: str):
        self._base_url = base_url
        self._api_key = api_key
        self._model = model

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
        cache_key: str,
    ) -> LLMResponse:
        raise NotImplementedError(
            "Fill in once the bank's gateway endpoint/auth contract is known. "
            "Until then, set LLM_PROVIDER=cache or LLM_PROVIDER=anthropic."
        )


class CachedReplayClient(LLMClient):
    """Zero-network mode. Replays a fixture recorded by AnthropicClient during
    development. Raises clearly (not a silent empty result) if a case wasn't
    pre-recorded — surfaces gaps in demo-case coverage before the demo, not during.
    """

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
        cache_key: str,
    ) -> LLMResponse:
        fixture = load_fixture(cache_key)
        if fixture is None:
            raise RuntimeError(
                f"No cached response for '{cache_key}'. Replay mode only covers "
                "pre-recorded demo cases — record it first by running this case "
                "once with LLM_PROVIDER=anthropic on a machine with API access."
            )
        fixture["source"] = "cache"
        return LLMResponse(**fixture)


def get_llm_client() -> LLMClient:
    provider = os.environ.get("LLM_PROVIDER", "cache")
    if provider == "anthropic":
        api_key = os.environ["ANTHROPIC_API_KEY"]
        return AnthropicClient(api_key=api_key)
    if provider == "gateway":
        return EnterpriseGatewayClient(
            base_url=os.environ["GATEWAY_BASE_URL"],
            api_key=os.environ["GATEWAY_API_KEY"],
            model=os.environ.get("GATEWAY_MODEL", "default"),
        )
    if provider == "cache":
        return CachedReplayClient()
    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}")
