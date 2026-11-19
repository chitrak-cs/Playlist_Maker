"""
history_parser.py
Parses Spotify Streaming History data files (JSON) to find the songs
you have listened to for the highest total number of minutes,
and cross-references them with your saved library and playlists.
"""

import os
import json
import glob
from collections import defaultdict
from typing import Optional


def _normalize_str(text: str) -> str:
    """Helper to normalize song/artist names for matching."""
    if not text:
        return ""
    return "".join(c for c in text.lower() if c.isalnum() or c.isspace()).strip()


def parse_streaming_history(data_path: str, limit: int = 50) -> list[dict]:
    """
    Parses either a directory of Spotify JSON files or a single JSON file.
    Supports both:
      1. Standard Spotify Streaming History ('StreamingHistory_music_*.json' or 'StreamingHistory*.json')
      2. Extended Lifetime Streaming History ('endsong_*.json')

    Returns tracks sorted by total minutes listened descending.
    """
    if os.path.isdir(data_path):
        json_files = glob.glob(os.path.join(data_path, "*.json"))
    elif os.path.isfile(data_path) and data_path.endswith(".json"):
        json_files = [data_path]
    else:
        raise FileNotFoundError(f"Path '{data_path}' is not a valid JSON file or directory.")

    if not json_files:
        raise FileNotFoundError(f"No JSON files found in '{data_path}'.")

    # Map: (norm_artist, norm_title) -> stats dict
    aggregated = defaultdict(lambda: {
        "ms_played": 0,
        "play_count": 0,
        "raw_title": "",
        "raw_artist": "",
        "uri": None
    })

    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"⚠️ Warning: Could not read {file_path}: {e}")
            continue

        if not isinstance(data, list):
            continue

        for entry in data:
            if "master_metadata_track_name" in entry:
                title = entry.get("master_metadata_track_name")
                artist = entry.get("master_metadata_album_artist_name")
                ms = entry.get("ms_played", 0)
                uri = entry.get("spotify_track_uri")
            elif "trackName" in entry:
                title = entry.get("trackName")
                artist = entry.get("artistName")
                ms = entry.get("msPlayed", 0)
                uri = None
            else:
                continue

            if not title or not artist or title == "Unknown Track":
                continue

            if ms and ms > 10000:  # > 10s playback
                key = (_normalize_str(artist), _normalize_str(title))
                aggregated[key]["ms_played"] += ms
                aggregated[key]["play_count"] += 1
                aggregated[key]["raw_title"] = title
                aggregated[key]["raw_artist"] = artist
                if uri and not aggregated[key]["uri"]:
                    aggregated[key]["uri"] = uri

    if not aggregated:
        raise ValueError("No valid song streaming data could be parsed from the provided files.")

    sorted_tracks = sorted(
        aggregated.values(),
        key=lambda item: item["ms_played"],
        reverse=True
    )

    results = []
    for rank, stats in enumerate(sorted_tracks[:limit], start=1):
        minutes = round(stats["ms_played"] / 60000.0, 1)
        results.append({
            "rank": rank,
            "artist": stats["raw_artist"],
            "title": stats["raw_title"],
            "minutes": minutes,
            "streams": f"{minutes:,.1f} mins ({stats['play_count']} plays)",
            "uri": stats["uri"]
        })

    return results


def rank_library_tracks_with_history(library_tracks: list[dict], data_path: str, limit: int = 50) -> list[dict]:
    """
    Cross-references a list of library tracks (Liked Songs + Playlists) with the user's
    downloaded Spotify streaming history to find the songs in their library
    listened to for the most number of minutes.
    """
    if os.path.isdir(data_path):
        json_files = glob.glob(os.path.join(data_path, "*.json"))
    elif os.path.isfile(data_path) and data_path.endswith(".json"):
        json_files = [data_path]
    else:
        raise FileNotFoundError(f"Path '{data_path}' is not a valid JSON file or directory.")

    if not json_files:
        raise FileNotFoundError(f"No JSON files found in '{data_path}'.")

    # Map history plays:
    # 1. by URI
    # 2. by (normalized_artist, normalized_title)
    uri_stats = defaultdict(lambda: {"ms": 0, "plays": 0})
    name_stats = defaultdict(lambda: {"ms": 0, "plays": 0})

    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        if not isinstance(data, list):
            continue

        for entry in data:
            if "master_metadata_track_name" in entry:
                title = entry.get("master_metadata_track_name")
                artist = entry.get("master_metadata_album_artist_name")
                ms = entry.get("ms_played", 0)
                uri = entry.get("spotify_track_uri")
            elif "trackName" in entry:
                title = entry.get("trackName")
                artist = entry.get("artistName")
                ms = entry.get("msPlayed", 0)
                uri = None
            else:
                continue

            if not title or not artist or ms <= 10000:
                continue

            if uri:
                uri_stats[uri]["ms"] += ms
                uri_stats[uri]["plays"] += 1

            key = (_normalize_str(artist), _normalize_str(title))
            name_stats[key]["ms"] += ms
            name_stats[key]["plays"] += 1

    # Match each library track
    matched_tracks = []
    for track in library_tracks:
        uri = track.get("uri")
        title = track.get("title", "")
        artist = track.get("artist", "")
        key = (_normalize_str(artist), _normalize_str(title))

        ms = 0
        plays = 0
        if uri and uri in uri_stats:
            ms = uri_stats[uri]["ms"]
            plays = uri_stats[uri]["plays"]
        elif key in name_stats:
            ms = name_stats[key]["ms"]
            plays = name_stats[key]["plays"]

        if ms > 0:
            minutes = round(ms / 60000.0, 1)
            sources_str = ", ".join(track.get("sources", ["Library"]))
            matched_tracks.append({
                "title": title,
                "artist": artist,
                "uri": uri,
                "ms": ms,
                "minutes": minutes,
                "plays": plays,
                "sources": sources_str,
                "streams": f"{minutes:,.1f} mins ({plays} plays) [Found in: {sources_str}]"
            })

    if not matched_tracks:
        raise ValueError("None of your library tracks could be matched in the streaming history files.")

    # Sort descending by total milliseconds listened
    matched_tracks.sort(key=lambda t: t["ms"], reverse=True)

    for rank, t in enumerate(matched_tracks[:limit], start=1):
        t["rank"] = rank

    return matched_tracks[:limit]
