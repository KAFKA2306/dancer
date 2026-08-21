from pathlib import Path

from dancer import video_generation
from dancer.motion_catalog import DanceMotion


def test_generate_all_videos_uses_one_directory_per_catalog_motion(monkeypatch, tmp_path):
    motions = [
        DanceMotion("01_01", 1, "walk", "bvh", "https://example.test/01_01.bvh"),
        DanceMotion("02_02", 2, "dance", "bvh", "https://example.test/02_02.bvh"),
    ]
    calls = []

    monkeypatch.setattr(video_generation, "load_catalog", lambda: motions)

    def fake_generate_video(output_dir, **kwargs):
        calls.append((Path(output_dir), kwargs))
        return kwargs["motion_id"]

    monkeypatch.setattr(video_generation, "generate_video", fake_generate_video)

    artifacts = video_generation.generate_all_videos(
        tmp_path,
        duration_seconds=1.0,
        fps=6,
        size=128,
    )

    assert artifacts == ["01_01", "02_02"]
    assert [call[0] for call in calls] == [
        tmp_path / "motions" / "01_01",
        tmp_path / "motions" / "02_02",
    ]
    assert all(call[1]["samples"] == 8 for call in calls)
