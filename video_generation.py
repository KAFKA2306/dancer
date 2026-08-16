"""Generate and validate a real 3D dance video."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from dance_renderer import render_dance


class PipelineMode(str, Enum):
    LOCAL_RENDER = "LOCAL_RENDER"
    YOUTUBE_PUBLISH = "YOUTUBE_PUBLISH"


@dataclass(frozen=True)
class GeneratedArtifact:
    path: str
    media_type: str
    generator: str
    generator_version: str
    duration_seconds: float
    width: int
    height: int
    codec: str
    sha256: str


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
    result = runner(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    video_stream = next(
        stream for stream in payload["streams"] if stream["codec_type"] == "video"
    )
    duration = float(payload["format"]["duration"])
    width = int(video_stream["width"])
    height = int(video_stream["height"])
    codec = str(video_stream["codec_name"])
    if duration <= 0:
        raise ValueError("video duration must be positive")
    if width <= 0 or height <= 0:
        raise ValueError("video dimensions must be positive")

    return GeneratedArtifact(
        path=path,
        media_type="video/mp4",
        generator="vtk",
        generator_version="9.6.2",
        duration_seconds=duration,
        width=width,
        height=height,
        codec=codec,
        sha256=_sha256(path),
    )


def generate_video(
    output_dir: str | os.PathLike[str],
    *,
    duration_seconds: float,
    fps: int,
    size: int,
    probe_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> GeneratedArtifact:
    """Render moving 3D geometry and return it only after ffprobe validation."""
    rendered_path = render_dance(
        output_dir,
        duration_seconds=duration_seconds,
        fps=fps,
        size=size,
    )
    return _probe_video(rendered_path, runner=probe_runner)
