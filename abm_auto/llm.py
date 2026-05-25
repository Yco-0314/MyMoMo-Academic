"""
LLM provider abstraction.

Supports two backends behind a single interface:
  - "anthropic"  → official Anthropic SDK (Claude)
  - "deepseek"   → OpenAI-compatible SDK pointed at api.deepseek.com

The choice is driven by env var LLM_PROVIDER (default "anthropic").
Switching provider only requires updating .env — no code changes downstream.

Usage:
    from abm_auto.llm import make_client
    client = make_client(provider="deepseek", api_key="sk-...", timeout=300)
    text = client.create(model="deepseek-chat", max_tokens=2048,
                         system="You are ...", user="Hello")

The client also exposes provider-specific exception classes for retry logic:
    except client.RateLimitError: ...
    except client.BadRequestError: ...
    except client.ConnectionErrors: ...    # tuple
"""
from __future__ import annotations

from typing import Literal


class LLMClient:
    """Single-turn LLM client; abstracts over Anthropic vs OpenAI-compat APIs."""

    def __init__(
        self,
        provider: Literal["anthropic", "deepseek"],
        api_key: str,
        base_url: str | None = None,
        timeout: float = 300.0,
    ):
        if not api_key:
            raise ValueError(
                f"{provider.upper()}_API_KEY is empty. "
                f"Set it in .env or environment."
            )
        self.provider = provider

        if provider == "anthropic":
            import anthropic
            self._sdk = anthropic
            self._client = anthropic.Anthropic(
                api_key=api_key, base_url=base_url, timeout=timeout,
            )
        elif provider == "deepseek":
            import openai
            self._sdk = openai
            self._client = openai.OpenAI(
                api_key=api_key,
                base_url=base_url or "https://api.deepseek.com/v1",
                timeout=timeout,
            )
        else:
            raise ValueError(f"Unknown provider: {provider!r}")

    # ── unified create() ────────────────────────────────────────────────────

    def create(
        self,
        model: str,
        max_tokens: int,
        system: str,
        user: str,
    ) -> str:
        """Send a single-turn (system + user) request. Returns response text."""
        if self.provider == "anthropic":
            r = self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return r.content[0].text

        # deepseek (OpenAI-compatible)
        r = self._client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return r.choices[0].message.content or ""

    # ── provider-specific exception types (for retry logic) ────────────────

    @property
    def RateLimitError(self):
        return self._sdk.RateLimitError

    @property
    def BadRequestError(self):
        return self._sdk.BadRequestError

    @property
    def ConnectionErrors(self) -> tuple:
        """Tuple of (ConnectionError, TimeoutError) classes."""
        return (self._sdk.APIConnectionError, self._sdk.APITimeoutError)


def make_client(
    provider: str,
    api_key: str,
    base_url: str | None = None,
    timeout: float = 300.0,
) -> LLMClient:
    """Factory: build an LLMClient for the given provider."""
    return LLMClient(provider=provider, api_key=api_key,
                     base_url=base_url, timeout=timeout)
