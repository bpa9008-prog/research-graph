"""Общие фикстуры для тестов.

Ключевая задача — изолировать тесты от локального .env, от реальных
переменных RG_* в окружении и от кэша singleton get_settings().
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from research_graph.config import _reset_settings_cache


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Изолировать каждый тест.

    - удаляет все переменные RG_* из окружения;
    - переводит cwd в tmp_path, чтобы Settings не подхватил ../.env;
    - сбрасывает кэш singleton get_settings(), иначе Settings будет
      переиспользоваться между тестами и не увидит новый env.
    """
    for key in list(os.environ):
        if key.startswith("RG_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)
    _reset_settings_cache()
    yield
    _reset_settings_cache()
