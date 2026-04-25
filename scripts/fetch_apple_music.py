import os
import sys
from pathlib import Path
from datetime import datetime
import json
import time
import jwt

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from metadata_utils import generate_metadata, save_with_metadata

"""
Apple Music Integration Notes:
================================
This script uses the Apple Music API to fetch user's library, playlists, and listening history.

Requirements:
- Apple Developer Account
- MusicKit Identifier and Private Key (.p8 file)
- Team ID and Key ID from Apple Developer portal
- pyjwt library (pip install pyjwt[crypto])

Apple Music API requires a JWT developer token for authentication. The token is signed
using the private key from Apple Developer account and includes claims for MusicKit access.
"""

# Configuration
RAW_DOCS_DIR = Path(__file__).parent.parent / "data" / "raw_docs"
APPLE_MUSIC_DIR = RAW_DOCS_DIR / "apple_music"
CREDENTIALS_DIR = Path(__file__).parent.parent / "credentials"

# Create directories if they don't exist
RAW_DOCS_DIR.mkdir(parents=True, exist_ok=True)
APPLE_MUSIC_DIR.mkdir(parents=True, exist_ok=True)
CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

def generate_developer_token(key_id, team_id, private_key_path):
    """Generate a JWT developer token for Apple Music API"""
    try:
        # Read the private key
        with open(private_key_path, 'r') as f:
            private_key = f.read()
        
        # Current time and expiration (6 months from now)
        now = int(time.time())
        expiration = now + (6 * 30 * 24 * 60 * 60)
        
        # Create JWT payload
        payload = {
            'iss': team_id,
            'iat': now,
            'exp': expiration,
            'sub': 'user-music-library-read'
        }
        
        # Sign the token
        token = jwt.encode(payload, private_key, algorithm='ES256', headers={'kid': key_id})
        
        return token
    except Exception as e:
        print(f"Error generating developer token: {e}")
        return None

def fetch_user_library(token, storefront='us'):
    """Fetch user's music library from Apple Music"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Music-User-Token': ''  # This would be set after user authorization
    }
    
    # For now, we'll fetch catalog search results since full library access requires user OAuth
    # This is a simplified version that demonstrates the integration
    base_url = f'https://api.music.apple.com/v1/catalog/{storefront}'
    
    try:
        # Search for popular tracks as a sample
        search_url = f'{base_url}/search'
        params = {
            'term': 'popular',
            'types': 'songs,albums,artists',
            'limit': 20
        }
        
        import requests
        response = requests.get(search_url, headers=headers, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching library: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error fetching library: {e}")
        return None

def format_song(song):
    """Format a song as text"""
    attributes = song.get('attributes', {})
    name = attributes.get('name', 'Unknown')
    artist = attributes.get('artistName', 'Unknown')
    album = attributes.get('albumName', 'Unknown')
    duration = attributes.get('durationInMillis', 0) / 1000  # Convert to seconds
    play_count = attributes.get('playCount', 0)
    
    song_text = f"Song: {name}\n"
    song_text += f"Artist: {artist}\n"
    song_text += f"Album: {album}\n"
    song_text += f"Duration: {duration:.1f} seconds\n"
    
    if play_count:
        song_text += f"Play Count: {play_count}\n"
    
    return song_text

def format_album(album):
    """Format an album as text"""
    attributes = album.get('attributes', {})
    name = attributes.get('name', 'Unknown')
    artist = attributes.get('artistName', 'Unknown')
    release_date = attributes.get('releaseDate', 'Unknown')
    genre = attributes.get('genreNames', [])
    
    album_text = f"Album: {name}\n"
    album_text += f"Artist: {artist}\n"
    album_text += f"Release Date: {release_date}\n"
    
    if genre:
        album_text += f"Genres: {', '.join(genre)}\n"
    
    return album_text

def format_artist(artist):
    """Format an artist as text"""
    attributes = artist.get('attributes', {})
    name = attributes.get('name', 'Unknown')
    genre = attributes.get('genreNames', [])
    
    artist_text = f"Artist: {name}\n"
    
    if genre:
        artist_text += f"Genres: {', '.join(genre)}\n"
    
    return artist_text

def save_music_data(data, data_type):
    """Save music data to a text file with metadata"""
    if not data:
        return None
    
    filename = f"{data_type}_data.txt"
    output_path = APPLE_MUSIC_DIR / filename
    
    # Generate metadata
    metadata = generate_metadata(
        source="apple_music",
        type=data_type,
        author=None,
        created_date=datetime.now().isoformat(),
        modified_date=None,
        data_type=data_type
    )
    
    # Format the content
    content = f"Apple Music {data_type.title()}\n"
    content += f"Extracted: {datetime.now().isoformat()}\n"
    content += "=" * 50 + "\n\n"
    
    if data_type == 'songs':
        songs = data.get('results', {}).get('songs', {}).get('data', [])
        for song in songs:
            song_text = format_song(song)
            content += song_text
            content += "\n" + "-" * 50 + "\n\n"
        metadata['song_count'] = len(songs)
    
    elif data_type == 'albums':
        albums = data.get('results', {}).get('albums', {}).get('data', [])
        for album in albums:
            album_text = format_album(album)
            content += album_text
            content += "\n" + "-" * 50 + "\n\n"
        metadata['album_count'] = len(albums)
    
    elif data_type == 'artists':
        artists = data.get('results', {}).get('artists', {}).get('data', [])
        for artist in artists:
            artist_text = format_artist(artist)
            content += artist_text
            content += "\n" + "-" * 50 + "\n\n"
        metadata['artist_count'] = len(artists)
    
    # Save with metadata header
    save_with_metadata(output_path, content, metadata)
    
    return output_path

def main():
    print("Fetching Apple Music data...")
    print("\nNote: You need Apple Developer credentials to access the Music API.")
    print("Get them from: https://developer.apple.com/account/resources/musickit/list")
    
    # Get credentials
    key_id = input("\nEnter your Key ID (from Apple Developer): ").strip()
    if not key_id:
        print("Key ID is required.")
        return
    
    team_id = input("Enter your Team ID (from Apple Developer): ").strip()
    if not team_id:
        print("Team ID is required.")
        return
    
    private_key_path = input("Enter path to your .p8 private key file: ").strip()
    if not private_key_path:
        print("Private key path is required.")
        return
    
    # Check if private key exists
    key_path = Path(private_key_path)
    if not key_path.exists():
        print(f"Private key file not found at: {private_key_path}")
        return
    
    # Generate developer token
    print("\nGenerating developer token...")
    token = generate_developer_token(key_id, team_id, private_key_path)
    
    if not token:
        print("Failed to generate developer token. Please check your credentials.")
        return
    
    print("Developer token generated successfully!")
    
    # Fetch music data
    print("\nFetching music data from Apple Music...")
    data = fetch_user_library(token)
    
    if not data:
        print("Failed to fetch music data.")
        return
    
    print("Data fetched successfully!")
    
    # Save different types of data
    print("\nSaving music data...")
    
    success_count = 0
    
    # Save songs
    songs_data = {'results': {'songs': data.get('results', {}).get('songs', {})}}
    if songs_data['results']['songs'].get('data'):
        output_path = save_music_data(songs_data, 'songs')
        if output_path:
            print(f"Saved songs data -> {output_path.name}")
            success_count += 1
    
    # Save albums
    albums_data = {'results': {'albums': data.get('results', {}).get('albums', {})}}
    if albums_data['results']['albums'].get('data'):
        output_path = save_music_data(albums_data, 'albums')
        if output_path:
            print(f"Saved albums data -> {output_path.name}")
            success_count += 1
    
    # Save artists
    artists_data = {'results': {'artists': data.get('results', {}).get('artists', {})}}
    if artists_data['results']['artists'].get('data'):
        output_path = save_music_data(artists_data, 'artists')
        if output_path:
            print(f"Saved artists data -> {output_path.name}")
            success_count += 1
    
    print(f"\nComplete! Saved {success_count} data files to {APPLE_MUSIC_DIR}")
    print("You can now run 'python scripts/ingest.py' to process this data.")
    print("\nNote: This is a simplified version using catalog search.")
    print("For full library access, you need to implement user OAuth authorization.")

if __name__ == "__main__":
    main()
