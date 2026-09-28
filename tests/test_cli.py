"""Тесты CLI через Typer CliRunner."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from research_graph import __version__
from research_graph.cli import app

runner = CliRunner()


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_check_config_summary() -> None:
    result = runner.invoke(app, ["check-config"])
    assert result.exit_code == 0
    assert "research-graph configuration" in result.stdout
    assert "github_token" in result.stdout
    assert "log_level" in result.stdout


def test_check_config_hides_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Секрет не должен попадать в stdout — это инцидент безопасности."""
    monkeypatch.setenv("RG_GITHUB_TOKEN", "ghp_supersecretvalue1234567890")
    result = runner.invoke(app, ["check-config"])
    assert result.exit_code == 0
    assert "ghp_supersecretvalue1234567890" not in result.stdout
    # но признак наличия и маска — есть
    assert "ghp_****" in result.stdout


def test_check_config_not_set() -> None:
    result = runner.invoke(app, ["check-config"])
    assert result.exit_code == 0
    assert "<not set>" in result.stdout


def test_check_config_verbose_creates_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    target = tmp_path / "data-x"
    monkeypatch.setenv("RG_DATA_DIR", str(target))
    result = runner.invoke(app, ["check-config", "--verbose"])
    assert result.exit_code == 0
    assert target.is_dir()


def test_help_lists_both_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "version" in result.stdout
    assert "check-config" in result.stdout
