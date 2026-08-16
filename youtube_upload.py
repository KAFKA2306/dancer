"""YouTube publication boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping

from video_generation import GeneratedArtifact, PipelineMode


class UploadStatus(str, Enum):
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    UPLOADED = "UPLOADED"


@dataclass(frozen=True)
class UploadResult:
    status: UploadStatus
    youtube_video_id: str | None = None


def upload_video(
    artifact: GeneratedArtifact,
    mode: PipelineMode,
    uploader: Callable[[str], Mapping[str, Any]] | None = None,
) -> UploadResult:
    """Publish a validated render when YOUTUBE_PUBLISH is explicitly selected."""
    if mode is PipelineMode.LOCAL_RENDER:
        return UploadResult(status=UploadStatus.NOT_ATTEMPTED)

    if uploader is None:
        raise RuntimeError("YOUTUBE_PUBLISH requires a YouTube uploader")

    response = uploader(artifact.path)
    video_id = response["id"]
    if not isinstance(video_id, str) or not video_id.strip():
        raise ValueError("upload response id must be a non-empty string")

    return UploadResult(
        status=UploadStatus.UPLOADED,
        youtube_video_id=video_id.strip(),
    )
