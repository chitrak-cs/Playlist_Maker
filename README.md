# 🎵 Spotify Scraper & Playlist Creator

A complete Python tool that scrapes the most listened songs from Spotify stream charts, matches them in the Spotify music catalog, and automatically creates a new playlist on your Spotify account.

---

## 🌟 Features

1. **🌟 Library Deep Dive**: Scans your entire Spotify account—all Liked Songs, playlists you've created, and playlists you've saved/followed—deduplicates them into a master pool, finds the ones you've listened to the most, and generates a new playlist with them!
2. **Daily Global Top Songs**: Scrapes daily most streamed songs worldwide directly from Spotify stream charts (Kworb).
3. **All-Time Most Streamed Songs**: Scrapes Spotify's most listened songs of all time (billions of streams, e.g., *Blinding Lights*, *Shape of You*).
4. **Personal Top Tracks (API)**: Fetches top tracks (lifetime, 6 months, or 4 weeks) ranked by Spotify's affinity algorithm.
5. **Exact Minutes from Data Export**: Parses your Spotify Streaming History JSON files to calculate the exact total minutes listened for every song.
6. **Automatic Playlist Creation**: Directly creates public or private playlists in your Spotify account.

---

## 📁 Project Structure

```
Spotify Project/
├── venv/                 # Python virtual environment (already set up)
├── .env.example          # Environment variables template
├── .env                  # Your private Spotify API credentials (create from .env.example)
├── requirements.txt      # Python dependencies (spotipy, beautifulsoup4, requests, python-dotenv)
├── scraper.py            # Web scraping engine for Spotify chart data
├── spotify_client.py     # Spotify API manager (auth, track searching, playlist creation)
├── main.py               # Interactive CLI to run the entire flow
└── README.md             # Documentation & Setup guide
```

---

## 🚀 Quick Setup & Usage

### 1. Set Up Your Spotify Developer Credentials

To allow Python to create a playlist on your Spotify account, Spotify requires standard OAuth authentication:

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and log in with your Spotify account.
2. Click **Create App**:
   - **App name**: `Music Scraper` (or any name *not* starting with "Spot")
   - **App description**: `Scraper and playlist generator`
   - **Redirect URIs**: `http://127.0.0.1:8080/callback` *(then click the purple **Add** button!)*
   - **Which API/SDKs are you planning to use?**: Check **Web API**.
3. Accept the Terms and click **Save**.
4. Click on **Settings** in your app dashboard to view your:
   - **Client ID**
   - **Client Secret** (click *View client secret*)

### 2. Configure Your `.env` File

Open [.env](file:///home/chitrak-betal/Desktop/Spotify%20Project/.env) and paste your credentials:
```env
SPOTIPY_CLIENT_ID=your_actual_client_id_here
SPOTIPY_CLIENT_SECRET=your_actual_client_secret_here
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8080/callback
```

---

### 3. Run the Program

Activate the virtual environment and run `main.py`:

```bash
# In the project directory:
source venv/bin/activate
python main.py
```

### 4. First-time Authentication

When you create a playlist for the first time, your browser will open asking you to authorize the app to access your Spotify account:
- Click **Agree**.
- The browser will redirect to `http://localhost:8888/callback?...`.
- Spotipy automatically detects the token and saves it in a `.cache` file so you don't have to log in again.
- Your playlist will be generated immediately and the link will be displayed on your terminal!

---

## 🛠️ Testing Scrapers Without API Credentials

If you just want to test the scraper and view the current most-listened songs without creating a playlist:
```bash
source venv/bin/activate
python scraper.py
```
or choose Option `[4]` in `python main.py`.

