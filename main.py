"""Strict orchestration for real render and optional YouTube publication."""

from __future__ import annotations

import hashlib
import json
import subprocess
from typing import Callable

from database import Database
from video_generation import PipelineMode, generate_video
from youtube_upload import upload_video


def build_idempotency_key(avatar: str, motion: str, music: str, background: str) -> str:
    payload = json.dumps(
        {
            "avatar": avatar,
            "motion": motion,
            "music": music,
            "background": background,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def process_video(
    db: Database,
    *,
    avatar: str,
    motion: str,
    music: str,
    background: str,
    output_dir: str,
    mode: PipelineMode,
    renderer: Callable[[str, str, str, str, str], str],
    probe_runner=subprocess.run,
    uploader=None,
):
    """Run one real pipeline execution and persist only a completed run."""
    idempotency_key = build_idempotency_key(avatar, motion, music, background)
    existing = db.get_pipeline_run(idempotency_key)
    if existing is not None:
        return existing

    artifact = generate_video(
        avatar,
        motion,
        music,
        background,
        output_dir,
        renderer=renderer,
        probe_runner=probe_runner,
    )
    upload = upload_video(artifact, mode, uploader=uploader)

    return db.save_pipeline_run(
        idempotency_key=idempotency_key,
        mode=mode.value,
        avatar=avatar,
        motion=motion,
        music=music,
        background=background,
        artifact_path=artifact.path,
        artifact_sha256=artifact.sha256,
        upload_status=upload.status.value,
        youtube_video_id=upload.youtube_video_id,
    )
