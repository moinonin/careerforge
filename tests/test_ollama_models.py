"""Ollama models endpoint tests."""

import pytest


def test_list_ollama_models_endpoint_registered() -> None:
    """The /models endpoint is registered in the llm-config router."""
    from backend.api.routes.llm_config import router
    route_paths = [getattr(r, "path", getattr(r, "name", str(r))) for r in router.routes]
    assert "/models" in route_paths


def test_ollama_models_function_exists() -> None:
    """The list_ollama_models function is defined and callable."""
    from backend.api.routes.llm_config import list_ollama_models, OllamaModelsResponse
    assert callable(list_ollama_models)
    assert issubclass(OllamaModelsResponse, object)