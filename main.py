"""
main.py
Main entry point for scraping Spotify top tracks and generating playlists.
Includes full library scanning (Liked Songs + all user playlists) to create
a playlist of your most listened tracks.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

from scraper import scrape_daily_global_top, scrape_all_time_top
from spotify_client import SpotifyManager
from history_parser import parse_streaming_history, rank_library_tracks_with_history


def check_env_setup() -> bool:
    """Verifies that .env exists and has required Spotify API credentials."""
    load_dotenv()
    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")

    if not client_id or not client_secret or "your_" in client_id:
        print("\n" + "=" * 60)
        print("⚠️  SPOTIFY API CREDENTIALS REQUIRED")
        print("=" * 60)
        print("To create playlists, configure '.env' with your credentials:\n")
        print("1. Go to: https://developer.spotify.com/dashboard")
        print("2. Open your App settings and ensure Redirect URI is:")
        print("   http://127.0.0.1:8080/callback")
        print("3. Check 'User Management' and add your Spotify email.")
        print("4. Add your credentials into '.env':")
        print("   SPOTIPY_CLIENT_ID=your_client_id")
        print("   SPOTIPY_CLIENT_SECRET=your_client_secret")
        print("   SPOTIPY_REDIRECT_URI=http://127.0.0.1:8080/callback\n")
        print("=" * 60 + "\n")
        return False
    return True


def display_tracks(tracks: list[dict]):
    """Pretty prints track list in terminal."""
    print("\n" + "-" * 80)
    print(f"{'#':<4} {'Artist':<22} {'Title':<25} {'Stats / Source'}")
    print("-" * 80)
    for t in tracks:
        artist = (t['artist'][:20] + "..") if len(t['artist']) > 22 else t['artist']
        title = (t['title'][:22] + "..") if len(t['title']) > 24 else t['title']
        stats = t.get('streams', '')
        print(f"{t['rank']:<4} {artist:<22} {title:<25} {stats}")
    print("-" * 80 + "\n")


def run():
    print("""
======================================================
  🎵 SPOTIFY SCRAPER & PLAYLIST GENERATOR 🎵
======================================================
Choose what you would like to do:
  [1] Scrape & Create Playlist: Daily Global Most Listened Songs
  [2] Scrape & Create Playlist: All-Time Most Streamed Songs on Spotify
  [3] Fetch & Create Playlist: YOUR Personal Top Tracks (Spotify API)
  [4] 🌟 LIBRARY DEEP DIVE: Scan Liked Songs + All Playlists & Make Playlist of Most Listened Songs!
  [5] Parse & Create Playlist: EXACT Minutes Listened from Spotify Data Export (.json files)
  [6] Only Scrape & Preview Data (No Playlist creation)
  [0] Exit
""")

    choice = input("Enter choice (0-6): ").strip()
    if choice == "0":
        print("Goodbye!")
        sys.exit(0)

    if choice not in ["1", "2", "3", "4", "5", "6"]:
        print("Invalid choice. Exiting.")
        sys.exit(1)

    limit_input = input("How many songs do you want in the final playlist? (Default: 30, Max: 100): ").strip()
    try:
        limit = int(limit_input) if limit_input else 30
        limit = max(1, min(limit, 100))
    except ValueError:
        limit = 30

    tracks = []
    playlist_default_name = ""
    playlist_desc = ""

    # 1. Daily Global
    if choice == "1":
        print(f"\n🌐 Scraping Top {limit} Daily Global Most Listened Songs...")
        try:
            tracks = scrape_daily_global_top(limit=limit)
            playlist_default_name = f"Daily Global Top Hits ({datetime.now().strftime('%Y-%m-%d')})"
            playlist_desc = f"Top {limit} daily global most streamed songs on Spotify. Auto-generated on {datetime.now().strftime('%Y-%m-%d')}."
        except Exception as e:
            print(f"❌ Error scraping daily songs: {e}")
            sys.exit(1)

    # 2. All-Time Global
    elif choice == "2":
        print(f"\n🌐 Scraping Top {limit} All-Time Most Streamed Songs...")
        try:
            tracks = scrape_all_time_top(limit=limit)
            playlist_default_name = f"All-Time Most Streamed Spotify Songs"
            playlist_desc = f"Top {limit} most streamed songs of all time on Spotify (billions of streams). Auto-generated."
        except Exception as e:
            print(f"❌ Error scraping all-time songs: {e}")
            sys.exit(1)

    # 3. Personal Top Tracks (Spotify API)
    elif choice == "3":
        if not check_env_setup():
            sys.exit(1)
        print("\nChoose listening timeframe for your top tracks:")
        print("  [1] Lifetime / All-time (Calculated across several years of listening)")
        print("  [2] Past 6 months (Medium-term)")
        print("  [3] Past 4 weeks (Short-term)")
        tf_choice = input("Select timeframe (1-3, default 1): ").strip()
        time_ranges = {"1": "long_term", "2": "medium_term", "3": "short_term"}
        selected_tr = time_ranges.get(tf_choice, "long_term")
        label = {"long_term": "All-Time Lifetime", "medium_term": "Past 6 Months", "short_term": "Past 4 Weeks"}[selected_tr]

        try:
            spotify = SpotifyManager()
            print(f"\n🎧 Fetching your Top {limit} tracks ({label}) ranked by listening duration/affinity...")
            tracks = spotify.get_personal_top_tracks(limit=limit, time_range=selected_tr)
            playlist_default_name = f"My Most Listened Songs - {label}"
            playlist_desc = f"My top {limit} most listened tracks ({label}) on Spotify."
        except Exception as e:
            print(f"❌ Error fetching personal top tracks: {e}")
            sys.exit(1)

    # 4. LIBRARY DEEP DIVE (Liked Songs + All Playlists)
    elif choice == "4":
        if not check_env_setup():
            sys.exit(1)

        try:
            spotify = SpotifyManager()
            # 1. Collect all songs from Liked Songs and all playlists
            library_tracks = spotify.collect_entire_library()
            if not library_tracks:
                print("❌ No songs found in your library or playlists.")
                sys.exit(1)

            print("\nHow would you like to rank the songs from your library?")
            print("  [1] By Spotify Listening Affinity (Lifetime, 6 Mo, 4 Wks Top Data - Instant)")
            print("  [2] By Exact Minutes Listened (from downloaded Spotify Streaming History JSON files)")
            rank_choice = input("Select ranking method (1 or 2, default 1): ").strip()

            if rank_choice == "2":
                path_input = input("Enter path to your JSON file or folder containing StreamingHistory*.json: ").strip()
                if not path_input:
                    path_input = "./data"
                tracks = rank_library_tracks_with_history(library_tracks, path_input, limit=limit)
                playlist_default_name = "My Most Listened Library Favorites (Exact Minutes)"
                playlist_desc = f"Top {limit} most listened tracks across all Liked Songs and Playlists by exact minutes."
            else:
                tracks = spotify.rank_library_by_api_affinity(library_tracks, limit=limit)
                playlist_default_name = "My Most Listened Library Favorites"
                playlist_desc = f"Top {limit} most listened tracks across all my Liked Songs and Playlists."

        except Exception as e:
            print(f"❌ Error during Library Deep Dive: {e}")
            sys.exit(1)

    # 5. Exact Minutes from Spotify JSON History
    elif choice == "5":
        print("\n📂 SPOTIFY STREAMING HISTORY DATA PARSER")
        print("Spotify allows downloading your full listening history (.json files) with exact milliseconds played.")
        print("To download: Spotify.com -> Account -> Privacy Settings -> 'Download your data'.\n")
        path_input = input("Enter path to your JSON file or folder containing StreamingHistory*.json: ").strip()
        if not path_input:
            path_input = "./data"

        try:
            tracks = parse_streaming_history(path_input, limit=limit)
            playlist_default_name = "My Most Listened Songs (By Exact Minutes)"
            playlist_desc = f"Top {limit} songs sorted by total listening minutes from Spotify Streaming History."
        except Exception as e:
            print(f"❌ Could not parse streaming history: {e}")
            sys.exit(1)

    # 6. Scrape Preview Only
    elif choice == "6":
        print("Scrape which dataset?")
        print("  [1] Daily Global Top Songs")
        print("  [2] All-Time Most Streamed Songs")
        sub_choice = input("Select (1 or 2): ").strip()
        if sub_choice == "2":
            tracks = scrape_all_time_top(limit=limit)
        else:
            tracks = scrape_daily_global_top(limit=limit)
        display_tracks(tracks)
        print(f"✅ Successfully scraped {len(tracks)} tracks.")
        return

    # Display Scraped / Retrieved Songs
    display_tracks(tracks)

    # Check credentials before creating playlist
    if not check_env_setup():
        print("Cannot create playlist without Spotify credentials. Please set up .env and run again.")
        sys.exit(1)

    # Playlist creation prompt
    custom_name = input(f"Playlist Name (Press Enter for '{playlist_default_name}'): ").strip()
    playlist_name = custom_name if custom_name else playlist_default_name

    is_public_in = input("Make playlist public? (Y/n): ").strip().lower()
    is_public = False if is_public_in == "n" else True

    print("\nConnecting to Spotify...")
    try:
        spotify = SpotifyManager()
    except Exception as e:
        print(f"❌ Spotify Authentication Error: {e}")
        sys.exit(1)

    track_uris = []
    print("\n🔍 Matching and preparing tracks on Spotify...")
    for item in tracks:
        if item.get("uri"):
            track_uris.append(item["uri"])
            continue

        uri = spotify.search_track_uri(artist=item["artist"], title=item["title"])
        if uri:
            track_uris.append(uri)
            print(f"  ✓ Found: {item['artist']} - {item['title']}")
        else:
            print(f"  ✗ Not found: {item['artist']} - {item['title']}")

    if not track_uris:
        print("❌ Could not match any tracks on Spotify.")
        sys.exit(1)

    print(f"\n📦 Creating playlist '{playlist_name}' with {len(track_uris)} songs...")
    try:
        result = spotify.create_playlist(
            name=playlist_name,
            description=playlist_desc,
            track_uris=track_uris,
            public=is_public
        )
        print("\n" + "=" * 60)
        print("🎉 PLAYLIST CREATED SUCCESSFULLY!")
        print("=" * 60)
        print(f"📌 Playlist Name: {result['name']}")
        print(f"🎶 Total Songs:   {result['count']}")
        print(f"🔗 Direct URL:    {result['url']}")
        print("=" * 60 + "\n")
    except Exception as e:
        print(f"❌ Failed to create playlist: {e}")


if __name__ == "__main__":
    run()
