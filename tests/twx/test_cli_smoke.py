from click.testing import CliRunner

from twx.cli import cli


def test_help_lists_new_commands():
    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "user" in result.output
    assert "search" in result.output
    assert "trending" in result.output
