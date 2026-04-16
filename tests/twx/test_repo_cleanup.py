"""Repository-shape assertions for the legacy cleanup task."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_only_twx_test_suite_remains():
    """No legacy test files should remain at the tests/ root level."""
    root_entries = {path.name for path in Path(REPO_ROOT / "tests").iterdir()}
    assert "twx" in root_entries
    assert "test_twitter_adapter.py" not in root_entries
    assert "test_tasks.py" not in root_entries


def test_no_legacy_app_directory():
    """The legacy app/ directory should not exist."""
    assert not (REPO_ROOT / "app").exists()


def test_no_legacy_alembic_directory():
    """The legacy alembic/ directory should not exist."""
    assert not (REPO_ROOT / "alembic").exists()


def test_no_legacy_cli_directory():
    """The legacy cli/ directory should not exist."""
    assert not (REPO_ROOT / "cli").exists()


def test_no_legacy_docker_files():
    """Legacy Docker/deployment files should not exist."""
    assert not (REPO_ROOT / "docker-compose.yml").exists()
    assert not (REPO_ROOT / "Dockerfile").exists()
    assert not (REPO_ROOT / "entrypoint.sh").exists()
    assert not (REPO_ROOT / "start-local.sh").exists()
    assert not (REPO_ROOT / "start.sh").exists()
    assert not (REPO_ROOT / "deploy.sh").exists()


def test_twx_package_exists():
    """The twx package directory must exist."""
    assert (REPO_ROOT / "twx").is_dir()


def test_twx_commands_exist():
    """Command modules must exist."""
    commands = REPO_ROOT / "twx" / "commands"
    assert (commands / "user.py").exists()
    assert (commands / "search.py").exists()
    assert (commands / "trending.py").exists()
