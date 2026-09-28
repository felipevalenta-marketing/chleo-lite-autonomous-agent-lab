"""Environment configuration for the Chleo Lite prototype."""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_CHROMA_PERSIST_DIRECTORY = "./chroma_db"


def _read_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class ChleoConfig(BaseModel):
    """Validated runtime configuration for local development."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    openai_api_key: str | None = Field(default=None)
    openai_model: str = Field(default=DEFAULT_OPENAI_MODEL)
    chroma_persist_directory: str = Field(default=DEFAULT_CHROMA_PERSIST_DIRECTORY)

    @property
    def has_openai_api_key(self) -> bool:
        return bool(self.openai_api_key)


def load_config() -> ChleoConfig:
    """Load environment variables and build the runtime configuration."""

    load_dotenv(override=False)
    return ChleoConfig(
        openai_api_key=_read_env("OPENAI_API_KEY"),
        openai_model=_read_env("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL,
        chroma_persist_directory=_read_env("CHROMA_PERSIST_DIRECTORY")
        or DEFAULT_CHROMA_PERSIST_DIRECTORY,
    )


@lru_cache(maxsize=1)
def get_config() -> ChleoConfig:
    """Return a cached configuration instance for application use."""

    return load_config()
