"""CLI research-graph на Typer."""

from __future__ import annotations

import logging
from typing import Annotated

import typer

from research_graph import __version__
from research_graph.config import get_settings
from research_graph.logging_setup import setup_logging

app = typer.Typer(
    name="rg",
    help="research-graph: сбор и обработка данных GitHub-репозиториев.",
    no_args_is_help=True,
    add_completion=False,
)

logger = logging.getLogger(__name__)


@app.command()
def version() -> None:
    """Показать версию пакета."""
    typer.echo(f"research-graph {__version__}")


@app.command(name="check-config")
def check_config(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Больше деталей.")] = False,
) -> None:
    """Загрузить настройки, инициализировать логирование, напечатать сводку."""
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.debug("Настройки успешно загружены")

    token_display = settings.masked_token() if settings.has_token else "<not set>"

    typer.echo("research-graph configuration")
    typer.echo("-" * 40)
    typer.echo(f"github_token     : {token_display}")
    typer.echo(f"data_dir       : {settings.data_dir}")
    typer.echo(f"log_level      : {settings.log_level}")
    typer.echo(f"request_timeout: {settings.request_timeout} s")
    typer.echo(f"max_concurrency: {settings.max_concurrency}")

    if verbose:
        data_dir = settings.ensure_data_dir()
        typer.echo(f"data_dir exists: {data_dir.exists()} ({data_dir.resolve()})")


def _main() -> None:  # pragma: no cover
    app()


if __name__ == "__main__":  # pragma: no cover
    _main()
