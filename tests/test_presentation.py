from pathlib import Path

import dancer.production as production
from dancer.audio import AudioArtifact, get_audio_track
from dancer.motion_catalog import DanceMotion


def _fixture():
    motion = DanceMotion(
        id="93_03",
        subject=93,
        category="Charleston Dance",
        format="bvh",
        url="https://example.invalid/93_03.bvh",
    )
    track = get_audio_track("maple_leaf_rag_pd_120")
    audio = AudioArtifact(
        path="source.ogg",
        sha256="a" * 64,
        source_sha1=track.source_sha1,
        size_bytes=track.source_size_bytes,
        playback_start_offset_seconds=3.5,
        track=track,
    )
    motion_source = {
        "cmu_terms_url": "https://example.invalid/cmu-terms",
        "conversion_terms_url": "https://example.invalid/conversion-terms",
        "mirror_commit": "0" * 40,
    }
    return motion, audio, motion_source


def test_presentation_audit_detects_metadata_and_thumbnail_contradictions():
    motion, audio, motion_source = _fixture()
    metadata = production._metadata(
        motion=motion,
        audio=audio,
        motion_source=motion_source,
    )
    thumbnail = {"source_video_sha256": "b" * 64}
    audit = production._validate_presentation(
        motion=motion,
        audio=audio,
        metadata=metadata,
        thumbnail=thumbnail,
        selected_video_sha256="b" * 64,
    )
    assert audit["passed"] is True

    bad_metadata = {**metadata, "title": "unrelated video"}
    bad_audit = production._validate_presentation(
        motion=motion,
        audio=audio,
        metadata=bad_metadata,
        thumbnail={"source_video_sha256": "c" * 64},
        selected_video_sha256="b" * 64,
    )
    assert bad_audit["passed"] is False
    assert bad_audit["checks"]["title_matches_motion"] is False
    assert bad_audit["checks"]["thumbnail_matches_selected_video"] is False


def test_thumbnail_candidates_are_three_real_frame_positions(monkeypatch, tmp_path):
    calls = []

    def fake_make_thumbnail(video_path, destination, *, timestamp_seconds):
        calls.append((Path(video_path), Path(destination), timestamp_seconds))
        return {
            "path": str(destination),
            "source_video_sha256": "d" * 64,
            "source_timestamp_seconds": timestamp_seconds,
        }

    monkeypatch.setattr(production, "_make_thumbnail", fake_make_thumbnail)
    candidates, selected = production._make_thumbnail_candidates(
        Path("selected.mp4"),
        tmp_path,
        duration_seconds=8.0,
    )
    assert len(candidates) == 3
    assert [call[2] for call in calls] == [2.0, 4.0, 6.0]
    assert selected["source_timestamp_seconds"] == 4.0
    assert selected["selection_reason"] == "deterministic_middle_frame"
