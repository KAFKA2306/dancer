"""Video generation and media validation."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable


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
    """Validate a rendered video with ffprobe.

    Missing ffprobe, rejected media, malformed output, and invalid dimensions or
    duration are errors. They are not converted into alternate pipeline states.
    """
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
        generator="external-renderer",
        generator_version="unknown",
        duration_seconds=duration,
        width=width,
        height=height,
        codec=codec,
        sha256=_sha256(path),
    )


def generate_video(
    avatar: str,
    motion: str,
    music: str,
    background: str,
    output_dir: str | os.PathLike[str],
    renderer: Callable[[str, str, str, str, str], str],
    probe_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> GeneratedArtifact:
    """Render a real video and return it only after ffprobe validation."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    rendered_path = renderer(avatar, motion, music, background, str(output_path))
    if not Path(rendered_path).is_file():
        raise FileNotFoundError(f"renderer did not create a file: {rendered_path}")
    return _probe_video(rendered_path, runner=probe_runner)
