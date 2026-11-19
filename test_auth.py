"""
test_auth.py
Quick diagnostic script to isolate the exact cause of Spotify auth failure.
Tests different redirect URIs and scopes to pinpoint the issue.
"""

import os
import secrets
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyPKCE

load_dotenv()

client_id = os.getenv("SPOTIPY_CLIENT_ID")
client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8080/callback")

print("\n" + "=" * 65)
print("🔍 SPOTIFY AUTHENTICATION DIAGNOSTIC TOOL")
print("=" * 65)
print(f"Current Client ID:    {client_id}")
print(f"Current Redirect URI: {redirect_uri}")
print("=" * 65)

print("\nSelect diagnostic test:")
print("  [1] Test Base Permission (scope: 'user-read-private' - simplest possible)")
print("  [2] Test with PKCE (Proof Key for Code Exchange - alternative OAuth)")
print("  [3] Test with port 8888 (http://127.0.0.1:8888/callback)")
print("  [4] Test with port 8080 (http://127.0.0.1:8080/callback)")
print("  [0] Exit")

test_choice = input("Enter choice (1-4): ").strip()

test_scope = "user-read-private"
test_redirect = redirect_uri
use_pkce = False

if test_choice == "1":
    test_scope = "user-read-private"
    print("\n👉 Testing basic profile scope ('user-read-private')...")
elif test_choice == "2":
    use_pkce = True
    test_scope = "user-read-private playlist-modify-public"
    print("\n👉 Testing PKCE OAuth flow...")
elif test_choice == "3":
    test_redirect = "http://127.0.0.1:8888/callback"
    test_scope = "user-read-private"
    print(f"\n👉 Testing with Redirect URI: {test_redirect}...")
elif test_choice == "4":
    test_redirect = "http://127.0.0.1:8080/callback"
    test_scope = "user-read-private"
    print(f"\n👉 Testing with Redirect URI: {test_redirect}...")
else:
    print("Exiting.")
    exit(0)

random_state = secrets.token_urlsafe(16)

if use_pkce:
    auth = SpotifyPKCE(
        client_id=client_id,
        redirect_uri=test_redirect,
        scope=test_scope,
        state=random_state,
        open_browser=False
    )
else:
    auth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=test_redirect,
        scope=test_scope,
        state=random_state,
        show_dialog=True,
        open_browser=False
    )

auth_url = auth.get_authorize_url()

print("\n" + "-" * 65)
print("Step 1: Open this URL in your browser (preferably Incognito/Private):")
print(f"\n{auth_url}\n")
print("Step 2: Log in and click 'Agree'.")
print("Step 3: Paste the full URL from your browser address bar below.")
print("-" * 65)

resp = input("\nEnter redirected URL: ").strip()

if "error=" in resp:
    print("\n❌ FAILED. Response contains error:")
    print(resp)
else:
    try:
        code = auth.parse_response_code(resp)
        token = auth.get_access_token(code)
        access_token = token if isinstance(token, str) else token.get("access_token")
        sp = spotipy.Spotify(auth=access_token)
        user = sp.me()
        print("\n" + "=" * 65)
        print("🎉 SUCCESS! Authentication worked!")
        print(f"Logged in as: {user.get('display_name')} (ID: {user.get('id')})")
        print(f"Country:      {user.get('country')}")
        print(f"Product/Plan: {user.get('product')}")
        print("=" * 65)
    except Exception as e:
        print(f"\n❌ Token exchange failed: {e}")

