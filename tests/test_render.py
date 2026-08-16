import json
import pathlib
import subprocess
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

from video_generation import generate_video


def test_real_3d_render_moves_and_is_valid_mp4(tmp_path):
    artifact = generate_video(
        tmp_path,
        duration_seconds=1.0,
        fps=8,
        size=160,
    )

    assert pathlib.Path(artifact.path).is_file()
    assert artifact.codec == "h264"
    assert artifact.width == 160
    assert artifact.height == 160
    assert artifact.duration_seconds == 1.0
    assert artifact.generator == "vtk"
    assert artifact.generator_version == "9.6.2"

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
    assert len(hashes) == 8
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
