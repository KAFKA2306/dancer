"""One-command autonomous production from verified motion to an auditable publish artifact."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .audio import (
    AudioArtifact,
    beat_aligned_duration,
    get_audio_track,
    materialize_audio,
    mux_audio,
    track_provenance,
)
from .dance_renderer import (
    CAMERA_PRESETS,
    IMAGE2OUTFIT_COMMIT,
    SIROINO_BLOB_SHA,
    SIROINO_LICENSE,
    SIROINO_TERMS_URL,
    SIROINO_URL,
)
from .media_audit import MediaAudit, audit_media, write_audit
from .motion_catalog import CATALOG_PATH, DanceMotion, get_motion
from .video_generation import GeneratedArtifact, _sha256, generate_video

PRODUCTION_CONTRACT_VERSION = 1
YOUTUBE_THUMBNAIL_MAX_BYTES = 2 * 1024 * 1024
THUMBNAIL_RATIOS = (0.25, 0.50, 0.75)


@dataclass(frozen=True)
class ProductionResult:
    run_id: str
    run_dir: str
    manifest_path: str
    selected_video_path: str
    selected_video_sha256: str
    thumbnail_path: str
    metadata_path: str
    publish_status: str


def _json_dump(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _catalog_source() -> dict[str, Any]:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    source = payload.get("source")
    if not isinstance(source, dict):
        raise ValueError("motion catalog source metadata is missing")
    required = ("cmu_terms_url", "conversion_terms_url", "mirror_commit")
    missing = [key for key in required if not source.get(key)]
    if missing:
        raise ValueError(f"motion catalog source metadata is incomplete: {missing}")
    return source


def _stable_key(payload: dict[str, object]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _candidate_score(artifact: GeneratedArtifact, audit: MediaAudit) -> float:
    if not audit.passed or artifact.framing_margin < 0:
        return float("-inf")
    return artifact.framing_margin - min(
        artifact.camera_max_step_per_frame, 1.0
    ) * 0.001


def _reuse_candidate(candidate_path: Path) -> dict[str, Any] | None:
    if not candidate_path.is_file():
        return None
    payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    video_path = Path(str(payload.get("video_path") or ""))
    expected_hash = str(payload.get("video_sha256") or "")
    if not video_path.is_file() or not expected_hash:
        return None
    if _sha256(video_path) != expected_hash:
        return None
    if not bool(payload.get("audit", {}).get("passed")):
        return None
    return payload


def _render_candidate(
    *,
    candidate_dir: Path,
    motion: DanceMotion,
    audio: AudioArtifact,
    duration_seconds: float,
    fps: int,
    width: int,
    height: int,
    camera_preset: str,
) -> dict[str, Any]:
    candidate_json = candidate_dir / "candidate.json"
    reused = _reuse_candidate(candidate_json)
    if reused is not None:
        return reused

    candidate_dir.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(candidate_dir / "siroino-render", ignore_errors=True)
    artifact = generate_video(
        candidate_dir,
        motion_id=motion.id,
        duration_seconds=duration_seconds,
        fps=fps,
        width=width,
        height=height,
        camera_preset=camera_preset,
    )
    publish_video = Path(
        mux_audio(
            artifact.path,
            audio,
            candidate_dir / "publish.mp4",
            duration_seconds=duration_seconds,
        )
    )
    audit = audit_media(
        publish_video,
        expected_width=width,
        expected_height=height,
        expected_duration_seconds=duration_seconds,
    )
    if artifact.framing_margin < 0:
        audit = MediaAudit(
            **{
                **asdict(audit),
                "passed": False,
                "reasons": tuple(audit.reasons)
                + (
                    "body framing crosses image boundary: "
                    f"margin={artifact.framing_margin:.5f}",
                ),
            }
        )
    write_audit(audit, candidate_dir / "audit.json")
    payload = {
        "camera_preset": camera_preset,
        "render": asdict(artifact),
        "audit": asdict(audit),
        "score": _candidate_score(artifact, audit),
        "video_path": str(publish_video.resolve()),
        "video_sha256": _sha256(publish_video),
        "video_size_bytes": publish_video.stat().st_size,
    }
    _json_dump(candidate_json, payload)
    return payload


def _make_thumbnail(
    video_path: Path,
    destination: Path,
    *,
    timestamp_seconds: float,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    transform = (
        "scale=1280:720:force_original_aspect_ratio=decrease,"
        "pad=1280:720:(ow-iw)/2:(oh-ih)/2"
    )
    runner(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-ss",
            f"{timestamp_seconds:.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-vf",
            transform,
            "-q:v",
            "4",
            str(destination),
        ],
        check=True,
    )
    if not destination.is_file() or destination.stat().st_size == 0:
        raise RuntimeError("thumbnail extraction failed")
    if destination.stat().st_size > YOUTUBE_THUMBNAIL_MAX_BYTES:
        raise ValueError(
            "thumbnail exceeds YouTube 2 MB limit: "
            f"{destination.stat().st_size} bytes"
        )
    return {
        "path": str(destination.resolve()),
        "sha256": _sha256(destination),
        "size_bytes": destination.stat().st_size,
        "source_video_sha256": _sha256(video_path),
        "source_timestamp_seconds": round(timestamp_seconds, 6),
        "width": 1280,
        "height": 720,
        "mime_type": "image/jpeg",
        "transform": transform,
        "text_overlay": None,
    }


def _make_thumbnail_candidates(
    video_path: Path,
    presentation_dir: Path,
    *,
    duration_seconds: float,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    candidates = [
        _make_thumbnail(
            video_path,
            presentation_dir / f"thumbnail-{index}.jpg",
            timestamp_seconds=max(0.0, duration_seconds * ratio),
        )
        for index, ratio in enumerate(THUMBNAIL_RATIOS)
    ]
    # The middle frame is the deterministic baseline. All candidates remain in
    # the manifest so a future policy can choose differently without losing evidence.
    selected = dict(candidates[len(candidates) // 2])
    selected["selection_reason"] = "deterministic_middle_frame"
    return candidates, selected


def _metadata(
    *,
    motion: DanceMotion,
    audio: AudioArtifact,
    motion_source: dict[str, Any],
) -> dict[str, object]:
    title = f"{motion.category} — SiroinoSotai dance ({motion.id})"[:100]
    attribution = ""
    if audio.track.attribution_required:
        attribution = (
            f"\nAudio attribution: {audio.track.creator} — {audio.track.title} "
            f"({audio.track.license_url})"
        )
    description = (
        f"Motion: {motion.category} / {motion.id}\n"
        f"Motion source: {motion.url}\n"
        f"CMU terms: {motion_source['cmu_terms_url']}\n"
        f"BVH conversion terms: {motion_source['conversion_terms_url']}\n\n"
        "Avatar: SiroinoSotai_PC\n"
        f"Avatar source: {SIROINO_URL}\n"
        f"Avatar terms (CC0): {SIROINO_TERMS_URL}\n\n"
        f"Audio: {audio.track.title} — {audio.track.creator}\n"
        f"Audio source: {audio.track.source_page_url}\n"
        f"Audio license: {audio.track.license_name} — "
        f"{audio.track.license_url}{attribution}"
    )
    return {
        "title": title,
        "description": description[:5000],
        "tags": [
            "3D dance",
            "Blender",
            "SiroinoSotai",
            motion.category,
            motion.id,
        ],
        "thumbnail_title": title,
        "sources": {
            "motion": motion.url,
            "avatar": SIROINO_URL,
            "audio": audio.track.source_page_url,
        },
    }


def _validate_presentation(
    *,
    motion: DanceMotion,
    audio: AudioArtifact,
    metadata: dict[str, object],
    thumbnail: dict[str, object],
    selected_video_sha256: str,
) -> dict[str, object]:
    title = str(metadata.get("title") or "")
    description = str(metadata.get("description") or "")
    tags = {str(tag) for tag in metadata.get("tags", [])}
    sources = metadata.get("sources")
    source_map = sources if isinstance(sources, dict) else {}
    checks = {
        "title_matches_motion": motion.id in title and motion.category in title,
        "tags_match_motion": motion.id in tags and motion.category in tags,
        "thumbnail_title_matches_title": metadata.get("thumbnail_title") == title,
        "description_has_motion_source": motion.url in description,
        "description_has_avatar_source": SIROINO_URL in description,
        "description_has_audio_identity": (
            audio.track.title in description and audio.track.creator in description
        ),
        "description_has_audio_terms": (
            audio.track.source_page_url in description
            and audio.track.license_url in description
        ),
        "source_map_matches_motion": source_map.get("motion") == motion.url,
        "source_map_matches_avatar": source_map.get("avatar") == SIROINO_URL,
        "source_map_matches_audio": (
            source_map.get("audio") == audio.track.source_page_url
        ),
        "thumbnail_matches_selected_video": (
            thumbnail.get("source_video_sha256") == selected_video_sha256
        ),
        "required_attribution_present": (
            not audio.track.attribution_required
            or audio.track.creator in description
        ),
    }
    return {"passed": all(checks.values()), "checks": checks}


def _compliance(
    *,
    motion: DanceMotion,
    audio: AudioArtifact,
    motion_source: dict[str, Any],
    metadata: dict[str, object],
) -> dict[str, object]:
    checks = {
        "motion_source_https": motion.url.startswith("https://"),
        "motion_terms_present": (
            str(motion_source.get("cmu_terms_url", "")).startswith("https://")
            and str(motion_source.get("conversion_terms_url", "")).startswith(
                "https://"
            )
        ),
        "avatar_source_pinned": (
            IMAGE2OUTFIT_COMMIT in SIROINO_URL and bool(SIROINO_BLOB_SHA)
        ),
        "avatar_terms_present": (
            SIROINO_TERMS_URL.startswith("https://")
            and SIROINO_LICENSE == "CC0-1.0"
        ),
        "audio_source_verified": audio.source_sha1 == audio.track.source_sha1,
        "audio_commercial_use": audio.track.commercial_use,
        "audio_terms_present": audio.track.license_url.startswith("https://"),
        "required_attribution_present": (
            not audio.track.attribution_required
            or audio.track.creator in str(metadata.get("description") or "")
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "contains_synthetic_media": False,
        "synthetic_media_reason": (
            "The output is a visibly stylized 3D character animation; this pipeline "
            "does not create a realistic depiction of a real person, place, scene, "
            "or event."
        ),
        "external_generative_video_provider": None,
    }


def _resume_manifest(manifest_path: Path) -> dict[str, Any] | None:
    if not manifest_path.is_file():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected = manifest.get("selected") or {}
    video_path = Path(str(selected.get("video_path") or ""))
    expected_hash = str(selected.get("video_sha256") or "")
    if not video_path.is_file() or not expected_hash:
        return None
    if _sha256(video_path) != expected_hash:
        raise ValueError("existing manifest video hash mismatch")
    if not bool(manifest.get("presentation_audit", {}).get("passed")):
        return None
    if not bool(manifest.get("compliance", {}).get("passed")):
        raise ValueError("existing manifest failed compliance gate")
    return manifest


def _handoff_to_yt3(
    *,
    manifest_path: Path,
    yt3_root: Path,
    profile: str,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    if profile not in {"byosan", "yawa", "humanity"}:
        raise ValueError("YT3 profile must be one of: byosan, yawa, humanity")
    if not (yt3_root / "Taskfile.yml").is_file():
        raise FileNotFoundError(f"YT3 Taskfile not found under {yt3_root}")
    revision_result = runner(
        ["git", "rev-parse", "HEAD"],
        cwd=yt3_root,
        capture_output=True,
        text=True,
        check=True,
    )
    yt3_revision = revision_result.stdout.strip()
    if len(yt3_revision) != 40 or any(
        ch not in "0123456789abcdef" for ch in yt3_revision.lower()
    ):
        raise RuntimeError(
            f"YT3 checkout revision is not a full commit SHA: {yt3_revision!r}"
        )
    imported = runner(
        [
            "bun",
            "src/scripts/import_dancer_artifact.ts",
            str(manifest_path),
            profile,
        ],
        cwd=yt3_root,
        capture_output=True,
        text=True,
        check=True,
    )
    lines = [
        line.strip()
        for line in imported.stdout.splitlines()
        if line.strip().startswith("{")
    ]
    if not lines:
        raise RuntimeError("YT3 import did not return machine-readable result")
    receipt = json.loads(lines[-1])
    run_id = str(receipt.get("run_id") or "")
    publish_video_path = str(receipt.get("publish_video_path") or "")
    if not run_id or not publish_video_path:
        raise RuntimeError(
            "YT3 import result is missing run_id or publish_video_path"
        )
    runner(
        [
            "task",
            "publish",
            f"PROFILE={profile}",
            "--",
            run_id,
            publish_video_path,
        ],
        cwd=yt3_root,
        check=True,
    )
    run_dir = Path(str(receipt.get("run_dir") or ""))
    yt3_receipt = run_dir / "publish" / "receipt.json"
    if not yt3_receipt.is_file():
        raise RuntimeError("YT3 publish completed without receipt.json")
    published = json.loads(yt3_receipt.read_text(encoding="utf-8"))
    youtube = published.get("youtube") or {}
    if not youtube.get("video_id"):
        raise RuntimeError("YT3 publish receipt is missing YouTube video id")
    return {
        "status": "published_or_scheduled",
        "profile": profile,
        "run_id": run_id,
        "yt3_revision": yt3_revision,
        "yt3_receipt_path": str(yt3_receipt.resolve()),
        "youtube": youtube,
    }


def run_production(
    output_dir: str | Path,
    *,
    motion_id: str = "auto",
    audio_id: str = "auto",
    duration_seconds: float = 8.0,
    fps: int = 24,
    width: int = 1080,
    height: int = 1920,
    candidates: int = 3,
    yt3_root: str | Path | None = None,
    publish_profile: str | None = None,
    publish_at: str | None = None,
) -> ProductionResult:
    if candidates < 1 or candidates > len(CAMERA_PRESETS):
        raise ValueError(
            f"candidates must be between 1 and {len(CAMERA_PRESETS)}"
        )
    if fps <= 0 or width <= 0 or height <= 0 or width % 2 or height % 2:
        raise ValueError(
            "fps must be positive and dimensions must be positive even integers"
        )
    if bool(yt3_root) != bool(publish_profile):
        raise ValueError("yt3_root and publish_profile must be provided together")
    if publish_at:
        parsed = datetime.fromisoformat(publish_at.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("publish_at must include a timezone offset")
        if parsed <= datetime.now(timezone.utc):
            raise ValueError("publish_at must be in the future")

    motion = get_motion(motion_id)
    track = get_audio_track(audio_id)
    duration = beat_aligned_duration(track, duration_seconds)
    key_input: dict[str, object] = {
        "contract_version": PRODUCTION_CONTRACT_VERSION,
        "motion_id": motion.id,
        "motion_url": motion.url,
        "audio_id": track.id,
        "audio_source_sha1": track.source_sha1,
        "duration_seconds": duration,
        "fps": fps,
        "width": width,
        "height": height,
        "candidates": candidates,
        "publish_profile": publish_profile or "none",
        "publish_at": publish_at or "none",
    }
    idempotency_key = _stable_key(key_input)
    run_id = f"dancer-{idempotency_key[:20]}"
    run_dir = Path(output_dir).resolve() / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / "manifest.json"
    existing = _resume_manifest(manifest_path)

    if existing is None:
        motion_source = _catalog_source()
        audio = materialize_audio(track, run_dir / "audio" / "source.ogg")
        candidate_results = []
        for index, camera_preset in enumerate(CAMERA_PRESETS[:candidates]):
            candidate_results.append(
                _render_candidate(
                    candidate_dir=(
                        run_dir
                        / "candidates"
                        / f"{index:02d}-{camera_preset}"
                    ),
                    motion=motion,
                    audio=audio,
                    duration_seconds=duration,
                    fps=fps,
                    width=width,
                    height=height,
                    camera_preset=camera_preset,
                )
            )
        valid = [
            candidate
            for candidate in candidate_results
            if bool(candidate.get("audit", {}).get("passed"))
            and float(candidate.get("score", float("-inf")))
            != float("-inf")
        ]
        if not valid:
            raise RuntimeError("all render candidates failed deterministic audit")
        selected = max(valid, key=lambda item: float(item["score"]))
        selected_path = Path(str(selected["video_path"]))
        thumbnail_candidates, thumbnail = _make_thumbnail_candidates(
            selected_path,
            run_dir / "presentation",
            duration_seconds=duration,
        )
        metadata = _metadata(
            motion=motion,
            audio=audio,
            motion_source=motion_source,
        )
        metadata_path = run_dir / "presentation" / "metadata.json"
        _json_dump(metadata_path, metadata)
        presentation_audit = _validate_presentation(
            motion=motion,
            audio=audio,
            metadata=metadata,
            thumbnail=thumbnail,
            selected_video_sha256=str(selected["video_sha256"]),
        )
        if not bool(presentation_audit["passed"]):
            raise RuntimeError("metadata/thumbnail contradiction gate failed")
        compliance = _compliance(
            motion=motion,
            audio=audio,
            motion_source=motion_source,
            metadata=metadata,
        )
        if not bool(compliance["passed"]):
            raise RuntimeError("rights/provenance compliance gate failed")
        manifest = {
            "schema_version": PRODUCTION_CONTRACT_VERSION,
            "run_id": run_id,
            "idempotency_key": idempotency_key,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "inputs": key_input,
            "motion": {
                "id": motion.id,
                "category": motion.category,
                "source_url": motion.url,
                "source": motion_source,
            },
            "avatar": {
                "source_url": SIROINO_URL,
                "source_commit": IMAGE2OUTFIT_COMMIT,
                "source_blob_sha": SIROINO_BLOB_SHA,
                "terms_url": SIROINO_TERMS_URL,
                "license": SIROINO_LICENSE,
            },
            "audio": track_provenance(audio),
            "candidates": candidate_results,
            "selected": selected,
            "thumbnail_candidates": thumbnail_candidates,
            "thumbnail": thumbnail,
            "metadata": {**metadata, "path": str(metadata_path.resolve())},
            "presentation_audit": presentation_audit,
            "caption_path": None,
            "publish_at": publish_at,
            "compliance": compliance,
            "publication": {"status": "NOT_ATTEMPTED"},
        }
        _json_dump(manifest_path, manifest)
    else:
        manifest = existing

    publication = dict(manifest.get("publication") or {})
    if yt3_root is not None and publish_profile is not None:
        publication = _handoff_to_yt3(
            manifest_path=manifest_path,
            yt3_root=Path(yt3_root).resolve(),
            profile=publish_profile,
        )
        manifest["publication"] = publication
        _json_dump(manifest_path, manifest)

    selected = manifest["selected"]
    thumbnail = manifest["thumbnail"]
    metadata = manifest["metadata"]
    return ProductionResult(
        run_id=run_id,
        run_dir=str(run_dir),
        manifest_path=str(manifest_path),
        selected_video_path=str(selected["video_path"]),
        selected_video_sha256=str(selected["video_sha256"]),
        thumbnail_path=str(thumbnail["path"]),
        metadata_path=str(metadata["path"]),
        publish_status=str(publication.get("status") or "NOT_ATTEMPTED"),
    )
