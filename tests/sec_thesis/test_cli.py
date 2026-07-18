from typer.testing import CliRunner

from sec_thesis.cli import app

runner = CliRunner()


def test_cli_lists_all_three_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "resolve-cik" in result.output
    assert "list-filings" in result.output
    assert "fetch-filings" in result.output


def test_resolve_cik_requires_ticker_argument() -> None:
    result = runner.invoke(app, ["resolve-cik"])

    assert result.exit_code != 0
