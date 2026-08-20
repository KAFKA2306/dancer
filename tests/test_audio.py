import subprocess

from dancer.audio import (
    beat_aligned_duration,
    detect_leading_silence,
    get_audio_track,
    load_audio_catalog,
)


def test_audio_catalog_is_rights_aware_and_pinned():
    tracks = load_audio_catalog()
    assert tracks
    assert len({track.id for track in tracks}) == len(tracks)
    track = get_audio_track("maple_leaf_rag_pd_120")
    assert track.source_page_url == "https://commons.wikimedia.org/wiki/File:Scott_Joplin_-_Maple_Leaf_Rag.ogg"
    assert track.license_name.startswith("Public domain")
    assert track.commercial_use is True
    assert track.attribution_required is False
    assert track.bpm == 120.0
    assert track.beat_grid_origin == "first_non_silent_audio"
    assert len(track.source_sha1) == 40


def test_duration_snaps_to_whole_beats_and_minimum_four_beats():
    track = get_audio_track("maple_leaf_rag_pd_120")
    assert beat_aligned_duration(track, 1.0) == 2.0
    assert beat_aligned_duration(track, 8.1) == 8.0


def test_leading_silence_offset_comes_from_ffmpeg_measurement():
    def runner(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="",
            stderr=(
                "[silencedetect] silence_start: 0\n"
                "[silencedetect] silence_end: 3.482 | silence_duration: 3.482\n"
            ),
        )

    assert detect_leading_silence("source.ogg", runner=runner) == 3.502
