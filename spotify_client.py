"""
spotify_client.py
Handles Spotify authentication, searching tracks, fetching personal top tracks,
scanning user library & playlists, and creating/populating playlists using Spotipy.
Uses SpotifyPKCE (Proof Key for Code Exchange) to ensure reliable OAuth authentication.
"""

import os
import re
from typing import Optional
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyPKCE

# Load environment variables from .env file
load_dotenv()


class SpotifyManager:
    """Manager class to handle all Spotify API interactions."""

    def __init__(self):
        client_id = os.getenv("SPOTIPY_CLIENT_ID")
        redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8080/callback")

        if not client_id or "your_" in client_id:
            raise ValueError(
                "Missing or invalid SPOTIPY_CLIENT_ID in .env file.\n"
                "Please configure SPOTIPY_CLIENT_ID in your .env file."
            )

        # Scopes required for:
        # - Creating/modifying playlists
        # - Reading user's top tracks
        # - Reading Liked Songs (user-library-read)
        # - Reading user's own playlists and saved/followed playlists (playlist-read-private, playlist-read-collaborative)
        scope = (
            "playlist-modify-public "
            "playlist-modify-private "
            "user-top-read "
            "user-library-read "
            "playlist-read-private "
            "playlist-read-collaborative"
        )

        # Using SpotifyPKCE flow for robust modern OAuth
        auth_manager = SpotifyPKCE(
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
            open_browser=False
        )

        self.sp = spotipy.Spotify(auth_manager=auth_manager)
        self.user_id = self.sp.me()["id"]

    # ---------------------------------------------------------
    # Library & Playlist Scanning Methods
    # ---------------------------------------------------------

    def get_all_liked_songs(self, max_tracks: int = 1500) -> list[dict]:
        """Fetches tracks saved in the user's Liked Songs library."""
        tracks = []
        limit = 50
        offset = 0
        print("  📥 Fetching Liked Songs...")
        while offset < max_tracks:
            try:
                batch = self.sp.current_user_saved_tracks(limit=limit, offset=offset)
            except Exception as e:
                print(f"  ⚠️ Warning fetching liked songs at offset {offset}: {e}")
                break

            items = batch.get("items", [])
            if not items:
                break

            for item in items:
                track = item.get("track")
                if not track or not track.get("id"):
                    continue
                artists = ", ".join([a["name"] for a in track["artists"]])
                tracks.append({
                    "id": track["id"],
                    "title": track["name"],
                    "artist": artists,
                    "uri": track["uri"],
                    "duration_ms": track.get("duration_ms", 0),
                    "source": "Liked Songs"
                })

            offset += len(items)
            if len(items) < limit:
                break

        print(f"  ✓ Retrieved {len(tracks)} Liked Songs.")
        return tracks

    def get_all_user_playlists(self, max_playlists: int = 50) -> list[dict]:
        """Fetches all playlists in the user's library (both created and followed)."""
        playlists = []
        limit = 50
        offset = 0
        while offset < max_playlists:
            try:
                batch = self.sp.current_user_playlists(limit=limit, offset=offset)
            except Exception as e:
                print(f"  ⚠️ Warning fetching playlists at offset {offset}: {e}")
                break

            items = batch.get("items", [])
            if not items:
                break

            for pl in items:
                if pl and pl.get("id"):
                    playlists.append({
                        "id": pl["id"],
                        "name": pl["name"],
                        "owner": pl.get("owner", {}).get("display_name", "Unknown"),
                        "total_tracks": pl.get("tracks", {}).get("total", 0)
                    })

            offset += len(items)
            if len(items) < limit:
                break

        return playlists

    def get_playlist_tracks(self, playlist_id: str, playlist_name: str, max_tracks: int = 300) -> list[dict]:
        """Fetches tracks from a single playlist with pagination."""
        tracks = []
        limit = 100
        offset = 0
        while offset < max_tracks:
            try:
                batch = self.sp.playlist_items(
                    playlist_id,
                    limit=limit,
                    offset=offset,
                    additional_types=("track",)
                )
            except Exception:
                break

            items = batch.get("items", [])
            if not items:
                break

            for item in items:
                track = item.get("track")
                if not track or not track.get("id"):
                    continue
                artists = ", ".join([a["name"] for a in track["artists"]])
                tracks.append({
                    "id": track["id"],
                    "title": track["name"],
                    "artist": artists,
                    "uri": track["uri"],
                    "duration_ms": track.get("duration_ms", 0),
                    "source": playlist_name
                })

            offset += len(items)
            if len(items) < limit:
                break

        return tracks

    def collect_entire_library(self) -> list[dict]:
        """
        Scans all Liked Songs and all user playlists (created & saved),
        pooling and deduplicating all tracks into one unique collection.
        """
        print("\n📚 Scanning your complete Spotify library (Liked Songs + All Playlists)...")
        unique_tracks = {}  # uri -> track_dict

        # 1. Fetch Liked Songs
        liked = self.get_all_liked_songs()
        for t in liked:
            uri = t["uri"]
            if uri not in unique_tracks:
                unique_tracks[uri] = {**t, "sources": ["Liked Songs"]}
            else:
                unique_tracks[uri]["sources"].append("Liked Songs")

        # 2. Fetch All Playlists
        playlists = self.get_all_user_playlists()
        print(f"  📂 Found {len(playlists)} playlists to scan...")
        for pl in playlists:
            print(f"  Scanning playlist: '{pl['name']}' ({pl['total_tracks']} tracks)...")
            pl_tracks = self.get_playlist_tracks(pl["id"], pl["name"])
            for t in pl_tracks:
                uri = t["uri"]
                if uri not in unique_tracks:
                    unique_tracks[uri] = {**t, "sources": [pl["name"]]}
                else:
                    if pl["name"] not in unique_tracks[uri]["sources"]:
                        unique_tracks[uri]["sources"].append(pl["name"])

        total_unique = len(unique_tracks)
        print(f"\n✅ Finished scanning! Found {total_unique} unique songs across your entire library.")
        return list(unique_tracks.values())

    def rank_library_by_api_affinity(self, library_tracks: list[dict], limit: int = 50) -> list[dict]:
        """
        Ranks all collected library songs by Spotify's listening affinity algorithm
        (combining Lifetime, 6 Months, and 4 Weeks top listening data).
        """
        print("\n🔍 Querying your Spotify listening affinity for library tracks...")
        affinity_scores = {}  # uri -> float score

        # 1. Lifetime top tracks (weight = 3x)
        try:
            long_top = self.sp.current_user_top_tracks(limit=50, time_range="long_term").get("items", [])
            for rank, item in enumerate(long_top, 1):
                affinity_scores[item["uri"]] = affinity_scores.get(item["uri"], 0) + (51 - rank) * 3.0
        except Exception as e:
            print(f"  ⚠️ Warning querying long_term top tracks: {e}")

        # 2. Medium-term top tracks (weight = 2x)
        try:
            med_top = self.sp.current_user_top_tracks(limit=50, time_range="medium_term").get("items", [])
            for rank, item in enumerate(med_top, 1):
                affinity_scores[item["uri"]] = affinity_scores.get(item["uri"], 0) + (51 - rank) * 2.0
        except Exception:
            pass

        # 3. Short-term top tracks (weight = 1x)
        try:
            short_top = self.sp.current_user_top_tracks(limit=50, time_range="short_term").get("items", [])
            for rank, item in enumerate(short_top, 1):
                affinity_scores[item["uri"]] = affinity_scores.get(item["uri"], 0) + (51 - rank) * 1.0
        except Exception:
            pass

        scored_tracks = []
        for track in library_tracks:
            uri = track["uri"]
            score = affinity_scores.get(uri, 0.0)
            # Bonus points for appearing in multiple playlists/liked songs
            num_sources = len(track.get("sources", []))
            score += num_sources * 2.0

            sources_summary = ", ".join(track.get("sources", [])[:3])
            if len(track.get("sources", [])) > 3:
                sources_summary += f" +{len(track['sources']) - 3} more"

            scored_tracks.append({
                **track,
                "score": score,
                "in_top_tracks": uri in affinity_scores,
                "sources_summary": sources_summary
            })

        # Sort tracks by affinity score descending
        scored_tracks.sort(key=lambda t: t["score"], reverse=True)

        results = []
        for rank, t in enumerate(scored_tracks[:limit], start=1):
            status = "🔥 Top Listened Track" if t["in_top_tracks"] else f"Saved in {len(t.get('sources', []))} lists"
            results.append({
                "rank": rank,
                "title": t["title"],
                "artist": t["artist"],
                "uri": t["uri"],
                "streams": f"{status} (Sources: {t['sources_summary']})"
            })

        return results

    # ---------------------------------------------------------
    # Core Utility Methods
    # ---------------------------------------------------------

    def get_personal_top_tracks(self, limit: int = 50, time_range: str = "long_term") -> list[dict]:
        """Fetches top tracks from Spotify API."""
        results = self.sp.current_user_top_tracks(limit=limit, time_range=time_range)
        tracks = []
        for idx, item in enumerate(results.get("items", []), start=1):
            artists = ", ".join([a["name"] for a in item["artists"]])
            duration_ms = item.get("duration_ms", 0)
            duration_min = round(duration_ms / 60000.0, 1)

            tracks.append({
                "rank": idx,
                "title": item["name"],
                "artist": artists,
                "uri": item["uri"],
                "streams": f"Track length: {duration_min} min (Rank #{idx} most listened)"
            })
        return tracks

    def search_track_uri(self, artist: str, title: str) -> Optional[str]:
        """Searches Spotify for a track given artist and title."""
        clean_title = re.sub(r"\(.*?\)|\[.*?\]", "", title).strip()
        main_artist = artist.split(",")[0].split("&")[0].split("feat.")[0].strip()

        queries = [
            f"track:{clean_title} artist:{main_artist}",
            f"{main_artist} {clean_title}",
            f"{artist} {title}"
        ]

        for query in queries:
            try:
                results = self.sp.search(q=query, type="track", limit=1)
                items = results.get("tracks", {}).get("items", [])
                if items:
                    return items[0]["uri"]
            except Exception:
                continue

        return None

    def create_playlist(
        self,
        name: str,
        description: str,
        track_uris: list[str],
        public: bool = True
    ) -> dict:
        """Creates a new playlist on the user's account and adds tracks in batches."""
        if not track_uris:
            raise ValueError("No tracks provided to add to the playlist.")

        playlist = self.sp.user_playlist_create(
            user=self.user_id,
            name=name,
            public=public,
            description=description
        )
        playlist_id = playlist["id"]
        playlist_url = playlist["external_urls"]["spotify"]

        batch_size = 100
        for i in range(0, len(track_uris), batch_size):
            chunk = track_uris[i:i + batch_size]
            self.sp.playlist_add_items(playlist_id=playlist_id, items=chunk)

        return {
            "id": playlist_id,
            "url": playlist_url,
            "name": name,
            "count": len(track_uris)
        }
