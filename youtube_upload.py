"""YouTube publication boundary.

This module never fabricates a YouTube video ID. A video ID is accepted only
from an injected uploader response after a validated render.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Mapping, Any

from video_generation import GeneratedArtifact, PipelineMode, ValidationStatus


class UploadStatus(str, Enum):
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    STUBBED = "STUBBED"
    UPLOADED = "UPLOADED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class UploadResult:
    status: UploadStatus
    youtube_video_id: str | None = None
    error: str | None = None


def upload_video(
    artifact: GeneratedArtifact,
    mode: PipelineMode,
    uploader: Callable[[str], Mapping[str, Any]] | None = None,
) -> UploadResult:
    """Publish only a validated render in YOUTUBE_PUBLISH mode."""
    if mode is PipelineMode.STUB:
        return UploadResult(status=UploadStatus.STUBBED)

    if mode is PipelineMode.LOCAL_RENDER:
        return UploadResult(status=UploadStatus.NOT_ATTEMPTED)

    if artifact.validation_status is not ValidationStatus.VALID:
        return UploadResult(
            status=UploadStatus.FAILED,
            error="media validation did not pass; upload was not attempted",
        )

    if uploader is None:
        return UploadResult(
            status=UploadStatus.FAILED,
            error="YOUTUBE_PUBLISH requires an explicit official API uploader",
        )

    try:
        response = uploader(artifact.path)
    except Exception as exc:  # uploader/provider boundary
        return UploadResult(status=UploadStatus.FAILED, error=str(exc))

    video_id = response.get("id") if isinstance(response, Mapping) else None
    if not isinstance(video_id, str) or not video_id.strip():
        return UploadResult(
            status=UploadStatus.FAILED,
            error="upload response did not contain a non-empty video id",
        )

    return UploadResult(
        status=UploadStatus.UPLOADED,
        youtube_video_id=video_id.strip(),
    )
