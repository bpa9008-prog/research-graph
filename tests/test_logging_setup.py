"""Тесты настройки логирования."""

from __future__ import annotations

import logging

from _pytest.capture import CaptureFixture

from research_graph.logging_setup import setup_logging


def test_no_duplicate_handlers() -> None:
    """Повторный вызов setup_logging не задваивает хендлеры."""
    setup_logging("INFO")
    setup_logging("DEBUG")
    assert len(logging.getLogger().handlers) == 1


def test_logs_go_to_stderr(capsys: CaptureFixture[str]) -> None:
    """Логи идут в stderr, а не в stdout."""
    setup_logging("INFO")
    logging.getLogger("research_graph.test").info("hello")
    captured = capsys.readouterr()
    assert "hello" in captured.err
    assert "hello" not in captured.out


def test_accepts_lowercase_level() -> None:
    """'debug' нормализуется к DEBUG."""
    setup_logging("debug")
    assert logging.getLogger().level == logging.DEBUG


def test_bad_level_falls_back_to_info() -> None:
    """Невалидный уровень не ломает setup_logging — фолбэк на INFO."""
    setup_logging("BOGUS")
    assert logging.getLogger().level == logging.INFO


def test_noisy_libraries_are_throttled() -> None:
    """Сторонние болтливые логгеры приглушены до WARNING."""
    setup_logging("DEBUG")
    for name in ("urllib3", "httpx", "httpcore", "requests", "asyncio", "charset_normalizer"):
        assert logging.getLogger(name).level == logging.WARNING
