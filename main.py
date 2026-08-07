"""Entry point for the dance video pipeline."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import yaml

from database import Database
from error_handling import log_error, send_alert
from parameter_selection import select_parameters
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
    config: dict,
    *,
    renderer=None,
    probe_runner=None,
    uploader=None,
):
    """Run one pipeline execution without conflating render and publish success."""
    avatar, motion, music, background = select_parameters()
    mode = PipelineMode(str(config.get("mode", PipelineMode.STUB.value)).upper())
    idempotency_key = build_idempotency_key(avatar, motion, music, background)

    existing = db.get_pipeline_run(idempotency_key)
    if existing is not None:
        return existing

    kwargs = {"mode": mode, "renderer": renderer}
    if probe_runner is not None:
        kwargs["probe_runner"] = probe_runner
    artifact = generate_video(
        avatar,
        motion,
        music,
        background,
        config["output_dir"],
        **kwargs,
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
        generation_status="GENERATED",
        validation_status=artifact.validation_status.value,
        upload_status=upload.status.value,
        youtube_video_id=upload.youtube_video_id,
        error=artifact.validation_error or upload.error,
    )


def main() -> None:
    project_root = Path(__file__).resolve().parent
    with (project_root / "config.yaml").open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)

    logging.basicConfig(filename=project_root / config["log_file"], level=logging.INFO)
    db = Database(project_root / config["database"])
    config = dict(config)
    config["output_dir"] = str(project_root / config["output_dir"])

    try:
        result = process_video(db, config)
        print(
            "Pipeline result: "
            f"mode={result['mode']} "
            f"validation={result['validation_status']} "
            f"upload={result['upload_status']} "
            f"youtube_video_id={result['youtube_video_id'] or 'NONE'}"
        )
    except Exception as exc:  # pragma: no cover - defensive boundary
        log_error(str(exc))
        send_alert(str(exc))
        raise


if __name__ == "__main__":
    main()
