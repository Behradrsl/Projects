"""Provider-neutral connection settings with explicit legacy compatibility."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import dotenv

DEFAULT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
LEGACY_MODEL = "gpt-4.1-mini"


@dataclass(frozen=True)
class Connection:
    api_key: str = field(repr=False)
    model: str
    base_url: str | None


def _setting(name: str, legacy: str, default: str) -> str:
    # Presence matters: an explicitly blank canonical value disables fallback.
    if name in os.environ:
        return os.environ[name].strip()
    if legacy in os.environ:
        return os.environ[legacy].strip()
    return default


def load_connection(root: Path) -> Connection:
    """Load .env without replacing process settings; never log credentials.

    New configurations default to OpenRouter. A legacy-only OpenAI configuration
    keeps its previous direct-OpenAI defaults, including when it has only a key.
    """
    dotenv.load_dotenv(root / ".env", override=False)
    fields = ("API_KEY", "MODEL", "BASE_URL")
    legacy_only = any(f"OPENAI_{name}" in os.environ for name in fields) and not any(
        f"LLM_{name}" in os.environ for name in fields
    )
    legacy_model_selected = "LLM_MODEL" not in os.environ and "OPENAI_MODEL" in os.environ
    model_default = LEGACY_MODEL if legacy_only else DEFAULT_MODEL
    url_default = "" if legacy_only or legacy_model_selected else DEFAULT_BASE_URL
    model = _setting("LLM_MODEL", "OPENAI_MODEL", model_default)
    if legacy_model_selected and not model:
        # Legacy setup treated an empty model as its direct-OpenAI default.
        model = LEGACY_MODEL
    return Connection(
        api_key=_setting("LLM_API_KEY", "OPENAI_API_KEY", ""),
        model=model,
        base_url=_setting("LLM_BASE_URL", "OPENAI_BASE_URL", url_default) or None,
    )
