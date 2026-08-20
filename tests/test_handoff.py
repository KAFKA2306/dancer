import json
import subprocess
from pathlib import Path

import pytest

from dancer.production import _handoff_to_yt3


class FakeYt3Runner:
    def __init__(self, yt3_root: Path, *, write_receipt: bool = True):
        self.yt3_root = yt3_root
        self.write_receipt = write_receipt
        self.commands = []
        self.run_dir = yt3_root / "runs" / "byosan_money" / "dancer-fixture"
        self.video_path = str((yt3_root / "fixture-video.mp4").resolve())

    def __call__(self, command, **kwargs):
        self.commands.append((command, kwargs))
        if command[:2] == ["bun", "src/scripts/import_dancer_artifact.ts"]:
            payload = {
                "run_id": "byosan_money/dancer-fixture",
                "run_dir": str(self.run_dir.resolve()),
                "publish_video_path": self.video_path,
                "source_artifact_sha256": "a" * 64,
            }
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps(payload) + "\n",
                stderr="",
            )
        if command[:2] == ["task", "publish"]:
            if self.write_receipt:
                publish_dir = self.run_dir / "publish"
                publish_dir.mkdir(parents=True, exist_ok=True)
                (publish_dir / "receipt.json").write_text(
                    json.dumps(
                        {
                            "youtube": {
                                "status": "uploaded",
                                "video_id": "video-fixture",
                                "channel_id": "channel-fixture",
                            }
                        }
                    ),
                    encoding="utf-8",
                )
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        raise AssertionError(command)


def test_offline_yt3_handoff_tracks_run_video_and_receipt(tmp_path):
    yt3_root = tmp_path / "yt3"
    yt3_root.mkdir()
    (yt3_root / "Taskfile.yml").write_text("version: '3'\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    runner = FakeYt3Runner(yt3_root)

    result = _handoff_to_yt3(
        manifest_path=manifest,
        yt3_root=yt3_root,
        profile="byosan",
        runner=runner,
    )

    assert result["status"] == "published_or_scheduled"
    assert result["run_id"] == "byosan_money/dancer-fixture"
    assert result["youtube"]["video_id"] == "video-fixture"
    import_command = runner.commands[0][0]
    assert import_command[-2:] == [str(manifest), "byosan"]
    publish_command = runner.commands[1][0]
    assert publish_command == [
        "task",
        "publish",
        "PROFILE=byosan",
        "--",
        "byosan_money/dancer-fixture",
        runner.video_path,
    ]


def test_offline_yt3_handoff_rejects_missing_publish_receipt(tmp_path):
    yt3_root = tmp_path / "yt3"
    yt3_root.mkdir()
    (yt3_root / "Taskfile.yml").write_text("version: '3'\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    runner = FakeYt3Runner(yt3_root, write_receipt=False)

    with pytest.raises(RuntimeError, match="without receipt.json"):
        _handoff_to_yt3(
            manifest_path=manifest,
            yt3_root=yt3_root,
            profile="byosan",
            runner=runner,
        )
