"""
scraper.py
Scrapes Spotify stream rankings and charts data using requests and BeautifulSoup.
"""

import requests
from bs4 import BeautifulSoup
import re


def _clean_text(text: str) -> str:
    """Removes excess whitespace and non-standard characters."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def scrape_daily_global_top(limit: int = 50) -> list[dict]:
    """
    Scrapes the daily global most-streamed tracks from Spotify charts (via Kworb).
    
    Returns a list of dictionaries:
    [
        {
            "rank": int,
            "artist": str,
            "title": str,
            "streams": str
        }, ...
    ]
    """
    url = "https://kworb.net/spotify/country/global_daily.html"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(url, headers=headers, timeout=15)
    response.encoding = "utf-8"
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", {"class": "sortable"})
    if not table:
        raise ValueError("Could not find the ranking table on Kworb Daily Global page.")

    tracks = []
    rows = table.find_all("tr")[1:]  # skip header row

    for row in rows:
        if len(tracks) >= limit:
            break

        tds = row.find_all("td")
        if len(tds) < 3:
            continue

        rank_str = _clean_text(tds[0].text)
        raw_text = _clean_text(tds[2].text)
        streams = _clean_text(tds[6].text) if len(tds) > 6 else "N/A"

        try:
            rank = int(rank_str)
        except ValueError:
            rank = len(tracks) + 1

        if " - " in raw_text:
            artist, title = raw_text.split(" - ", 1)
        else:
            artist, title = raw_text, ""

        tracks.append({
            "rank": rank,
            "artist": _clean_text(artist),
            "title": _clean_text(title),
            "streams": streams
        })

    return tracks


def scrape_all_time_top(limit: int = 50) -> list[dict]:
    """
    Scrapes the all-time most streamed songs on Spotify (via Kworb).
    
    Returns a list of dictionaries with song details and stream counts.
    """
    url = "https://kworb.net/spotify/songs.html"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(url, headers=headers, timeout=15)
    response.encoding = "utf-8"
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", {"class": "sortable"})
    if not table:
        raise ValueError("Could not find ranking table on Kworb Spotify Songs page.")

    tracks = []
    rows = table.find_all("tr")[1:]  # skip header row

    for idx, row in enumerate(rows, start=1):
        if len(tracks) >= limit:
            break

        tds = row.find_all("td")
        if len(tds) < 2:
            continue

        raw_text = _clean_text(tds[0].text)
        streams = _clean_text(tds[1].text)

        if " - " in raw_text:
            artist, title = raw_text.split(" - ", 1)
        else:
            artist, title = raw_text, ""

        tracks.append({
            "rank": idx,
            "artist": _clean_text(artist),
            "title": _clean_text(title),
            "streams": streams
        })

    return tracks


if __name__ == "__main__":
    print("Testing Daily Global Scraper...")
    daily = scrape_daily_global_top(5)
    for t in daily:
        print(f"#{t['rank']} {t['artist']} - {t['title']} ({t['streams']} streams)")

    print("\nTesting All-Time Top Scraper...")
    all_time = scrape_all_time_top(5)
    for t in all_time:
        print(f"#{t['rank']} {t['artist']} - {t['title']} ({t['streams']} streams)")

