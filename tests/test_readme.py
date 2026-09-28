"""Проверка консистентности README и кода.

Тесты ловят две типичные ошибки:
1. README упоминает команду CLI, которой больше нет.
2. README упоминает переменную RG_*, которой нет в Settings.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from research_graph.config import Settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
README_PATH = PROJECT_ROOT / "README.md"


@pytest.fixture(scope="module")
def readme_text() -> str:
    return README_PATH.read_text(encoding="utf-8")


def test_readme_exists() -> None:
    assert README_PATH.exists(), "README.md отсутствует"


def test_readme_mentions_real_cli_commands(readme_text: str) -> None:
    """Все команды вида `rg <subcommand>` из README должны существовать в app."""
    from typer.main import get_command

    from research_graph.cli import app

    typer_app = get_command(app)
    known = set(typer_app.commands.keys())  # type: ignore[attr-defined]

    # Ищем в тексте вхождения "rg <word>" — в блоках кода и инлайн
    mentioned = set(re.findall(r"\brg\s+([a-z][a-z0-9-]+)", readme_text))

    # Отфильтровываем известные не-команды (пути, флаги, примеры)
    ignored = {"--help", "--verbose", "-v"}
    mentioned -= ignored

    unknown = mentioned - known
    assert not unknown, f"README упоминает несуществующие команды rg: {sorted(unknown)}"


def test_readme_mentions_real_env_vars(readme_text: str) -> None:
    """Все переменные RG_* из README должны присутствовать в Settings."""
    env_vars = set(re.findall(r"\bRG_[A-Z_]+", readme_text))

    known = {f"RG_{name.upper()}" for name in Settings.model_fields}

    unknown = env_vars - known
    assert not unknown, f"README упоминает неизвестные переменные: {sorted(unknown)}"


def test_readme_mentions_uv_sync(readme_text: str) -> None:
    """В README должна быть инструкция установки через uv sync."""
    assert "uv sync" in readme_text
