"""Packaging and import tests for phx."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_phx_imports_without_token(monkeypatch):
    monkeypatch.delenv("PRODUCTHUNT_TOKEN", raising=False)

    import phx

    assert hasattr(phx, "__version__")


def test_phx_cli_imports_without_token(monkeypatch):
    monkeypatch.delenv("PRODUCTHUNT_TOKEN", raising=False)

    from phx.cli import cli

    assert cli.name == "cli" or cli.name is not None


def test_pyproject_includes_phx_package_and_script():
    pyproject = (REPO_ROOT / "pyproject.toml").read_text()

    assert '"phx*"' in pyproject
    assert 'phx = "phx.cli:cli"' in pyproject
    assert '"tests/phx"' in pyproject
