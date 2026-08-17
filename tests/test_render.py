import json
import pathlib
import subprocess
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

from dance_renderer import IMAGE2OUTFIT_COMMIT, SIROINO_PATH
from video_generation import generate_video


def test_real_siroino_render_uses_public_motion_and_is_valid_mp4(tmp_path):
    assert IMAGE2OUTFIT_COMMIT == "e6c3f707932fe3cdbddf07e77fa26279a0ff0252"
    assert SIROINO_PATH == "Assets/SiroinoWorks/SiroinoSotai/FBX/SiroinoSotai_PC.fbx"

    artifact = generate_video(
        tmp_path,
        motion_id="93_03",
        duration_seconds=1.0,
        fps=6,
        size=128,
    )

    assert pathlib.Path(artifact.path).is_file()
    assert artifact.codec == "h264"
    assert artifact.width == 128
    assert artifact.height == 128
    assert artifact.duration_seconds == 1.0
    assert artifact.generator == "Blender"
    assert artifact.generator_version == "4.5.12 LTS"
    assert artifact.motion_id == "93_03"
    assert (
        "/09a07f54f3bbb58797325f009282d0b2048a2871/data/093/93_03.bvh"
        in artifact.motion_source_url
    )

    frame_md5 = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", artifact.path, "-f", "framemd5", "-"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    hashes = [
        line.rsplit(",", 1)[-1].strip()
        for line in frame_md5.splitlines()
        if line and not line.startswith("#")
    ]
    assert len(hashes) == 6
    assert len(set(hashes)) > 1

    probe = json.loads(
        subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_streams",
                "-show_format",
                artifact.path,
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    stream = next(item for item in probe["streams"] if item["codec_type"] == "video")
    assert stream["codec_name"] == "h264"
