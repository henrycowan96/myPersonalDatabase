import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from oauth import get_spotify_credentials


async def fetch_spotify_data(user_id: str):
    """Fetch Spotify data using OAuth credentials"""
    try:
        print(f"[SPOTIFY FETCH] Starting Spotify data fetch for user {user_id}")
        
        # Get access token
        access_token = get_spotify_credentials(user_id)
        
        # Import the Spotify client from the fetch script
        sys.path.append(str(Path(__file__).parent.parent.parent / "scripts"))
        from fetch_spotify import SpotifyClient, save_spotify_data
        
        # Create Spotify client (we already have the token, so we don't need to re-auth)
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", f"{base_url}/spotify/callback")
        
        client = SpotifyClient(client_id, client_secret, redirect_uri, access_token=access_token)
        
        # Fetch all data
        saved_files = []
        
        # Get user profile
        print("[SPOTIFY FETCH] Fetching user profile...")
        profile = client.get_user_profile()
        spotify_user_id = profile.get("id", "unknown")
        
        # Get top tracks
        print("[SPOTIFY FETCH] Fetching top tracks...")
        top_tracks = client.get_top_tracks(limit=50, time_range="medium_term")
        if top_tracks.get("items"):
            output_path = save_spotify_data(top_tracks, 'top_tracks', spotify_user_id)
            if output_path:
                saved_files.append(str(output_path))
                print(f"Saved top tracks -> {output_path.name}")
        
        # Get top artists
        print("[SPOTIFY FETCH] Fetching top artists...")
        top_artists = client.get_top_artists(limit=50, time_range="medium_term")
        if top_artists.get("items"):
            output_path = save_spotify_data(top_artists, 'top_artists', spotify_user_id)
            if output_path:
                saved_files.append(str(output_path))
                print(f"Saved top artists -> {output_path.name}")
        
        # Get saved tracks
        print("[SPOTIFY FETCH] Fetching saved tracks...")
        saved_tracks = client.get_saved_tracks(limit=50)
        if saved_tracks.get("items"):
            output_path = save_spotify_data(saved_tracks, 'saved_tracks', spotify_user_id)
            if output_path:
                saved_files.append(str(output_path))
                print(f"Saved tracks -> {output_path.name}")
        
        # Get playlists
        print("[SPOTIFY FETCH] Fetching playlists...")
        playlists = client.get_playlists(limit=50)
        if playlists.get("items"):
            output_path = save_spotify_data(playlists, 'playlists', spotify_user_id)
            if output_path:
                saved_files.append(str(output_path))
                print(f"Saved playlists -> {output_path.name}")
        
        # Get recently played
        print("[SPOTIFY FETCH] Fetching recently played...")
        recently_played = client.get_recently_played(limit=50)
        if recently_played.get("items"):
            output_path = save_spotify_data(recently_played, 'recently_played', spotify_user_id)
            if output_path:
                saved_files.append(str(output_path))
                print(f"Saved recently played -> {output_path.name}")
        
        print(f"[SPOTIFY FETCH] Total files saved: {len(saved_files)}")
        return saved_files
        
    except Exception as e:
        print(f"[SPOTIFY FETCH] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Error fetching Spotify data: {str(e)}")
