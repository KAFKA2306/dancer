from dancer.audio import beat_aligned_duration, get_audio_track, load_audio_catalog


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
    assert len(track.source_sha1) == 40


def test_duration_snaps_to_whole_beats_and_minimum_four_beats():
    track = get_audio_track("maple_leaf_rag_pd_120")
    assert beat_aligned_duration(track, 1.0) == 2.0
    assert beat_aligned_duration(track, 8.1) == 8.0
