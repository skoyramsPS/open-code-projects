from __future__ import annotations

import json
from pathlib import Path

from pipelines.shared.db import ComicBookDB
from pipelines.shared.fingerprint import compute_prompt_fingerprint
from pipelines.workflows.image_prompt_gen.graph import run_workflow
from pipelines.workflows.image_prompt_gen.state import TemplateSummary

from .support import FakeImageTransport
from .support import FakeRouterTransport
from .support import db
from .support import make_deps
from .support import make_image_response
from .support import make_new_template_router_response
from .support import make_router_response


def test_run_workflow_happy_path_generates_images_and_finalizes_run(tmp_path: Path, db: ComicBookDB) -> None:
    router_transport = FakeRouterTransport(
        responses=[
            make_router_response(
                "Traveler portrait at sunrise.",
                "Traveler portrait at dusk.",
            )
        ]
    )
    image_transport = FakeImageTransport(
        responses=[
            make_image_response(b"image-one"),
            make_image_response(b"image-two"),
        ]
    )

    final_state = run_workflow(
        {
            "run_id": "run-1",
            "user_prompt": "Create a two-panel traveler portrait sequence.",
        },
        make_deps(tmp_path, db, router_transport, image_transport, logger_name="test-graph-happy"),
    )

    assert final_state["run_id"] == "run-1"
    assert final_state["run_status"] == "succeeded"
    assert final_state["summary"].cache_hits == 0
    assert final_state["summary"].generated == 2
    assert final_state["summary"].failed == 0
    assert final_state["summary"].skipped_rate_limit == 0
    assert [result.status for result in final_state["image_results"]] == ["generated", "generated"]
    assert final_state["usage"].router_calls == 1
    assert final_state["usage"].image_calls == 2

    assert len(router_transport.calls) == 1
    assert len(image_transport.calls) == 2
    assert image_transport.calls[0]["payload"]["prompt"] == "Traveler portrait at sunrise."
    assert image_transport.calls[1]["payload"]["prompt"] == "Traveler portrait at dusk."

    generated_paths = [Path(result.file_path or "") for result in final_state["image_results"]]
    assert all(path.exists() for path in generated_paths)

    run_record = db.get_run("run-1")
    assert run_record is not None
    assert run_record.status == "succeeded"
    assert run_record.generated == 2
    assert run_record.cache_hits == 0
    assert run_record.failed == 0
    assert run_record.pid is None
    assert run_record.host is None
    assert json.loads(run_record.plan_json or "{}") != {}


def test_run_workflow_second_run_uses_cache_and_skips_image_api(tmp_path: Path, db: ComicBookDB) -> None:
    first_router_transport = FakeRouterTransport(responses=[make_router_response("Traveler portrait at sunrise.")])
    first_image_transport = FakeImageTransport(responses=[make_image_response(b"cached-image-source")])
    first_state = run_workflow(
        {
            "run_id": "run-1",
            "user_prompt": "Create one traveler portrait.",
        },
        make_deps(tmp_path, db, first_router_transport, first_image_transport, logger_name="test-graph-cache-hit-first"),
    )

    assert first_state["summary"].generated == 1
    assert len(first_image_transport.calls) == 1

    second_router_transport = FakeRouterTransport(responses=[make_router_response("Traveler portrait at sunrise.")])
    second_image_transport = FakeImageTransport(responses=[])
    second_state = run_workflow(
        {
            "run_id": "run-2",
            "user_prompt": "Create one traveler portrait.",
        },
        make_deps(tmp_path, db, second_router_transport, second_image_transport, logger_name="test-graph-cache-hit-second"),
    )

    assert second_state["run_status"] == "succeeded"
    assert second_state["summary"].cache_hits == 1
    assert second_state["summary"].generated == 0
    assert second_state["image_results"] == []
    assert second_state["usage"].router_calls == 1
    assert second_state["usage"].image_calls == 0
    assert len(second_router_transport.calls) == 1
    assert second_image_transport.calls == []

    second_run_record = db.get_run("run-2")
    assert second_run_record is not None
    assert second_run_record.status == "succeeded"
    assert second_run_record.cache_hits == 1
    assert second_run_record.generated == 0


def test_run_workflow_resume_reuses_existing_same_run_output_file(tmp_path: Path, db: ComicBookDB) -> None:
    first_subject = "Traveler portrait at sunrise."
    second_subject = "Traveler portrait at dusk."
    first_fingerprint = compute_prompt_fingerprint(
        first_subject,
        size="1024x1536",
        quality="high",
        image_model="gpt-image-1.5",
    )
    resumed_path = tmp_path / "image_output" / "run-1" / f"{first_fingerprint}.png"
    resumed_path.parent.mkdir(parents=True, exist_ok=True)
    resumed_path.write_bytes(b"existing-image")

    router_transport = FakeRouterTransport(responses=[make_router_response(first_subject, second_subject)])
    image_transport = FakeImageTransport(responses=[make_image_response(b"new-image")])

    final_state = run_workflow(
        {
            "run_id": "run-1",
            "user_prompt": "Create a two-panel traveler portrait sequence.",
        },
        make_deps(tmp_path, db, router_transport, image_transport, logger_name="test-graph-resume"),
    )

    assert final_state["run_status"] == "succeeded"
    assert [result.status for result in final_state["image_results"]] == ["generated", "generated"]
    assert final_state["summary"].generated == 2
    assert final_state["summary"].cache_hits == 0
    assert final_state["usage"].image_calls == 1
    assert len(image_transport.calls) == 1
    assert image_transport.calls[0]["payload"]["prompt"] == second_subject

    resumed_rows = db.get_existing_images_by_fingerprint(first_fingerprint)
    assert resumed_rows[-1].status == "generated"
    assert resumed_rows[-1].file_path == str(resumed_path)

    run_record = db.get_run("run-1")
    assert run_record is not None
    assert run_record.status == "succeeded"
    assert run_record.generated == 2


def test_run_workflow_extract_new_template_persists_exactly_one_template_row(tmp_path: Path, db: ComicBookDB) -> None:
    router_transport = FakeRouterTransport(responses=[make_new_template_router_response()])
    image_transport = FakeImageTransport(responses=[make_image_response(b"new-template-image")])

    final_state = run_workflow(
        {
            "run_id": "run-new-template",
            "user_prompt": "Create a moody alley portrait in a fresh comic-ink style.",
        },
        make_deps(
            tmp_path,
            db,
            router_transport,
            image_transport,
            pricing={"image_models": {"gpt-image-1.5": {"usd_per_image": 0.25}}},
            logger_name="test-graph-new-template",
        ),
    )

    assert final_state["run_status"] == "succeeded"
    assert final_state["summary"].generated == 1
    assert final_state["plan"].template_decision.extract_new_template is True
    assert final_state["plan"].template_decision.new_template is not None
    assert final_state["plan"].template_decision.new_template.id == "fresh-ink"

    template_summaries = db.list_template_summaries(summary_factory=TemplateSummary.model_validate)
    persisted_rows = db.get_templates_by_ids(["fresh-ink"])
    assert [summary.id for summary in template_summaries] == ["fresh-ink"]
    assert len(persisted_rows) == 1
    assert persisted_rows[0].name == "Fresh Ink"
    assert persisted_rows[0].created_by_run == "run-new-template"

    assert len(router_transport.calls) == 1
    assert len(image_transport.calls) == 1
    report_path = tmp_path / "runs" / "run-new-template" / "report.md"
    summary_path = tmp_path / "logs" / "run-new-template.summary.json"
    assert report_path.exists()
    assert summary_path.exists()
