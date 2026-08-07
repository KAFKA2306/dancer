"""Video artifact generation and validation boundaries."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable


class PipelineMode(str, Enum):
    STUB = "STUB"
    LOCAL_RENDER = "LOCAL_RENDER"
    YOUTUBE_PUBLISH = "YOUTUBE_PUBLISH"


class ValidationStatus(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    VALID = "VALID"
    INVALID = "INVALID"


@dataclass(frozen=True)
class GeneratedArtifact:
    path: str
    media_type: str
    generator: str
    generator_version: str
    duration_seconds: float | None
    width: int | None
    height: int | None
    codec: str | None
    sha256: str
    validation_status: ValidationStatus
    validation_error: str | None = None


def _sha256(path: str | os.PathLike[str]) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _probe_video(
    path: str,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> GeneratedArtifact:
    """Validate a rendered video with ffprobe and return audited metadata."""
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        path,
    ]
    try:
        result = runner(command, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return GeneratedArtifact(
            path=path,
            media_type="video/mp4",
            generator="external-renderer",
            generator_version="unknown",
            duration_seconds=None,
            width=None,
            height=None,
            codec=None,
            sha256=_sha256(path),
            validation_status=ValidationStatus.INVALID,
            validation_error="ffprobe is not installed",
        )

    if result.returncode != 0:
        return GeneratedArtifact(
            path=path,
            media_type="video/mp4",
            generator="external-renderer",
            generator_version="unknown",
            duration_seconds=None,
            width=None,
            height=None,
            codec=None,
            sha256=_sha256(path),
            validation_status=ValidationStatus.INVALID,
            validation_error=(result.stderr or "ffprobe rejected the media").strip(),
        )

    try:
        payload = json.loads(result.stdout)
        streams = payload.get("streams", [])
        video_stream = next(stream for stream in streams if stream.get("codec_type") == "video")
        duration = float(payload.get("format", {}).get("duration") or video_stream.get("duration"))
        if duration <= 0:
            raise ValueError("duration must be positive")
        width = int(video_stream["width"])
        height = int(video_stream["height"])
        codec = str(video_stream["codec_name"])
    except (KeyError, StopIteration, TypeError, ValueError) as exc:
        return GeneratedArtifact(
            path=path,
            media_type="video/mp4",
            generator="external-renderer",
            generator_version="unknown",
            duration_seconds=None,
            width=None,
            height=None,
            codec=None,
            sha256=_sha256(path),
            validation_status=ValidationStatus.INVALID,
            validation_error=f"invalid ffprobe payload: {exc}",
        )

    return GeneratedArtifact(
        path=path,
        media_type="video/mp4",
        generator="external-renderer",
        generator_version="unknown",
        duration_seconds=duration,
        width=width,
        height=height,
        codec=codec,
        sha256=_sha256(path),
        validation_status=ValidationStatus.VALID,
    )


def generate_video(
    avatar: str,
    motion: str,
    music: str,
    background: str,
    output_dir: str | os.PathLike[str],
    mode: PipelineMode = PipelineMode.STUB,
    renderer: Callable[[str, str, str, str, str], str] | None = None,
    probe_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> GeneratedArtifact:
    """Generate an explicit stub manifest or validate a renderer-produced video."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if mode is PipelineMode.STUB:
        stub_path = output_path / f"{uuid.uuid4().hex}.stub.json"
        stub_path.write_text(
            json.dumps(
                {
                    "mode": PipelineMode.STUB.value,
                    "avatar": avatar,
                    "motion": motion,
                    "music": music,
                    "background": background,
                    "note": "No video was rendered or published.",
                },
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return GeneratedArtifact(
            path=str(stub_path),
            media_type="application/json",
            generator="dancer-stub",
            generator_version="1",
            duration_seconds=None,
            width=None,
            height=None,
            codec=None,
            sha256=_sha256(stub_path),
            validation_status=ValidationStatus.NOT_APPLICABLE,
        )

    if renderer is None:
        raise RuntimeError(f"{mode.value} requires an explicit renderer")

    rendered_path = renderer(avatar, motion, music, background, str(output_path))
    if not Path(rendered_path).is_file():
        raise RuntimeError(f"renderer did not create a file: {rendered_path}")
    return _probe_video(rendered_path, runner=probe_runner)
