"""Инициализация логирования (в stderr)."""

from __future__ import annotations

import contextlib
import logging
import sys

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_NOISY_LOGGERS = ("urllib3", "httpx", "httpcore", "requests", "asyncio", "charset_normalizer")


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()

    for handler in list(root.handlers):
        root.removeHandler(handler)
        with contextlib.suppress(Exception):
            handler.close()

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT))
    root.addHandler(handler)

    level_value = logging.getLevelName(level.upper()) if isinstance(level, str) else int(level)
    if not isinstance(level_value, int):
        level_value = logging.INFO
    root.setLevel(level_value)

    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
