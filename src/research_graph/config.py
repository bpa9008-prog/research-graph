"""Настройки приложения на базе pydantic-settings."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RG_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    github_token: str | None = Field(default=None)
    data_dir: Path = Field(default=Path("data"))
    log_level: str = Field(default="INFO")
    request_timeout: float = Field(default=30.0, ge=1.0, le=300.0)
    max_concurrency: int = Field(default=4, ge=1, le=64)

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"log_level должен быть одним из {sorted(allowed)}, получено: {v!r}")
        return v_upper

    @field_validator("github_token")
    @classmethod
    def _validate_token(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v or v.lower() in {"changeme", "none", "null", "your_token_here"}:
            return None
        return v

    @property
    def has_token(self) -> bool:
        return bool(self.github_token)

    def masked_token(self) -> str:
        if not self.github_token:
            return "<not set>"
        token = self.github_token
        if len(token) <= 8:
            return "*" * len(token)
        prefix_part = f"{token.split('_', 1)[0]}_" if "_" in token else token[:3]
        return f"{prefix_part}****{token[-4:]}"

    def ensure_data_dir(self) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def _reset_settings_cache() -> None:
    global _settings
    _settings = None
