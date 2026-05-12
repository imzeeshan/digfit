"""
Server-side Ollama HTTP API helpers.

Default model is MedGemma (`OLLAMA_MODEL`, e.g. `medgemma:4b`). Pull it locally first, e.g.:

    ollama pull medgemma:4b
"""

from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING, Any

import ollama
from django.conf import settings

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser


def get_client(host: str | None = None) -> ollama.Client:
    return ollama.Client(host=(host or '').strip() or settings.OLLAMA_HOST)


def _model(model: str | None) -> str:
    return model if model is not None else settings.OLLAMA_MODEL


def _ollama_host_model_for_user(user: 'AbstractBaseUser') -> tuple[str, str]:
    """Resolve host and model from UserSettings when present."""
    if not getattr(user, 'is_authenticated', False):
        return settings.OLLAMA_HOST, settings.OLLAMA_MODEL
    from apps.dashboard.models import UserSettings

    try:
        us = UserSettings.objects.get(user=user)
    except UserSettings.DoesNotExist:
        return settings.OLLAMA_HOST, settings.OLLAMA_MODEL
    return us.get_effective_ollama_host(), us.get_effective_ollama_model()


def chat(
    messages: Sequence[dict[str, Any]],
    *,
    model: str | None = None,
    host: str | None = None,
    stream: bool = False,
) -> Any | Iterator[Any]:
    """Chat completion (`messages` uses Ollama roles: user, assistant, system)."""
    client = get_client(host)
    return client.chat(model=_model(model), messages=list(messages), stream=stream)


def chat_for_user(
    user: 'AbstractBaseUser',
    messages: Sequence[dict[str, Any]],
    *,
    stream: bool = False,
) -> Any | Iterator[Any]:
    """Chat using the signed-in user's Ollama host and model from dashboard settings."""
    host, model = _ollama_host_model_for_user(user)
    return chat(messages, model=model, host=host, stream=stream)


def generate(
    prompt: str,
    *,
    model: str | None = None,
    host: str | None = None,
    stream: bool = False,
) -> Any | Iterator[Any]:
    """Single-string prompt completion."""
    client = get_client(host)
    return client.generate(model=_model(model), prompt=prompt, stream=stream)


def generate_for_user(
    user: 'AbstractBaseUser',
    prompt: str,
    *,
    stream: bool = False,
) -> Any | Iterator[Any]:
    host, model = _ollama_host_model_for_user(user)
    return generate(prompt, model=model, host=host, stream=stream)
