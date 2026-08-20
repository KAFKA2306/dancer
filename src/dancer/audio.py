"""Rights-aware music catalog, beat timing, and deterministic audio muxing."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

CATALOG_PATH = Path(__file__).with_name("audio_tracks.json")


@dataclass(frozen=True)
class AudioTrack:
    id: str
    title: str
    creator: str
    source_url: str
    source_page_url: str
    license_name: str
    license_url: str
    source_sha1: str
    source_size_bytes: int
    bpm: float
    beat_grid_origin: str
    attribution_required: bool
    commercial_use: bool


@dataclass(frozen=True)
class AudioArtifact:
    path: str
    sha256: str
    source_sha1: str
    size_bytes: int
    playback_start_offset_seconds: float
    track: AudioTrack


def _digest(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_audio_catalog() -> list[AudioTrack]:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported audio catalog schema")
    tracks = [AudioTrack(**raw) for raw in payload.get("tracks", [])]
    if not tracks:
        raise ValueError("audio catalog is empty")
    ids = [track.id for track in tracks]
    if len(ids) != len(set(ids)):
        raise ValueError("audio track ids must be unique")
    for track in tracks:
        if track.bpm <= 0:
            raise ValueError(f"audio track has invalid BPM: {track.id}")
        if track.beat_grid_origin != "first_non_silent_audio":
            raise ValueError(f"unsupported beat grid origin for {track.id}")
        if not track.commercial_use:
            raise ValueError(f"audio track is not cleared for commercial use: {track.id}")
        if not track.source_url.startswith("https://"):
            raise ValueError(f"audio source must use HTTPS: {track.id}")
        if not track.source_page_url.startswith("https://"):
            raise ValueError(f"audio source page must use HTTPS: {track.id}")
        if not track.license_url.startswith("https://"):
            raise ValueError(f"audio license URL must use HTTPS: {track.id}")
        if len(track.source_sha1) != 40:
            raise ValueError(f"audio source SHA-1 is malformed: {track.id}")
        if track.source_size_bytes <= 0:
            raise ValueError(f"audio source size is invalid: {track.id}")
    return tracks


def get_audio_track(track_id: str) -> AudioTrack:
    tracks = load_audio_catalog()
    if track_id == "auto":
        return tracks[0]
    for track in tracks:
        if track.id == track_id:
            return track
    raise ValueError(f"unknown audio track id: {track_id}")


def detect_leading_silence(
    path: str | Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> float:
    result = runner(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-af",
            "silencedetect=noise=-45dB:d=0.10",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    stderr = result.stderr or ""
    starts = [float(value) for value in re.findall(r"silence_start:\s*([0-9.]+)", stderr)]
    ends = [float(value) for value in re.findall(r"silence_end:\s*([0-9.]+)", stderr)]
    if not starts or starts[0] > 0.02:
        return 0.0
    if not ends:
        raise ValueError("audio begins with silence but no audible start was detected")
    # Start just after FFmpeg's measured leading silence boundary. The exact source
    # is hash-pinned, so this value is reproducible and is recorded in provenance.
    return round(ends[0] + 0.02, 6)


def materialize_audio(
    track: AudioTrack,
    destination: str | Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> AudioArtifact:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        request = urllib.request.Request(
            track.source_url,
            headers={"User-Agent": "dancer/0.2 (+https://github.com/KAFKA2306/dancer)"},
        )
        with urllib.request.urlopen(request) as response, path.open("wb") as output:
            shutil.copyfileobj(response, output)
    size_bytes = path.stat().st_size
    if size_bytes != track.source_size_bytes:
        raise ValueError(
            f"audio size mismatch for {track.id}: expected {track.source_size_bytes}, got {size_bytes}"
        )
    source_sha1 = _digest(path, "sha1")
    if source_sha1 != track.source_sha1:
        raise ValueError(
            f"audio SHA-1 mismatch for {track.id}: expected {track.source_sha1}, got {source_sha1}"
        )
    playback_start_offset_seconds = detect_leading_silence(path, runner=runner)
    return AudioArtifact(
        path=str(path.resolve()),
        sha256=_digest(path, "sha256"),
        source_sha1=source_sha1,
        size_bytes=size_bytes,
        playback_start_offset_seconds=playback_start_offset_seconds,
        track=track,
    )


def beat_aligned_duration(track: AudioTrack, requested_seconds: float) -> float:
    if requested_seconds <= 0:
        raise ValueError("requested duration must be positive")
    beat_seconds = 60.0 / track.bpm
    minimum_beats = 4
    beats = max(minimum_beats, round(requested_seconds / beat_seconds))
    return round(beats * beat_seconds, 6)


def mux_audio(
    video_path: str | Path,
    audio: AudioArtifact,
    output_path: str | Path,
    *,
    duration_seconds: float,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> str:
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    runner(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-stream_loop",
            "-1",
            "-ss",
            f"{audio.playback_start_offset_seconds:.6f}",
            "-i",
            audio.path,
            "-filter:a",
            "loudnorm=I=-16:LRA=11:TP=-1.5",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-t",
            f"{duration_seconds:.6f}",
            "-movflags",
            "+faststart",
            str(output),
        ],
        check=True,
    )
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("audio mux did not produce a non-empty output file")
    return str(output.resolve())


def track_provenance(audio: AudioArtifact) -> dict[str, object]:
    payload = asdict(audio.track)
    payload.update(
        {
            "materialized_sha256": audio.sha256,
            "materialized_size_bytes": audio.size_bytes,
            "playback_start_offset_seconds": audio.playback_start_offset_seconds,
        }
    )
    return payload
