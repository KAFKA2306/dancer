"""Command-line entry point for real 3D dance rendering."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from video_generation import generate_video


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--duration-seconds", required=True, type=float)
    parser.add_argument("--fps", required=True, type=int)
    parser.add_argument("--size", required=True, type=int)
    args = parser.parse_args()

    artifact = generate_video(
        args.output_dir,
        duration_seconds=args.duration_seconds,
        fps=args.fps,
        size=args.size,
    )
    print(json.dumps(asdict(artifact), sort_keys=True))


if __name__ == "__main__":
    main()
