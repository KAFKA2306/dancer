import json
from pathlib import Path

from motion_catalog import CATALOG_PATH, get_motion, load_catalog


def test_catalog_is_pinned_and_contains_public_dances():
    motions = load_catalog()
    assert len(motions) == 102
    assert len({motion.id for motion in motions}) == len(motions)
    assert all(motion.format == "bvh" for motion in motions)
    assert all(
        "/09a07f54f3bbb58797325f009282d0b2048a2871/" in motion.url
        for motion in motions
    )
    assert get_motion("93_03").category == "Charleston Dance"

    payload = json.loads(Path(CATALOG_PATH).read_text(encoding="utf-8"))
    assert payload["source"]["cmu_terms_url"] == "https://mocap.cs.cmu.edu/"
    assert payload["selection"]["excluded"] == ["49_15 static dance pose"]
