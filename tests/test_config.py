"""Тесты настроек и валидации."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from research_graph.config import Settings, _reset_settings_cache, get_settings


def test_defaults() -> None:
    """Без переменных окружения Settings имеет ожидаемые значения."""
    s = Settings()
    assert s.github_token is None
    assert s.data_dir == Path("data")
    assert s.log_level == "INFO"
    assert s.request_timeout == 30.0
    assert s.max_concurrency == 4
    assert s.has_token is False


def test_get_settings_returns_instance() -> None:
    """get_settings() возвращает экземпляр Settings."""
    _reset_settings_cache()
    s = get_settings()
    assert isinstance(s, Settings)


def test_settings_read_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RG_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("RG_MAX_CONCURRENCY", "16")
    s = Settings()
    assert s.log_level == "DEBUG"
    assert s.max_concurrency == 16


def test_log_level_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    """log_level приводится к верхнему регистру валидатором."""
    monkeypatch.setenv("RG_LOG_LEVEL", "debug")
    s = Settings()
    assert s.log_level == "DEBUG"


def test_rejects_zero_concurrency() -> None:
    with pytest.raises(ValidationError):
        Settings(max_concurrency=0)


def test_rejects_huge_concurrency() -> None:
    with pytest.raises(ValidationError):
        Settings(max_concurrency=65)


def test_rejects_small_timeout() -> None:
    with pytest.raises(ValidationError):
        Settings(request_timeout=0.5)


def test_rejects_huge_timeout() -> None:
    with pytest.raises(ValidationError):
        Settings(request_timeout=500.0)


def test_rejects_invalid_concurrency(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RG_MAX_CONCURRENCY", "0")
    with pytest.raises(ValidationError):
        Settings()


def test_rejects_invalid_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RG_LOG_LEVEL", "TRACE")
    with pytest.raises(ValidationError):
        Settings()


def test_token_masking_full() -> None:
    """Полный токен маскируется по шаблону <prefix>_****<last4>."""
    s = Settings(github_token="ghp_1234567890abcdef")
    assert s.masked_token() == "ghp_****cdef"
    assert "1234567890" not in s.masked_token()


def test_token_masking_short() -> None:
    """Короткий токен маскируется целиком."""
    s = Settings(github_token="abc")
    assert s.masked_token() == "***"


def test_token_placeholder_becomes_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Плейсхолдеры из шаблонов окружения превращаются в None."""
    monkeypatch.setenv("RG_GITHUB_TOKEN", "changeme")
    s = Settings()
    assert s.github_token is None
    assert s.has_token is False


def test_ensure_data_dir_creates_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = tmp_path / "nested" / "research-graph"
    s = Settings(data_dir=target)
    assert not target.exists()
    created = s.ensure_data_dir()
    assert created == target
    assert target.is_dir()


def test_masked_token_when_not_set() -> None:
    """masked_token() без токена возвращает '<not set>'."""
    s = Settings()
    assert s.masked_token() == "<not set>"


def test_token_masking_without_prefix() -> None:
    """Токен без подчёркивания: маска сохраняет первые 3 и последние 4 символа."""
    s = Settings(github_token="abcdefghij1234")
    assert s.masked_token() == "abc****1234"


def test_get_settings_is_cached() -> None:
    """Повторный вызов get_settings() без сброса кэша возвращает тот же объект."""
    _reset_settings_cache()
    first = get_settings()
    second = get_settings()
    assert first is second
