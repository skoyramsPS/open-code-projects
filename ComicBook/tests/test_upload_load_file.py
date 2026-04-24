from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


def make_deps(*, max_file_bytes: int = 5_000_000, allow_external_path: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        config=SimpleNamespace(
            comicbook_import_max_file_bytes=max_file_bytes,
            comicbook_import_allow_external_path=allow_external_path,
        )
    )


def test_upload_load_file_accepts_bare_array_input(tmp_path: Path) -> None:
    from comicbook.nodes.upload_load_file import upload_load_file

    payload = [
        {
            "template_id": "storybook-soft",
            "name": "Storybook Soft",
            "style_text": "Soft painterly linework.",
            "tags": ["storybook"],
            "summary": "Warm storybook lighting.",
        }
    ]
    source_file = tmp_path / "templates.json"
    encoded = json.dumps(payload).encode("utf-8")
    source_file.write_bytes(encoded)

    delta = upload_load_file(
        {
            "source_file_path": str(source_file),
            "allow_external_path": True,
        },
        make_deps(),
    )

    assert delta["source_file_path"] == str(source_file.resolve())
    assert delta["source_label"] == str(source_file.resolve())
    assert delta["source_file_hash"] == hashlib.sha256(encoded).hexdigest()
    assert delta["input_version"] == 1
    assert delta["raw_rows"] == payload


def test_upload_load_file_accepts_versioned_envelope_input(tmp_path: Path) -> None:
    from comicbook.nodes.upload_load_file import upload_load_file

    payload = {
        "version": 1,
        "templates": [
            {
                "template_id": "storybook-soft",
                "name": "Storybook Soft",
                "style_text": "Soft painterly linework.",
            }
        ],
    }
    source_file = tmp_path / "templates.json"
    source_file.write_text(json.dumps(payload), encoding="utf-8")

    delta = upload_load_file(
        {
            "source_file_path": str(source_file),
            "allow_external_path": True,
        },
        make_deps(),
    )

    assert delta["input_version"] == 1
    assert delta["raw_rows"] == payload["templates"]


def test_upload_load_file_accepts_stdin_payload() -> None:
    from comicbook.nodes.upload_load_file import upload_load_file

    stdin_text = json.dumps(
        [
            {
                "template_id": "storybook-soft",
                "name": "Storybook Soft",
                "style_text": "Soft painterly linework.",
            }
        ]
    )

    delta = upload_load_file(
        {
            "stdin_text": stdin_text,
            "allow_external_path": False,
        },
        make_deps(),
    )

    assert delta["source_file_path"] is None
    assert delta["source_label"] == "<stdin>"
    assert delta["source_file_hash"] == hashlib.sha256(stdin_text.encode("utf-8")).hexdigest()
    assert delta["raw_rows"][0]["template_id"] == "storybook-soft"


def test_upload_load_file_rejects_invalid_top_level_shape(tmp_path: Path) -> None:
    from comicbook.nodes.upload_load_file import upload_load_file

    source_file = tmp_path / "templates.json"
    source_file.write_text(json.dumps({"template_id": "not-an-array"}), encoding="utf-8")

    with pytest.raises(ValueError, match="top-level"):
        upload_load_file(
            {
                "source_file_path": str(source_file),
                "allow_external_path": True,
            },
            make_deps(),
        )


def test_upload_load_file_rejects_external_path_when_disallowed(tmp_path: Path) -> None:
    from comicbook.nodes.upload_load_file import upload_load_file

    source_file = tmp_path / "templates.json"
    source_file.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="outside the allowed tree"):
        upload_load_file(
            {
                "source_file_path": str(source_file),
                "allow_external_path": False,
            },
            make_deps(),
        )
