"""
test_music_ranker.py — Comprehensive unit tests for MusicRanker.
"""
from app.services.music_ranker import music_ranker


def test_original_ranked_over_remix():
    candidates = [
        {
            "name": "Believer - Cedric Gervais Remix",
            "artists": [{"name": "Imagine Dragons"}, {"name": "Cedric Gervais"}],
            "album": {"name": "Believer (Remix)", "album_type": "single"},
            "popularity": 65,
        },
        {
            "name": "Believer",
            "artists": [{"name": "Imagine Dragons"}],
            "album": {"name": "Evolve", "album_type": "album"},
            "popularity": 88,
        },
        {
            "name": "Believer - Karaoke Version",
            "artists": [{"name": "Sing King"}],
            "album": {"name": "Karaoke Hits", "album_type": "album"},
            "popularity": 30,
        },
    ]

    ranked = music_ranker.rank_tracks(candidates, query="Believer", artist_hint="Imagine Dragons")
    assert len(ranked) == 3
    # Original should be ranked #1
    assert ranked[0]["name"] == "Believer"
    assert ranked[0]["album"]["name"] == "Evolve"
    assert ranked[0]["_ranking_score"] > ranked[1]["_ranking_score"]


def test_artist_matching_preference():
    candidates = [
        {
            "name": "Believer",
            "artists": [{"name": "Different Artist"}],
            "album": {"name": "Other Album", "album_type": "album"},
            "popularity": 50,
        },
        {
            "name": "Believer",
            "artists": [{"name": "Imagine Dragons"}],
            "album": {"name": "Evolve", "album_type": "album"},
            "popularity": 90,
        },
    ]

    ranked = music_ranker.rank_tracks(candidates, query="Believer by Imagine Dragons")
    assert ranked[0]["artists"][0]["name"] == "Imagine Dragons"


def test_tamil_pattuma_matching():
    candidates = [
        {
            "name": "Pattuma - Lofi Chill Version",
            "artists": [{"name": "Lo-Fi Collective"}],
            "album": {"name": "Tamil Lo-Fi", "album_type": "album"},
            "popularity": 40,
        },
        {
            "name": "Pattuma",
            "artists": [{"name": "Sai Abhyankkar"}],
            "album": {"name": "Pattuma", "album_type": "single"},
            "popularity": 75,
        },
        {
            "name": "Pattuma Cover",
            "artists": [{"name": "Cover Singer"}],
            "album": {"name": "Acoustic Covers", "album_type": "single"},
            "popularity": 35,
        },
    ]

    ranked = music_ranker.rank_tracks(candidates, query="Play Pattuma", artist_hint="Sai Abhyankkar", language_hint="Tamil")
    assert ranked[0]["name"] == "Pattuma"
    assert ranked[0]["artists"][0]["name"] == "Sai Abhyankkar"
    assert "exact_title_match (+120)" in ranked[0]["_ranking_reasons"]


def test_explicit_remix_query_not_penalized():
    candidates = [
        {
            "name": "Believer",
            "artists": [{"name": "Imagine Dragons"}],
            "album": {"name": "Evolve", "album_type": "album"},
            "popularity": 85,
        },
        {
            "name": "Believer - Cedric Gervais Remix",
            "artists": [{"name": "Imagine Dragons"}, {"name": "Cedric Gervais"}],
            "album": {"name": "Believer (Remix)", "album_type": "single"},
            "popularity": 70,
        },
    ]

    ranked = music_ranker.rank_tracks(candidates, query="Believer remix")
    # When user asks for remix, the remix should be preferred
    assert "Remix" in ranked[0]["name"]


def test_empty_candidates_handling():
    ranked = music_ranker.rank_tracks([], query="nonexistent")
    assert ranked == []
