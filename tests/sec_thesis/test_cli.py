from typer.testing import CliRunner

from sec_thesis.cli import app

runner = CliRunner()


def test_cli_lists_all_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "resolve-cik" in result.output
    assert "list-filings" in result.output
    assert "fetch-filings" in result.output
    assert "extract-relationships" in result.output
    assert "show-graph" in result.output


def test_resolve_cik_requires_ticker_argument() -> None:
    result = runner.invoke(app, ["resolve-cik"])

    assert result.exit_code != 0


def test_show_graph_fails_cleanly_without_extraction(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SEC_USER_AGENT", "Test test@example.com")
    monkeypatch.setenv("SEC_THESIS_DB_PATH", str(tmp_path / "sec_thesis.duckdb"))

    result = runner.invoke(app, ["show-graph", "ZZZZ"])

    assert result.exit_code == 1
    assert "extract-relationships" in result.output
