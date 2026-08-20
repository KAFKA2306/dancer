"""Deterministic media validation for candidate publication artifacts."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class MediaAudit:
    passed: bool
    duration_seconds: float
    width: int
    height: int
    video_codec: str
    audio_codec: str
    black_duration_seconds: float
    mean_volume_db: float | None
    max_volume_db: float | None
    reasons: tuple[str, ...]


def _run_text(command: list[str], runner: Callable[..., subprocess.CompletedProcess[str]]) -> subprocess.CompletedProcess[str]:
    return runner(command, capture_output=True, text=True, check=True)


def audit_media(
    path: str | Path,
    *,
    expected_width: int,
    expected_height: int,
    expected_duration_seconds: float,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> MediaAudit:
    probe = _run_text(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        runner,
    )
    payload = json.loads(probe.stdout)
    videos = [item for item in payload.get("streams", []) if item.get("codec_type") == "video"]
    audios = [item for item in payload.get("streams", []) if item.get("codec_type") == "audio"]
    reasons: list[str] = []
    if len(videos) != 1:
        reasons.append(f"expected exactly one video stream, found {len(videos)}")
    if len(audios) != 1:
        reasons.append(f"expected exactly one audio stream, found {len(audios)}")
    video = videos[0] if videos else {}
    audio = audios[0] if audios else {}
    width = int(video.get("width") or 0)
    height = int(video.get("height") or 0)
    duration = float(payload.get("format", {}).get("duration") or 0.0)
    if width != expected_width or height != expected_height:
        reasons.append(f"resolution mismatch: expected {expected_width}x{expected_height}, got {width}x{height}")
    tolerance = max(0.25, 1.0 / 6.0)
    if abs(duration - expected_duration_seconds) > tolerance:
        reasons.append(f"duration mismatch: expected {expected_duration_seconds:.3f}s, got {duration:.3f}s")

    black = runner(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vf", "blackdetect=d=0.15:pix_th=0.10", "-an", "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    black_duration = sum(float(value) for value in re.findall(r"black_duration:([0-9.]+)", black.stderr or ""))
    if duration > 0 and black_duration / duration > 0.08:
        reasons.append(f"black frames exceed threshold: {black_duration:.3f}s of {duration:.3f}s")

    volume = runner(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    stderr = volume.stderr or ""
    mean_match = re.search(r"mean_volume:\s*(-?[0-9.]+) dB", stderr)
    max_match = re.search(r"max_volume:\s*(-?[0-9.]+) dB", stderr)
    mean_volume = float(mean_match.group(1)) if mean_match else None
    max_volume = float(max_match.group(1)) if max_match else None
    if mean_volume is None or max_volume is None:
        reasons.append("unable to measure audio volume")
    else:
        if mean_volume < -45.0:
            reasons.append(f"audio is effectively silent: mean {mean_volume:.1f} dB")
        if max_volume > -0.1:
            reasons.append(f"audio peak is too close to clipping: {max_volume:.1f} dB")

    return MediaAudit(
        passed=not reasons,
        duration_seconds=duration,
        width=width,
        height=height,
        video_codec=str(video.get("codec_name") or ""),
        audio_codec=str(audio.get("codec_name") or ""),
        black_duration_seconds=black_duration,
        mean_volume_db=mean_volume,
        max_volume_db=max_volume,
        reasons=tuple(reasons),
    )


def write_audit(audit: MediaAudit, destination: str | Path) -> None:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(audit), ensure_ascii=False, indent=2), encoding="utf-8")
