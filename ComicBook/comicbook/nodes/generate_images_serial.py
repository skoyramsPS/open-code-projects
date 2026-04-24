"""Generate images strictly serially from precomputed prompt work items."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from comicbook.db import ImageRecord
from comicbook.deps import Deps
from comicbook.image_client import generate_one
from comicbook.state import ImageResult, RenderedPrompt, RunState, UsageTotals, WorkflowError


def _format_timestamp(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc) if value.tzinfo is not None else value
    rendered = normalized.replace(microsecond=0).isoformat()
    return rendered.replace("+00:00", "Z") if value.tzinfo is not None else f"{rendered}Z"


def _result_path(output_dir: Path, run_id: str, fingerprint: str) -> Path:
    return output_dir / run_id / f"{fingerprint}.png"


def _has_same_run_generated_row(existing_images: list[ImageRecord], *, run_id: str, out_path: Path) -> bool:
    rendered_path = str(out_path)
    return any(
        image.run_id == run_id and image.status == "generated" and image.file_path == rendered_path
        for image in existing_images
    )


def _build_image_result(
    *,
    prompt: RenderedPrompt,
    status: str,
    file_path: str | None,
    bytes_written: int,
    run_id: str,
    created_at: str,
    failure_reason: str | None = None,
) -> ImageResult:
    fingerprint = prompt.fingerprint
    if fingerprint is None:  # pragma: no cover - guarded by caller state checks
        raise RuntimeError("RenderedPrompt.fingerprint is required for image result materialization")

    return ImageResult.model_validate(
        {
            "fingerprint": fingerprint,
            "status": status,
            "file_path": file_path,
            "bytes": bytes_written,
            "run_id": run_id,
            "created_at": created_at,
            "failure_reason": failure_reason,
        }
    )


def _build_workflow_error(
    *,
    code: str,
    message: str,
    fingerprint: str | None = None,
    attempts: int | None = None,
    http_status: int | None = None,
    retryable: bool = False,
) -> WorkflowError:
    details: dict[str, object] = {}
    if fingerprint is not None:
        details["fingerprint"] = fingerprint
    if attempts is not None:
        details["attempts"] = attempts
    if http_status is not None:
        details["http_status"] = http_status

    return WorkflowError.model_validate(
        {
            "code": code,
            "message": message,
            "node": "generate_images_serial",
            "retryable": retryable,
            "details": details,
        }
    )


def generate_images_serial(state: RunState, deps: Deps) -> dict[str, object]:
    """Generate uncached images one at a time, with resume and rate-limit guards."""

    run_id = state.get("run_id")
    if not run_id:
        raise ValueError("generate_images_serial requires state['run_id']")

    if "to_generate" not in state:
        raise ValueError("generate_images_serial requires state['to_generate']")

    rendered_prompts_by_fp = state.get("rendered_prompts_by_fp")
    if not rendered_prompts_by_fp:
        raise ValueError("generate_images_serial requires state['rendered_prompts_by_fp']")

    existing_results = list(state.get("image_results", []))
    existing_errors = list(state.get("errors", []))
    existing_usage = UsageTotals.model_validate(state.get("usage") or {})
    rate_limit_consecutive_failures = state.get("rate_limit_consecutive_failures", 0)

    new_results: list[ImageResult] = []
    new_errors: list[WorkflowError] = []
    image_call_attempts = 0

    for index, queued_prompt in enumerate(state["to_generate"]):
        fingerprint = queued_prompt.fingerprint
        if fingerprint is None:
            raise ValueError("generate_images_serial requires every prompt in state['to_generate'] to have a fingerprint")

        prompt = rendered_prompts_by_fp.get(fingerprint)
        if prompt is None:
            raise ValueError("generate_images_serial could not resolve a fingerprint from state['rendered_prompts_by_fp']")

        created_at = _format_timestamp(deps.clock())
        out_path = _result_path(deps.output_dir, run_id, fingerprint)
        if out_path.exists():
            bytes_written = out_path.stat().st_size
            existing_images = deps.db.get_existing_images_by_fingerprint(fingerprint)
            if not _has_same_run_generated_row(existing_images, run_id=run_id, out_path=out_path):
                deps.db.insert_image_result(
                    fingerprint=fingerprint,
                    run_id=run_id,
                    created_at=created_at,
                    status="generated",
                    file_path=str(out_path),
                    bytes_written=bytes_written,
                )
            new_results.append(
                _build_image_result(
                    prompt=prompt,
                    status="generated",
                    file_path=str(out_path),
                    bytes_written=bytes_written,
                    run_id=run_id,
                    created_at=created_at,
                )
            )
            rate_limit_consecutive_failures = 0
            continue

        client_result = generate_one(
            http_client=deps.http_client,
            config=deps.config,
            prompt=prompt.rendered_prompt,
            size=prompt.size,
            quality=prompt.quality,
            image_model=prompt.image_model,
            out_path=out_path,
            transport=deps.image_transport,
        )
        image_call_attempts += client_result.attempts
        created_at = _format_timestamp(deps.clock())

        if client_result.ok:
            persisted_path = str(client_result.file_path) if client_result.file_path is not None else str(out_path)
            deps.db.insert_image_result(
                fingerprint=fingerprint,
                run_id=run_id,
                created_at=created_at,
                status="generated",
                file_path=persisted_path,
                bytes_written=client_result.bytes_written,
            )
            new_results.append(
                _build_image_result(
                    prompt=prompt,
                    status="generated",
                    file_path=persisted_path,
                    bytes_written=client_result.bytes_written,
                    run_id=run_id,
                    created_at=created_at,
                )
            )
            rate_limit_consecutive_failures = 0
            continue

        failure_reason = client_result.failure_reason or "Image generation failed"
        deps.db.insert_image_result(
            fingerprint=fingerprint,
            run_id=run_id,
            created_at=created_at,
            status="failed",
            file_path=None,
            bytes_written=0,
            failure_reason=failure_reason,
        )
        new_results.append(
            _build_image_result(
                prompt=prompt,
                status="failed",
                file_path=None,
                bytes_written=0,
                run_id=run_id,
                created_at=created_at,
                failure_reason=failure_reason,
            )
        )
        new_errors.append(
            _build_workflow_error(
                code=client_result.failure_code or "image_generation_failed",
                message=failure_reason,
                fingerprint=fingerprint,
                attempts=client_result.attempts,
                http_status=client_result.last_http_status,
                retryable=client_result.last_http_status in {408, 429}
                or (client_result.last_http_status is not None and client_result.last_http_status >= 500),
            )
        )

        if client_result.last_http_status == 429 and client_result.failure_code == "rate_limited":
            rate_limit_consecutive_failures += 1
        else:
            rate_limit_consecutive_failures = 0

        if rate_limit_consecutive_failures < 2:
            continue

        skipped_fingerprints: list[str] = []
        for skipped_prompt in state["to_generate"][index + 1 :]:
            skipped_fingerprint = skipped_prompt.fingerprint
            if skipped_fingerprint is None:
                raise ValueError(
                    "generate_images_serial requires every prompt in state['to_generate'] to have a fingerprint"
                )
            resolved_prompt = rendered_prompts_by_fp.get(skipped_fingerprint)
            if resolved_prompt is None:
                raise ValueError(
                    "generate_images_serial could not resolve a skipped fingerprint from state['rendered_prompts_by_fp']"
                )

            skipped_reason = (
                "Skipped because the rate limit circuit breaker tripped after two consecutive retry-exhausted 429 failures."
            )
            skipped_created_at = _format_timestamp(deps.clock())
            deps.db.insert_image_result(
                fingerprint=skipped_fingerprint,
                run_id=run_id,
                created_at=skipped_created_at,
                status="skipped_rate_limit",
                file_path=None,
                bytes_written=0,
                failure_reason=skipped_reason,
            )
            new_results.append(
                _build_image_result(
                    prompt=resolved_prompt,
                    status="skipped_rate_limit",
                    file_path=None,
                    bytes_written=0,
                    run_id=run_id,
                    created_at=skipped_created_at,
                    failure_reason=skipped_reason,
                )
            )
            skipped_fingerprints.append(skipped_fingerprint)

        if skipped_fingerprints:
            new_errors.append(
                WorkflowError.model_validate(
                    {
                        "code": "rate_limit_circuit_breaker",
                        "message": "Stopped remaining image API calls after two consecutive retry-exhausted 429 failures.",
                        "node": "generate_images_serial",
                        "retryable": True,
                        "details": {"skipped_fingerprints": skipped_fingerprints},
                    }
                )
            )
        break

    updated_usage = existing_usage.model_copy(update={"image_calls": existing_usage.image_calls + image_call_attempts})

    return {
        "image_results": existing_results + new_results,
        "errors": existing_errors + new_errors,
        "usage": updated_usage,
        "rate_limit_consecutive_failures": rate_limit_consecutive_failures,
    }


__all__ = ["generate_images_serial"]
