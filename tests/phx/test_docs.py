"""Documentation smoke tests for phx."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_phx_docs_exist_and_cover_contract():
    quickstart = REPO_ROOT / "docs/phx/quickstart.md"
    commands = REPO_ROOT / "docs/phx/commands.md"
    contracts = REPO_ROOT / "docs/phx/contracts.md"

    for path in [quickstart, commands, contracts]:
        assert path.exists(), path
        text = path.read_text()
        assert "PRODUCTHUNT_TOKEN" in text or path.name != "quickstart.md"
        assert "phx" in text

    contract_text = contracts.read_text()
    assert '"ok": true' in contract_text
    assert "config_error" in contract_text
    assert "invalid_input" in contract_text
    assert "America/Los_Angeles" in contract_text


def test_readmes_link_to_phx_docs():
    assert "docs/phx/quickstart.md" in (REPO_ROOT / "README.md").read_text()
    assert "docs/phx/quickstart.md" in (REPO_ROOT / "README.en.md").read_text()
