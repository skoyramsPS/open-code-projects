"""Prompt and schema helpers for template metadata backfill."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


METADATA_BACKFILL_SYSTEM_PROMPT = (
    "You are helping populate metadata for an art-style template in a comic-book image workflow. "
    "Given a template's name and style_text, produce (a) a list of 3–6 lowercase tags that a "
    "designer would use to find this style, and (b) a <=240-char summary describing the style. "
    "Do not restate the name. Output only JSON matching the schema."
)

METADATA_BACKFILL_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["tags", "summary"],
    "properties": {
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 8,
        },
        "summary": {"type": "string", "minLength": 10, "maxLength": 240},
    },
}

METADATA_BACKFILL_RESPONSE_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "comicbook_template_metadata",
        "schema": deepcopy(METADATA_BACKFILL_JSON_SCHEMA),
        "strict": True,
    },
}


class MetadataBackfillValidationError(ValueError):
    """Raised when a backfill response is not valid metadata JSON."""


class MetadataBackfillResult(BaseModel):
    """Validated backfill payload for missing template metadata."""

    model_config = ConfigDict(extra="forbid")

    tags: list[str] = Field(min_length=1, max_length=8)
    summary: str = Field(min_length=10, max_length=240)

    @field_validator("tags")
    @classmethod
    def _normalize_tags(cls, value: list[str]) -> list[str]:
        normalized_tags: list[str] = []
        for tag in value:
            normalized = tag.strip().lower()
            if not normalized:
                raise ValueError("tags must not contain blank values")
            normalized_tags.append(normalized)
        return normalized_tags

    @field_validator("summary")
    @classmethod
    def _normalize_summary(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("summary must not be blank")
        return normalized


def build_metadata_backfill_payload(*, name: str, style_text: str) -> dict[str, str]:
    """Return the JSON payload sent to the metadata backfill model."""

    return {
        "name": name,
        "style_text": style_text,
    }


def build_metadata_backfill_messages(
    payload: Mapping[str, Any],
    *,
    validation_error: str | None = None,
    previous_response: str | None = None,
) -> list[dict[str, str]]:
    """Build system/user messages for metadata backfill and one repair retry."""

    if validation_error is None:
        user_content = json.dumps(dict(payload), sort_keys=True)
    else:
        user_content = (
            "Your previous JSON response failed validation. Return corrected JSON only.\n\n"
            f"Original metadata input:\n{json.dumps(dict(payload), sort_keys=True)}\n\n"
            f"Validation error:\n{validation_error}\n\n"
            f"Previous invalid response:\n{previous_response or ''}"
        )

    return [
        {"role": "system", "content": METADATA_BACKFILL_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def validate_metadata_backfill_response(raw_payload: Mapping[str, Any] | str) -> MetadataBackfillResult:
    """Parse and validate a metadata backfill JSON payload."""

    if isinstance(raw_payload, str):
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise MetadataBackfillValidationError(f"metadata response was not valid JSON: {exc}") from exc
    else:
        payload = dict(raw_payload)

    if not isinstance(payload, dict):
        raise MetadataBackfillValidationError("metadata response must be a JSON object")

    try:
        return MetadataBackfillResult.model_validate(payload)
    except ValidationError as exc:
        raise MetadataBackfillValidationError(str(exc)) from exc


__all__ = [
    "METADATA_BACKFILL_JSON_SCHEMA",
    "METADATA_BACKFILL_RESPONSE_FORMAT",
    "METADATA_BACKFILL_SYSTEM_PROMPT",
    "MetadataBackfillResult",
    "MetadataBackfillValidationError",
    "build_metadata_backfill_messages",
    "build_metadata_backfill_payload",
    "validate_metadata_backfill_response",
]
