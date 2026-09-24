"""LLM Config API — Sprint 6: BYOK + Local LLM management.

Endpoints:
  GET    /api/v1/llm-config              — list user's LLM configurations
  POST   /api/v1/llm-config              — create new config
  GET    /api/v1/llm-config/{config_id}  — get single config (decrypted key not returned)
  PUT    /api/v1/llm-config/{config_id}  — update config
  DELETE /api/v1/llm-config/{config_id}  — delete config
  POST   /api/v1/llm-config/{config_id}/test — test connectivity
  GET    /api/v1/llm/models              — list available Ollama models
"""

from __future__ import annotations

import os
from typing import Annotated, Any

from backend.auth.schemas import CurrentUserId
from backend.database import get_session
from backend.models import LLMConfig
from backend.security import decrypt_api_key, encrypt_api_key
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="", tags=["llm-config"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class LLMConfigCreate(BaseModel):
    """Request to create a new LLM configuration."""

    provider: str = Field(
        description="Provider slug: openai, anthropic, ollama, custom"
    )
    base_url: str | None = Field(
        default=None, description="Custom base URL for Ollama or custom providers"
    )
    api_key: str | None = Field(
        default=None, description="API key (will be encrypted at rest)"
    )
    model_name: str = Field(description="Model identifier, e.g., gpt-4o-mini, llama3.1:70b")
    is_active: bool = Field(
        default=True, description="Whether this is the active config for generation"
    )


class LLMConfigUpdate(BaseModel):
    """Request to update an LLM configuration."""

    provider: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    model_name: str | None = None
    is_active: bool | None = None


class LLMConfigResponse(BaseModel):
    """Response model for LLM config (never returns decrypted API key)."""

    id: str
    provider: str
    base_url: str | None
    model_name: str
    is_active: bool
    has_api_key: bool
    created_at: str
    updated_at: str

    @classmethod
    def from_model(cls, config: LLMConfig) -> "LLMConfigResponse":
        return cls(
            id=str(config.id),
            provider=config.provider,
            base_url=config.base_url,
            model_name=config.model_name,
            is_active=config.is_active,
            has_api_key=bool(config.api_key_encrypted),
            created_at=config.created_at.isoformat() if config.created_at else "",
            updated_at=config.updated_at.isoformat() if config.updated_at else "",
        )


class LLMConfigTestRequest(BaseModel):
    """Request to test an LLM config connectivity."""

    prompt: str = Field(
        default="Hello! Reply with a single word: 'OK'.",
        description="Test prompt to send",
    )


class LLMConfigTestResponse(BaseModel):
    """Response from connectivity test."""

    success: bool
    message: str
    latency_ms: int | None = None
    response_preview: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("", response_model=list[LLMConfigResponse])
async def list_llm_configs(
    current_user_id: CurrentUserId,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[LLMConfigResponse]:
    """List all LLM configurations for the current user."""
    stmt = select(LLMConfig).where(LLMConfig.user_id == current_user_id).order_by(LLMConfig.created_at.desc())
    result = await session.execute(stmt)
    configs = result.scalars().all()
    return [LLMConfigResponse.from_model(c) for c in configs]


@router.post("", response_model=LLMConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_llm_config(
    req: LLMConfigCreate,
    current_user_id: CurrentUserId,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LLMConfigResponse:
    """Create a new LLM configuration."""
    # Validate provider
    valid_providers = {"openai", "anthropic", "ollama", "custom", "litellm"}
    if req.provider not in valid_providers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider '{req.provider}'. Valid: {', '.join(sorted(valid_providers))}",
        )

    # If setting as active, deactivate others
    if req.is_active:
        await _deactivate_user_configs(session, current_user_id)

    # Encrypt API key if provided
    encrypted_key = encrypt_api_key(req.api_key) if req.api_key else None

    config = LLMConfig(
        user_id=current_user_id,
        provider=req.provider,
        base_url=req.base_url,
        api_key_encrypted=encrypted_key,
        model_name=req.model_name,
        is_active=req.is_active,
    )
    session.add(config)
    await session.commit()
    await session.refresh(config)
    return LLMConfigResponse.from_model(config)


# ── Ollama Models ───────────────────────────────────────────────────────


class OllamaModel(BaseModel):
    """A single model returned by Ollama's /api/tags."""
    name: str
    model: str
    modified_at: str | None = None
    size: int | None = None
    details: dict[str, Any] | None = None
    capabilities: list[str] | None = None


class OllamaModelsResponse(BaseModel):
    """Response from the Ollama models endpoint."""
    models: list[OllamaModel]


@router.get("/models", response_model=OllamaModelsResponse)
async def list_ollama_models() -> OllamaModelsResponse:
    """List available models from the local Ollama instance.

    Calls Ollama's /api/tags endpoint and returns model names.
    Returns an empty list if Ollama is not reachable.
    """
    import httpx

    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{base_url}/api/tags")
            r.raise_for_status()
            data = r.json()
            raw_models = data.get("models", [])
            return OllamaModelsResponse(
                models=[OllamaModel(**m) for m in raw_models]
            )
    except Exception:
        return OllamaModelsResponse(models=[])



@router.get("/{config_id}", response_model=LLMConfigResponse)
async def get_llm_config(
    config_id: str,
    current_user_id: CurrentUserId,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LLMConfigResponse:
    """Get a single LLM configuration (without decrypted API key)."""
    stmt = select(LLMConfig).where(LLMConfig.id == config_id, LLMConfig.user_id == current_user_id)
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status_code=404, detail="LLM config not found")
    return LLMConfigResponse.from_model(config)


@router.put("/{config_id}", response_model=LLMConfigResponse)
async def update_llm_config(
    config_id: str,
    req: LLMConfigUpdate,
    current_user_id: CurrentUserId,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LLMConfigResponse:
    """Update an LLM configuration."""
    stmt = select(LLMConfig).where(LLMConfig.id == config_id, LLMConfig.user_id == current_user_id)
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status_code=404, detail="LLM config not found")

    # Validate provider if changed
    if req.provider is not None:
        valid_providers = {"openai", "anthropic", "ollama", "custom", "litellm"}
        if req.provider not in valid_providers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider '{req.provider}'. Valid: {', '.join(sorted(valid_providers))}",
            )
        config.provider = req.provider

    # If setting as active, deactivate others
    if req.is_active is True:
        await _deactivate_user_configs(session, current_user_id)
        config.is_active = True
    elif req.is_active is False:
        config.is_active = False

    if req.base_url is not None:
        config.base_url = req.base_url
    if req.model_name is not None:
        config.model_name = req.model_name
    if req.api_key is not None:
        config.api_key_encrypted = encrypt_api_key(req.api_key) if req.api_key else None

    await session.commit()
    await session.refresh(config)
    return LLMConfigResponse.from_model(config)


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_config(
    config_id: str,
    current_user_id: CurrentUserId,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Delete an LLM configuration."""
    stmt = select(LLMConfig).where(LLMConfig.id == config_id, LLMConfig.user_id == current_user_id)
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status_code=404, detail="LLM config not found")

    await session.delete(config)
    await session.commit()


@router.post("/{config_id}/test", response_model=LLMConfigTestResponse)
async def test_llm_config(
    config_id: str,
    req: LLMConfigTestRequest,
    current_user_id: CurrentUserId,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LLMConfigTestResponse:
    """Test connectivity for an LLM configuration."""
    import time

    from backend.llm.adapter import GenerationError, get_adapter_class
    from backend.llm.adapters import LiteLLMAdapter, OllamaAdapter, OpenAIAdapter

    stmt = select(LLMConfig).where(LLMConfig.id == config_id, LLMConfig.user_id == current_user_id)
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(status_code=404, detail="LLM config not found")

    # Decrypt API key if present
    api_key = decrypt_api_key(config.api_key_encrypted) if config.api_key_encrypted else None

    try:
        adapter_cls = get_adapter_class(config.provider)
        if adapter_cls is None:
            return LLMConfigTestResponse(
                success=False,
                message=f"Unknown provider '{config.provider}'",
            )

        adapter = adapter_cls(api_key=api_key, base_url=config.base_url)

        # Use a minimal schema for testing
        test_schema = {
            "type": "object",
            "properties": {"reply": {"type": "string"}},
            "required": ["reply"],
        }

        start = time.perf_counter()
        result_data = await adapter.generate(
            prompt=req.prompt,
            schema=test_schema,
            model=config.model_name,
            max_retries=1,  # Quick test, fewer retries
        )
        latency_ms = int((time.perf_counter() - start) * 1000)

        return LLMConfigTestResponse(
            success=True,
            message=f"Connected successfully to {config.provider}/{config.model_name}",
            latency_ms=latency_ms,
            response_preview=str(result_data)[:200],
        )

    except GenerationError as exc:
        return LLMConfigTestResponse(
            success=False,
            message=f"LLM error: {exc}",
        )
    except Exception as exc:
        return LLMConfigTestResponse(
            success=False,
            message=f"Connection failed: {exc}",
        )


# ── Helpers ───────────────────────────────────────────────────────────────


async def _deactivate_user_configs(session: AsyncSession, user_id: str) -> None:
    """Set is_active=False for all user's LLM configs."""
    stmt = select(LLMConfig).where(LLMConfig.user_id == user_id, LLMConfig.is_active == True)
    result = await session.execute(stmt)
    for config in result.scalars().all():
        config.is_active = False
    await session.commit()