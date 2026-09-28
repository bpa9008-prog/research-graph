# research-graph

Инструмент для сбора и обработки данных о GitHub-репозиториях.
Проект развивается как учебный пайплайн: снимок сырых данных -> Bronze-слой ->
Silver/Gold. На текущем этапе (ЛР1) реализованы конфигурация, логирование и CLI.

![CI](https://github.com/bpa9008-prog/research-graph/actions/workflows/ci.yml/badge.svg)

## Требования

- Python 3.11+
- uv — https://docs.astral.sh/uv/

## Установка

    git clone https://github.com/bpa9008-prog/research-graph.git
    cd research-graph
    uv sync --all-groups

## Конфигурация

Все настройки читаются из переменных окружения с префиксом RG_.
Локально удобно хранить их в .env (он в .gitignore); шаблон — .env.example.

Переменная           | По умолчанию | Описание
---------------------|--------------|------------------------------------------------------
RG_GITHUB_TOKEN      | (нет)        | GitHub Personal Access Token. Без него — анонимно.
RG_DATA_DIR          | data         | Корневая директория для данных.
RG_LOG_LEVEL         | INFO         | DEBUG / INFO / WARNING / ERROR / CRITICAL.
RG_REQUEST_TIMEOUT   | 30.0         | Таймаут HTTP-запроса, секунды (1–300).
RG_MAX_CONCURRENCY   | 4            | Максимум одновременных запросов (1–64).

## Использование

    uv run rg version
    # -> research-graph 0.1.0

    uv run rg check-config
    # -> research-graph configuration
    #    ----------------------------------------
    #    github_token     : <not set>
    #    data_dir       : data
    #    log_level      : INFO
    #    request_timeout: 30.0 s
    #    max_concurrency: 4

## Разработка

    uv run ruff check .
    uv run ruff format --check .
    uv run mypy src
    uv run pytest -q
    uv run pre-commit run --all-files

## Структура проекта

    research-graph/
    ├── src/research_graph/
    │   ├── __init__.py
    │   ├── config.py
    │   ├── logging_setup.py
    │   ├── cli.py
    │   └── py.typed
    ├── tests/
    │   ├── conftest.py
    │   ├── test_config.py
    │   ├── test_cli.py
    │   └── test_logging_setup.py
    ├── .github/workflows/ci.yml
    ├── .pre-commit-config.yaml
    ├── .gitattributes
    ├── .gitignore
    ├── .env.example
    ├── pyproject.toml
    └── uv.lock
