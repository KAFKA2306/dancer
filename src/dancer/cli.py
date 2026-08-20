"""Command-line entry points for verified render and autonomous production."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from .motion_catalog import load_catalog
from .production import run_production
from .video_generation import generate_video


def _render_main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="dancer")
    parser.add_argument("--list-motions", action="store_true")
    parser.add_argument("--motion-id", default="auto")
    parser.add_argument("--output-dir")
    parser.add_argument("--duration-seconds", type=float)
    parser.add_argument("--fps", type=int)
    parser.add_argument("--size", type=int)
    args = parser.parse_args(argv)

    if args.list_motions:
        print(json.dumps([asdict(motion) for motion in load_catalog()], ensure_ascii=False, sort_keys=True))
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


def _production_main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="dancer production")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--motion-id", default="auto")
    parser.add_argument("--audio-id", default="auto")
    parser.add_argument("--duration-seconds", type=float, default=8.0)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--candidates", type=int, default=3)
    parser.add_argument("--yt3-root")
    parser.add_argument("--publish-profile", choices=("byosan", "yawa", "humanity"))
    parser.add_argument("--publish-at")
    args = parser.parse_args(argv)
    result = run_production(
        args.output_dir,
        motion_id=args.motion_id,
        audio_id=args.audio_id,
        duration_seconds=args.duration_seconds,
        fps=args.fps,
        width=args.width,
        height=args.height,
        candidates=args.candidates,
        yt3_root=args.yt3_root,
        publish_profile=args.publish_profile,
        publish_at=args.publish_at,
    )
    print(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))


def main() -> None:
    argv = sys.argv[1:]
    if argv and argv[0] == "production":
        _production_main(argv[1:])
        return
    _render_main(argv)
