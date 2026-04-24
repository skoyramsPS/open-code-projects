from __future__ import annotations

import pytest


def test_parse_args_accepts_positional_source_file() -> None:
    from comicbook.upload_run import parse_args

    parsed = parse_args(["templates.json", "--dry-run"])

    assert parsed.source_file == "templates.json"
    assert parsed.stdin is False
    assert parsed.dry_run is True


def test_parse_args_accepts_stdin_without_source_file() -> None:
    from comicbook.upload_run import parse_args

    parsed = parse_args(["--stdin", "--no-backfill"])

    assert parsed.source_file is None
    assert parsed.stdin is True
    assert parsed.no_backfill is True


def test_parse_args_rejects_missing_source(capsys: pytest.CaptureFixture[str]) -> None:
    from comicbook.upload_run import parse_args

    with pytest.raises(SystemExit) as excinfo:
        parse_args([])

    assert excinfo.value.code == 2
    assert "exactly one source must be provided" in capsys.readouterr().err


def test_parse_args_rejects_both_source_file_and_stdin(capsys: pytest.CaptureFixture[str]) -> None:
    from comicbook.upload_run import parse_args

    with pytest.raises(SystemExit) as excinfo:
        parse_args(["templates.json", "--stdin"])

    assert excinfo.value.code == 2
    assert "exactly one source must be provided" in capsys.readouterr().err


def test_parse_args_rejects_allow_missing_optional_without_no_backfill(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from comicbook.upload_run import parse_args

    with pytest.raises(SystemExit) as excinfo:
        parse_args(["templates.json", "--allow-missing-optional"])

    assert excinfo.value.code == 2
    assert "--allow-missing-optional requires --no-backfill" in capsys.readouterr().err
