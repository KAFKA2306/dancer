"""Command-line entry point for real 3D dance rendering."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .motion_catalog import load_catalog
from .video_generation import generate_video


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list-motions", action="store_true")
    parser.add_argument("--motion-id", default="auto")
    parser.add_argument("--output-dir")
    parser.add_argument("--duration-seconds", type=float)
    parser.add_argument("--fps", type=int)
    parser.add_argument("--size", type=int)
    args = parser.parse_args()

    if args.list_motions:
        print(
            json.dumps(
                [asdict(motion) for motion in load_catalog()],
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return

    for name in ("output_dir", "duration_seconds", "fps", "size"):
        if getattr(args, name) is None:
            parser.error(f"--{name.replace('_', '-')} is required unless --list-motions is used")

    artifact = generate_video(
        args.output_dir,
        motion_id=args.motion_id,
        duration_seconds=args.duration_seconds,
        fps=args.fps,
        size=args.size,
    )
    print(json.dumps(asdict(artifact), sort_keys=True))
