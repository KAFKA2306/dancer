"""Generate and validate a real Siroino dance video."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from typing import Callable

import bpy

from .dance_renderer import IMAGE2OUTFIT_COMMIT, SIROINO_LICENSE, SIROINO_TERMS_URL, SIROINO_URL, render_dance


@dataclass(frozen=True)
class GeneratedArtifact:
    path: str
    media_type: str
    generator: str
    generator_version: str
    duration_seconds: float
    fps: float
    width: int
    height: int
    codec: str
    sha256: str
    size_bytes: int
    motion_id: str
    motion_source_url: str
    avatar_source_url: str
    avatar_source_commit: str
    avatar_terms_url: str
    avatar_license: str
    camera_preset: str
    framing_margin: float
    camera_max_step_per_frame: float


def _sha256(path: str | os.PathLike[str]) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_frame_rate(raw: str) -> float:
    if "/" in raw:
        numerator, denominator = raw.split("/", maxsplit=1)
        denominator_value = float(denominator)
        if denominator_value == 0:
            return 0.0
        return float(numerator) / denominator_value
    return float(raw or 0.0)


def _probe_video(
    path: str,
    *,
    motion_id: str,
    motion_source_url: str,
    camera_preset: str,
    framing_margin: float,
    camera_max_step_per_frame: float,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> GeneratedArtifact:
    result = runner(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    video_stream = next(stream for stream in payload["streams"] if stream["codec_type"] == "video")
    duration = float(payload["format"]["duration"])
    width = int(video_stream["width"])
    height = int(video_stream["height"])
    codec = str(video_stream["codec_name"])
    fps = _parse_frame_rate(str(video_stream.get("avg_frame_rate") or "0"))
    if duration <= 0:
        raise ValueError("video duration must be positive")
    if width <= 0 or height <= 0:
        raise ValueError("video dimensions must be positive")
    if fps <= 0:
        raise ValueError("video frame rate must be positive")

    return GeneratedArtifact(
        path=str(os.path.abspath(path)),
        media_type="video/mp4",
        generator="Blender",
        generator_version=bpy.app.version_string,
        duration_seconds=duration,
        fps=fps,
        width=width,
        height=height,
        codec=codec,
        sha256=_sha256(path),
        size_bytes=os.path.getsize(path),
        motion_id=motion_id,
        motion_source_url=motion_source_url,
        avatar_source_url=SIROINO_URL,
        avatar_source_commit=IMAGE2OUTFIT_COMMIT,
        avatar_terms_url=SIROINO_TERMS_URL,
        avatar_license=SIROINO_LICENSE,
        camera_preset=camera_preset,
        framing_margin=framing_margin,
        camera_max_step_per_frame=camera_max_step_per_frame,
    )


def generate_video(
    output_dir: str | os.PathLike[str],
    *,
    motion_id: str,
    duration_seconds: float,
    fps: int,
    size: int | None = None,
    width: int | None = None,
    height: int | None = None,
    camera_preset: str = "front",
    probe_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> GeneratedArtifact:
    rendered_path, motion, render_evidence = render_dance(
        output_dir,
        motion_id=motion_id,
        duration_seconds=duration_seconds,
        fps=fps,
        size=size,
        width=width,
        height=height,
        camera_preset=camera_preset,
    )
    return _probe_video(
        rendered_path,
        motion_id=motion.id,
        motion_source_url=motion.url,
        camera_preset=render_evidence.camera_preset,
        framing_margin=render_evidence.framing_margin,
        camera_max_step_per_frame=render_evidence.camera_max_step_per_frame,
        runner=probe_runner,
    )
