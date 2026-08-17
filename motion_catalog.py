"""Load and fetch immutable public dance motions from the repository catalog."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path

CATALOG_PATH = Path(__file__).with_name("motions.json")


@dataclass(frozen=True)
class DanceMotion:
    id: str
    subject: int
    category: str
    format: str
    url: str


def load_catalog() -> list[DanceMotion]:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    commit = str(payload["source"]["mirror_commit"])
    motions: list[DanceMotion] = []
    for group in payload["groups"]:
        subject = int(group["subject"])
        category = str(group["category"])
        for motion_id in group["motion_ids"]:
            motions.append(
                DanceMotion(
                    id=str(motion_id),
                    subject=subject,
                    category=category,
                    format="bvh",
                    url=(
                        "https://raw.githubusercontent.com/una-dinosauria/cmu-mocap/"
                        f"{commit}/data/{subject:03d}/{motion_id}.bvh"
                    ),
                )
            )
    return motions


def get_motion(motion_id: str) -> DanceMotion:
    for motion in load_catalog():
        if motion.id == motion_id:
            return motion
    raise ValueError(f"unknown motion id: {motion_id}")


def download_motion(motion_id: str, destination: str | Path) -> DanceMotion:
    motion = get_motion(motion_id)
    if motion.format != "bvh":
        raise ValueError(f"unsupported motion format: {motion.format}")

    path = Path(destination)
    urllib.request.urlretrieve(motion.url, path)
    with path.open("rb") as handle:
        if handle.read(9) != b"HIERARCHY":
            raise ValueError(f"downloaded motion is not BVH: {motion.id}")
    return motion
