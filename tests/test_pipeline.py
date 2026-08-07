import pathlib
import sys

# Ensure project root is on the import path
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

from parameter_selection import select_parameters
from video_generation import PipelineMode, ValidationStatus, generate_video
from youtube_upload import UploadStatus, upload_video


def test_full_stub_pipeline(tmp_path):
    avatar, motion, music, background = select_parameters()
    artifact = generate_video(
        avatar,
        motion,
        music,
        background,
        tmp_path,
        mode=PipelineMode.STUB,
    )

    path = pathlib.Path(artifact.path)
    assert path.exists()
    assert path.suffix == ".json"
    assert not list(tmp_path.glob("*.mp4"))
    assert artifact.validation_status is ValidationStatus.NOT_APPLICABLE

    upload = upload_video(artifact, PipelineMode.STUB)
    assert upload.status is UploadStatus.STUBBED
    assert upload.youtube_video_id is None
