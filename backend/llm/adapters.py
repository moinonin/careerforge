"""Concrete LLM adapters — OpenAI, LiteLLM, Ollama.

Each adapter is registered with ``@register_adapter("...")`` at module load
so ``get_adapter_class("openai")`` etc. resolve without runtime imports.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from backend.llm.adapter import (
    GenerationError,
    LLMAdapter,
    _build_retry_prompt,
    _validate_against_schema,
    register_adapter,
)

# ═══════════════════════════════════════════════════════════════════════════════
# OpenAI
# ═══════════════════════════════════════════════════════════════════════════════

@register_adapter("openai")
class OpenAIAdapter(LLMAdapter):
    """Calls OpenAI Chat Completions with ``response_format=json_object``."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        super().__init__(api_key=api_key, base_url=base_url)
        import openai

        self._client = openai.AsyncOpenAI(
            api_key=api_key or os.environ.get("OPENAI_API_KEY", ""),
            base_url=base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )

    async def generate(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        model: str | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        target_model = model or os.environ.get("LLM_MODEL", "gpt-4o-mini")
        last_error: Exception | None = None

        # Extract sub-schemas from the combined schema for nested validation
        cv_sub_schema: dict[str, Any] = schema.get("properties", {}).get("cv", {})
        cl_sub_schema: dict[str, Any] = schema.get("properties", {}).get("cover_letter", {})

        for attempt in range(1, max_retries + 1):
            try:
                response = await self._client.chat.completions.create(
                    model=target_model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                )
                content = response.choices[0].message.content
                if content is None:
                    raise GenerationError("Empty response from OpenAI")

                parsed: dict[str, Any] = json.loads(content)

                # Validate top-level structure (cv + cover_letter keys)
                ok, msg = _validate_against_schema(parsed, schema)
                if not ok:
                    raise ValueError(msg)

                # Validate sub-objects — these failures also trigger retry
                if cv_sub_schema:
                    cv_data = parsed.get("cv", {})
                    ok_cv, msg_cv = _validate_against_schema(cv_data, cv_sub_schema)
                    if not ok_cv:
                        raise ValueError(f"CV validation: {msg_cv}")

                if cl_sub_schema:
                    cl_data = parsed.get("cover_letter", {})
                    ok_cl, msg_cl = _validate_against_schema(cl_data, cl_sub_schema)
                    if not ok_cl:
                        raise ValueError(f"Cover letter validation: {msg_cl}")

                return parsed

            except (json.JSONDecodeError, ValueError, GenerationError) as exc:
                last_error = exc
                if attempt < max_retries:
                    corrected = _build_retry_prompt(prompt, schema, str(exc))
                    prompt = corrected
                    continue
                break

        raise GenerationError(
            f"OpenAI generation failed after {max_retries} attempts",
            last_error=last_error,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# LiteLLM (covers Anthropic, DeepSeek, Gemini, Ollama, AWS Bedrock, …)
# ═══════════════════════════════════════════════════════════════════════════════

@register_adapter("litellm")
class LiteLLMAdapter(LLMAdapter):
    """Uses LiteLLM's unified ``completion`` call.

    The *provider* is selected via the ``LITELLM_MODEL`` env var or the
    *model* kwarg using LiteLLM's ``provider/model`` notation, e.g.
    ``"anthropic/claude-3-5-sonnet-20241022"`` or ``"gpt-4o-mini"``.
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        super().__init__(api_key=api_key, base_url=base_url)

        # LiteLLM reads API keys from env vars automatically; we pass nothing
        # here and let it resolve OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.
        self._config: dict[str, Any] = {}
        if base_url:
            self._config["custom_host"] = base_url

    async def generate(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        model: str | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        import litellm

        target_model = model or os.environ.get("LITELLM_MODEL", "gpt-4o-mini")
        last_error: Exception | None = None

        # Extract sub-schemas from the combined schema for nested validation
        cv_sub_schema: dict[str, Any] = schema.get("properties", {}).get("cv", {})
        cl_sub_schema: dict[str, Any] = schema.get("properties", {}).get("cover_letter", {})

        for attempt in range(1, max_retries + 1):
            try:
                response = await litellm.acompletion(
                    model=target_model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                    **self._config,
                )
                # LiteLLM returns the OpenAI-format response
                content = response.choices[0].message.content
                if content is None:
                    raise GenerationError("Empty response from LiteLLM")

                parsed: dict[str, Any] = json.loads(content)

                # Validate top-level structure (cv + cover_letter keys)
                ok, msg = _validate_against_schema(parsed, schema)
                if not ok:
                    raise ValueError(msg)

                # Validate sub-objects — these failures also trigger retry
                if cv_sub_schema:
                    cv_data = parsed.get("cv", {})
                    ok_cv, msg_cv = _validate_against_schema(cv_data, cv_sub_schema)
                    if not ok_cv:
                        raise ValueError(f"CV validation: {msg_cv}")

                if cl_sub_schema:
                    cl_data = parsed.get("cover_letter", {})
                    ok_cl, msg_cl = _validate_against_schema(cl_data, cl_sub_schema)
                    if not ok_cl:
                        raise ValueError(f"Cover letter validation: {msg_cl}")

                return parsed

            except (json.JSONDecodeError, ValueError, GenerationError) as exc:
                last_error = exc
                if attempt < max_retries:
                    corrected = _build_retry_prompt(prompt, schema, str(exc))
                    prompt = corrected
                    continue
                break

        raise GenerationError(
            f"LiteLLM generation failed after {max_retries} attempts",
            last_error=last_error,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Ollama (direct HTTP — for explicit localhost / custom Ollama setups)
# ═══════════════════════════════════════════════════════════════════════════════

@register_adapter("ollama")
class OllamaAdapter(LLMAdapter):
    """Calls a local Ollama instance via its HTTP API.

    Default base URL: ``http://localhost:11434`` (overridable via
    ``OLLAMA_BASE_URL`` env var or the *base_url* constructor arg).
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        super().__init__(api_key=api_key, base_url=base_url)
        self._base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self._http = httpx.AsyncClient(timeout=120.0)

    async def generate(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        model: str | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        target_model = model or os.environ.get("OLLAMA_MODEL", "llama3.1:70b")
        last_error: Exception | None = None

        # Extract sub-schemas from the combined schema for nested validation
        cv_sub_schema: dict[str, Any] = schema.get("properties", {}).get("cv", {})
        cl_sub_schema: dict[str, Any] = schema.get("properties", {}).get("cover_letter", {})

        for attempt in range(1, max_retries + 1):
            try:
                payload: dict[str, Any] = {
                    "model": target_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                }
                # Ollama's `/api/chat` doesn't support response_format json_object
                # directly — we instruct the model in the prompt instead.
                payload["messages"][0]["content"] = (
                    f"{prompt}\n\n"
                    f"IMPORTANT: Respond with ONLY a valid JSON object matching the "
                    f"required schema. No markdown fences, no extra text, no commentary."
                )

                resp = await self._http.post(
                    f"{self._base_url}/api/chat",
                    json=payload,
                )
                resp.raise_for_status()
                body = resp.json()

                content = body.get("message", {}).get("content", "")
                if content is None:
                    raise GenerationError("Empty response from Ollama")

                # Ollama may wrap in markdown fences — strip them
                content = content.strip()
                if content.startswith("```"):
                    # remove ```json ... ``` or ``` ... ```
                    lines = content.splitlines()
                    # find first non-fence line
                    start = 0
                    while start < len(lines) and lines[start].strip().startswith("```"):
                        start += 1
                    end = len(lines)
                    while end > start and lines[end - 1].strip().startswith("```"):
                        end -= 1
                    content = "\n".join(lines[start:end]).strip()

                parsed: dict[str, Any] = json.loads(content)

                # Validate top-level structure (cv + cover_letter keys)
                ok, msg = _validate_against_schema(parsed, schema)
                if not ok:
                    raise ValueError(msg)

                # Validate sub-objects — these failures also trigger retry
                if cv_sub_schema:
                    cv_data = parsed.get("cv", {})
                    ok_cv, msg_cv = _validate_against_schema(cv_data, cv_sub_schema)
                    if not ok_cv:
                        raise ValueError(f"CV validation: {msg_cv}")

                if cl_sub_schema:
                    cl_data = parsed.get("cover_letter", {})
                    ok_cl, msg_cl = _validate_against_schema(cl_data, cl_sub_schema)
                    if not ok_cl:
                        raise ValueError(f"Cover letter validation: {msg_cl}")

                return parsed

            except (json.JSONDecodeError, ValueError, GenerationError, httpx.HTTPError) as exc:
                last_error = exc
                if attempt < max_retries:
                    corrected = _build_retry_prompt(prompt, schema, str(exc))
                    prompt = corrected
                    continue
                break

        raise GenerationError(
            f"Ollama generation failed after {max_retries} attempts",
            last_error=last_error,
        )

    async def close(self) -> None:
        await self._http.aclose()
