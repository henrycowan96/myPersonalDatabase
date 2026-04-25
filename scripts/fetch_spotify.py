import os
import sys
from pathlib import Path
from datetime import datetime
import json
import time
import requests
from urllib.parse import urlencode
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from metadata_utils import generate_metadata, save_with_metadata

"""
Spotify Integration Notes:
================================
This script uses the Spotify Web API to fetch user's library, playlists, top tracks, and listening history.

Requirements:
- Spotify Developer Account (https://developer.spotify.com/dashboard)
- Client ID and Client Secret from Spotify Developer portal
- User authorization via OAuth2
- requests library (pip install requests)

Spotify Web API requires OAuth2 authorization. The script uses authorization code flow
to get access tokens and refresh tokens for API access.
"""

load_dotenv()

# Configuration
RAW_DOCS_DIR = Path(__file__).parent.parent / "data" / "raw_docs"
SPOTIFY_DIR = RAW_DOCS_DIR / "spotify"
CREDENTIALS_DIR = Path(__file__).parent.parent / "credentials"

# Create directories if they don't exist
RAW_DOCS_DIR.mkdir(parents=True, exist_ok=True)
SPOTIFY_DIR.mkdir(parents=True, exist_ok=True)
CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

# Spotify API endpoints
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"

# OAuth scopes
SPOTIFY_SCOPES = [
    "user-read-private",
    "user-read-email",
    "user-library-read",
    "user-top-read",
    "user-read-playback-state",
    "user-read-recently-played",
    "playlist-read-private",
    "playlist-read-collaborative"
]

class SpotifyClient:
    """Spotify API client with OAuth2 token management"""
    
    def __init__(self, client_id, client_secret, redirect_uri, access_token=None, refresh_token=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = access_token
        self.refresh_token = refresh_token
    
    def get_auth_url(self):
        """Generate Spotify authorization URL"""
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(SPOTIFY_SCOPES)
        }
        return f"{SPOTIFY_AUTH_URL}?{urlencode(params)}"
    
    def exchange_code_for_token(self, code):
        """Exchange authorization code for access token"""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        response = requests.post(SPOTIFY_TOKEN_URL, data=data)
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.refresh_token = token_data.get("refresh_token")
            return token_data
        else:
            raise Exception(f"Failed to exchange code for token: {response.text}")
    
    def refresh_access_token(self):
        """Refresh access token using refresh token"""
        if not self.refresh_token:
            raise Exception("No refresh token available")
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        response = requests.post(SPOTIFY_TOKEN_URL, data=data)
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data["access_token"]
            if "refresh_token" in token_data:
                self.refresh_token = token_data["refresh_token"]
            return token_data
        else:
            raise Exception(f"Failed to refresh token: {response.text}")
    
    def make_request(self, endpoint, params=None):
        """Make authenticated request to Spotify API"""
        if not self.access_token:
            raise Exception("No access token available")
        
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        response = requests.get(f"{SPOTIFY_API_BASE}{endpoint}", headers=headers, params=params)
        
        if response.status_code == 401:
            # Token expired, try to refresh
            self.refresh_access_token()
            headers["Authorization"] = f"Bearer {self.access_token}"
            response = requests.get(f"{SPOTIFY_API_BASE}{endpoint}", headers=headers, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API request failed: {response.status_code} - {response.text}")
    
    def get_user_profile(self):
        """Get current user's profile"""
        return self.make_request("/me")
    
    def get_top_tracks(self, limit=50, time_range="medium_term"):
        """Get user's top tracks"""
        params = {
            "limit": limit,
            "time_range": time_range  # short_term, medium_term, long_term
        }
        return self.make_request("/me/top/tracks", params)
    
    def get_top_artists(self, limit=50, time_range="medium_term"):
        """Get user's top artists"""
        params = {
            "limit": limit,
            "time_range": time_range
        }
        return self.make_request("/me/top/artists", params)
    
    def get_saved_tracks(self, limit=50, offset=0):
        """Get user's saved tracks"""
        params = {
            "limit": limit,
            "offset": offset
        }
        return self.make_request("/me/tracks", params)
    
    def get_playlists(self, limit=50, offset=0):
        """Get user's playlists"""
        params = {
            "limit": limit,
            "offset": offset
        }
        return self.make_request("/me/playlists", params)
    
    def get_recently_played(self, limit=50):
        """Get recently played tracks"""
        params = {
            "limit": limit
        }
        return self.make_request("/player/recently-played", params)
    
    def get_playlist_tracks(self, playlist_id, limit=100, offset=0):
        """Get tracks from a specific playlist"""
        params = {
            "limit": limit,
            "offset": offset
        }
        return self.make_request(f"/playlists/{playlist_id}/tracks", params)

def format_track(track):
    """Format a track as text"""
    if not track:
        return ""
    
    track_data = track.get("track", track)
    name = track_data.get("name", "Unknown")
    
    # Get artists
    artists = track_data.get("artists", [])
    artist_names = ", ".join([a.get("name", "Unknown") for a in artists])
    
    # Get album
    album = track_data.get("album", {})
    album_name = album.get("name", "Unknown")
    
    # Get duration
    duration_ms = track_data.get("duration_ms", 0)
    duration_sec = duration_ms / 1000
    
    # Get popularity
    popularity = track_data.get("popularity", 0)
    
    track_text = f"Track: {name}\n"
    track_text += f"Artist: {artist_names}\n"
    track_text += f"Album: {album_name}\n"
    track_text += f"Duration: {duration_sec:.1f} seconds\n"
    track_text += f"Popularity: {popularity}/100\n"
    
    # Get external IDs
    external_ids = track_data.get("external_ids", {})
    if external_ids.get("isrc"):
        track_text += f"ISRC: {external_ids['isrc']}\n"
    
    return track_text

def format_artist(artist):
    """Format an artist as text"""
    if not artist:
        return ""
    
    name = artist.get("name", "Unknown")
    genres = artist.get("genres", [])
    popularity = artist.get("popularity", 0)
    followers = artist.get("followers", {}).get("total", 0)
    
    artist_text = f"Artist: {name}\n"
    artist_text += f"Followers: {followers:,}\n"
    artist_text += f"Popularity: {popularity}/100\n"
    
    if genres:
        artist_text += f"Genres: {', '.join(genres)}\n"
    
    return artist_text

def format_playlist(playlist):
    """Format a playlist as text"""
    if not playlist:
        return ""
    
    name = playlist.get("name", "Unknown")
    owner = playlist.get("owner", {}).get("display_name", "Unknown")
    description = playlist.get("description", "")
    tracks_total = playlist.get("tracks", {}).get("total", 0)
    public = playlist.get("public", False)
    collaborative = playlist.get("collaborative", False)
    
    playlist_text = f"Playlist: {name}\n"
    playlist_text += f"Owner: {owner}\n"
    playlist_text += f"Total Tracks: {tracks_total}\n"
    playlist_text += f"Public: {public}\n"
    playlist_text += f"Collaborative: {collaborative}\n"
    
    if description:
        playlist_text += f"Description: {description}\n"
    
    return playlist_text

def save_spotify_data(data, data_type, user_id=None):
    """Save Spotify data to a text file with metadata"""
    if not data:
        return None
    
    filename = f"{data_type}_data.txt"
    if user_id:
        filename = f"{user_id}_{filename}"
    output_path = SPOTIFY_DIR / filename
    
    # Generate metadata
    metadata = generate_metadata(
        source="spotify",
        type=data_type,
        author=user_id,
        created_date=datetime.now().isoformat(),
        modified_date=None,
        data_type=data_type
    )
    
    # Format the content
    content = f"Spotify {data_type.title()}\n"
    content += f"Extracted: {datetime.now().isoformat()}\n"
    if user_id:
        content += f"User ID: {user_id}\n"
    content += "=" * 50 + "\n\n"
    
    if data_type == 'top_tracks':
        tracks = data.get("items", [])
        for track in tracks:
            track_text = format_track(track)
            content += track_text
            content += "\n" + "-" * 50 + "\n\n"
        metadata['track_count'] = len(tracks)
    
    elif data_type == 'top_artists':
        artists = data.get("items", [])
        for artist in artists:
            artist_text = format_artist(artist)
            content += artist_text
            content += "\n" + "-" * 50 + "\n\n"
        metadata['artist_count'] = len(artists)
    
    elif data_type == 'saved_tracks':
        items = data.get("items", [])
        for item in items:
            track_text = format_track(item)
            content += track_text
            content += "\n" + "-" * 50 + "\n\n"
        metadata['track_count'] = len(items)
    
    elif data_type == 'playlists':
        playlists = data.get("items", [])
        for playlist in playlists:
            playlist_text = format_playlist(playlist)
            content += playlist_text
            content += "\n" + "-" * 50 + "\n\n"
        metadata['playlist_count'] = len(playlists)
    
    elif data_type == 'recently_played':
        items = data.get("items", [])
        for item in items:
            track = item.get("track", {})
            played_at = item.get("played_at", "")
            track_text = format_track({"track": track})
            track_text += f"Played At: {played_at}\n"
            content += track_text
            content += "\n" + "-" * 50 + "\n\n"
        metadata['track_count'] = len(items)
    
    # Save with metadata header
    save_with_metadata(output_path, content, metadata)
    
    return output_path

def fetch_all_spotify_data(client, user_id=None):
    """Fetch all relevant Spotify data for a user"""
    print("Fetching Spotify data...")
    
    saved_files = []
    
    try:
        # Get user profile
        print("Fetching user profile...")
        profile = client.get_user_profile()
        if not user_id:
            user_id = profile.get("id", "unknown")
        print(f"User: {profile.get('display_name', 'Unknown')}")
        
        # Get top tracks
        print("Fetching top tracks...")
        top_tracks = client.get_top_tracks(limit=50, time_range="medium_term")
        if top_tracks.get("items"):
            output_path = save_spotify_data(top_tracks, 'top_tracks', user_id)
            if output_path:
                saved_files.append(output_path)
                print(f"Saved top tracks -> {output_path.name}")
        
        # Get top artists
        print("Fetching top artists...")
        top_artists = client.get_top_artists(limit=50, time_range="medium_term")
        if top_artists.get("items"):
            output_path = save_spotify_data(top_artists, 'top_artists', user_id)
            if output_path:
                saved_files.append(output_path)
                print(f"Saved top artists -> {output_path.name}")
        
        # Get saved tracks
        print("Fetching saved tracks...")
        saved_tracks = client.get_saved_tracks(limit=50)
        if saved_tracks.get("items"):
            output_path = save_spotify_data(saved_tracks, 'saved_tracks', user_id)
            if output_path:
                saved_files.append(output_path)
                print(f"Saved tracks -> {output_path.name}")
        
        # Get playlists
        print("Fetching playlists...")
        playlists = client.get_playlists(limit=50)
        if playlists.get("items"):
            output_path = save_spotify_data(playlists, 'playlists', user_id)
            if output_path:
                saved_files.append(output_path)
                print(f"Saved playlists -> {output_path.name}")
        
        # Get recently played
        print("Fetching recently played...")
        recently_played = client.get_recently_played(limit=50)
        if recently_played.get("items"):
            output_path = save_spotify_data(recently_played, 'recently_played', user_id)
            if output_path:
                saved_files.append(output_path)
                print(f"Saved recently played -> {output_path.name}")
        
        print(f"\nComplete! Saved {len(saved_files)} data files to {SPOTIFY_DIR}")
        return saved_files
        
    except Exception as e:
        print(f"Error fetching Spotify data: {e}")
        return saved_files

def main():
    """Main function for standalone script execution"""
    print("Spotify Data Fetcher")
    print("=" * 50)
    
    # Get credentials from environment or prompt
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8000/spotify/callback")
    
    if not client_id:
        client_id = input("Enter Spotify Client ID: ").strip()
    if not client_secret:
        client_secret = input("Enter Spotify Client Secret: ").strip()
    
    # Initialize client
    client = SpotifyClient(client_id, client_secret, redirect_uri)
    
    # Generate auth URL
    auth_url = client.get_auth_url()
    print(f"\n1. Visit this URL to authorize:\n{auth_url}\n")
    
    # Get authorization code from callback
    auth_code = input("2. Paste the authorization code from the callback URL: ").strip()
    
    # Exchange code for token
    print("3. Exchanging authorization code for access token...")
    try:
        token_data = client.exchange_code_for_token(auth_code)
        print("Successfully obtained access token!")
        
        # Save tokens for future use
        token_file = CREDENTIALS_DIR / "spotify_tokens.json"
        with open(token_file, 'w') as f:
            json.dump({
                "access_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "expires_at": time.time() + token_data.get("expires_in", 3600)
            }, f)
        print(f"Tokens saved to {token_file}")
        
        # Fetch data
        print("\n4. Fetching Spotify data...")
        saved_files = fetch_all_spotify_data(client)
        
        if saved_files:
            print(f"\nSuccess! You can now run 'python scripts/ingest.py' to process this data.")
        else:
            print("\nNo data was fetched. Please check your authorization and try again.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
