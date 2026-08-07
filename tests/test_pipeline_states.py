import pathlib
import sqlite3
import subprocess
import sys

import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

from database import Database
from video_generation import GeneratedArtifact, PipelineMode, ValidationStatus, generate_video
from youtube_upload import UploadStatus, upload_video


def test_stub_never_creates_mp4_or_youtube_id(tmp_path):
    artifact = generate_video("a", "m", "music", "bg", tmp_path, mode=PipelineMode.STUB)
    upload = upload_video(artifact, PipelineMode.STUB)

    assert artifact.path.endswith(".stub.json")
    assert not list(tmp_path.glob("*.mp4"))
    assert artifact.validation_status is ValidationStatus.NOT_APPLICABLE
    assert upload.status is UploadStatus.STUBBED
    assert upload.youtube_video_id is None


def test_invalid_media_never_reaches_uploaded(tmp_path):
    video_path = tmp_path / "invalid.mp4"

    def renderer(*_args):
        video_path.write_text("not a media container", encoding="utf-8")
        return str(video_path)

    def rejected_probe(*_args, **_kwargs):
        return subprocess.CompletedProcess([], 1, stdout="", stderr="invalid data")

    artifact = generate_video(
        "a",
        "m",
        "music",
        "bg",
        tmp_path,
        mode=PipelineMode.YOUTUBE_PUBLISH,
        renderer=renderer,
        probe_runner=rejected_probe,
    )
    upload = upload_video(
        artifact,
        PipelineMode.YOUTUBE_PUBLISH,
        uploader=lambda _path: {"id": "must-not-be-used"},
    )

    assert artifact.validation_status is ValidationStatus.INVALID
    assert upload.status is UploadStatus.FAILED
    assert upload.youtube_video_id is None


def valid_artifact(tmp_path):
    path = tmp_path / "valid.mp4"
    path.write_bytes(b"fixture")
    return GeneratedArtifact(
        path=str(path),
        media_type="video/mp4",
        generator="fixture",
        generator_version="1",
        duration_seconds=1.0,
        width=16,
        height=16,
        codec="h264",
        sha256="fixture-sha",
        validation_status=ValidationStatus.VALID,
    )


def test_upload_failure_is_not_reported_as_uploaded(tmp_path):
    artifact = valid_artifact(tmp_path)

    def failed_upload(_path):
        raise RuntimeError("provider failed")

    result = upload_video(artifact, PipelineMode.YOUTUBE_PUBLISH, uploader=failed_upload)
    assert result.status is UploadStatus.FAILED
    assert result.youtube_video_id is None
    assert "provider failed" in result.error


def test_only_success_response_supplies_youtube_id(tmp_path):
    artifact = valid_artifact(tmp_path)
    result = upload_video(
        artifact,
        PipelineMode.YOUTUBE_PUBLISH,
        uploader=lambda _path: {"id": "real-api-id"},
    )
    assert result.status is UploadStatus.UPLOADED
    assert result.youtube_video_id == "real-api-id"


def test_database_separates_states_and_rejects_duplicate_idempotency_key(tmp_path):
    db = Database(tmp_path / "test.db")
    kwargs = dict(
        idempotency_key="same-input",
        mode=PipelineMode.STUB.value,
        avatar="a",
        motion="m",
        music="music",
        background="bg",
        artifact_path="out.stub.json",
        artifact_sha256="abc",
        generation_status="GENERATED",
        validation_status=ValidationStatus.NOT_APPLICABLE.value,
        upload_status=UploadStatus.STUBBED.value,
        youtube_video_id=None,
        error=None,
    )
    row = db.save_pipeline_run(**kwargs)
    assert row["generation_status"] == "GENERATED"
    assert row["validation_status"] == "NOT_APPLICABLE"
    assert row["upload_status"] == "STUBBED"
    assert row["youtube_video_id"] is None

    with pytest.raises(sqlite3.IntegrityError):
        db.save_pipeline_run(**kwargs)
