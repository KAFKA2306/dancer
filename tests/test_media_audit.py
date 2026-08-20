import json
import subprocess

from dancer.media_audit import audit_media


class FakeRunner:
    def __init__(self, *, moving=True):
        self.moving = moving

    def __call__(self, command, **kwargs):
        if command[0] == "ffprobe":
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps(
                    {
                        "format": {"duration": "8.000000"},
                        "streams": [
                            {
                                "codec_type": "video",
                                "codec_name": "h264",
                                "width": 1080,
                                "height": 1920,
                            },
                            {"codec_type": "audio", "codec_name": "aac"},
                        ],
                    }
                ),
                stderr="",
            )
        if "framemd5" in command:
            second = "bbbb" if self.moving else "aaaa"
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=f"#format: frame checksums\n0, 0, 0, 1, 1, aaaa\n0, 1, 1, 1, 1, {second}\n",
                stderr="",
            )
        if "blackdetect=d=0.15:pix_th=0.10" in command:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        if "volumedetect" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="",
                stderr=(
                    "[Parsed_volumedetect] mean_volume: -16.0 dB\n"
                    "[Parsed_volumedetect] max_volume: -1.0 dB\n"
                ),
            )
        raise AssertionError(command)


def test_media_audit_requires_valid_video_audio_motion_and_levels():
    audit = audit_media(
        "candidate.mp4",
        expected_width=1080,
        expected_height=1920,
        expected_duration_seconds=8.0,
        runner=FakeRunner(),
    )
    assert audit.passed is True
    assert audit.video_codec == "h264"
    assert audit.audio_codec == "aac"
    assert audit.unique_video_frame_hashes == 2
    assert audit.reasons == ()


def test_media_audit_rejects_static_video():
    audit = audit_media(
        "candidate.mp4",
        expected_width=1080,
        expected_height=1920,
        expected_duration_seconds=8.0,
        runner=FakeRunner(moving=False),
    )
    assert audit.passed is False
    assert audit.unique_video_frame_hashes == 1
    assert any("no proven frame-to-frame motion" in reason for reason in audit.reasons)
