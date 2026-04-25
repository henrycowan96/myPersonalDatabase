# Apple Music Integration Setup Guide

This guide explains how to set up and use the Apple Music API integration for your Personal Database.

## Overview

The Apple Music integration allows you to fetch and index music data (songs, albums, artists) from Apple Music into your personal database. This data can then be queried using semantic search.

## Prerequisites

### Apple Developer Account

To use the Apple Music API, you need:
1. An Apple Developer Program membership ($99/year)
2. Access to the Apple Developer portal

### Generate MusicKit Credentials

1. Go to [Apple Developer Portal](https://developer.apple.com/account/resources/musickit/list)
2. Click "Create a MusicKit Identifier"
3. Enter a name and description
4. Save the MusicKit ID

5. Go to [Keys](https://developer.apple.com/account/resources/authkeys/list)
6. Click "Create a Key"
7. Select "MusicKit" as the key type
8. Download the `.p8` private key file (you can only download it once!)
9. Note down:
   - **Key ID** (10-character alphanumeric string)
   - **Team ID** (10-character alphanumeric string)

## Installation

1. Install the required dependencies:
```bash
pip install pyjwt[crypto]
```

Or update your requirements.txt (already included in the project).

## Configuration

Add the following environment variables to your `.env` file:

```env
APPLE_MUSIC_KEY_ID=your_key_id_here
APPLE_MUSIC_TEAM_ID=your_team_id_here
APPLE_MUSIC_PRIVATE_KEY_PATH=/path/to/your/private_key.p8
```

**Important:** Keep your `.p8` private key file secure. Never commit it to version control.

## Usage

### Standalone Script

You can run the standalone script to fetch Apple Music data:

```bash
python scripts/fetch_apple_music.py
```

The script will prompt you for:
- Key ID
- Team ID
- Path to your .p8 private key file

The fetched data will be saved to `data/raw_docs/apple_music/` with metadata headers.

### Backend API Integration

The Apple Music integration is also integrated into the backend API:

1. **Fetch Apple Music Data Endpoint**
   ```bash
   POST /fetch-apple-music
   ```
   Request body:
   ```json
   {
     "key_id": "your_key_id",
     "team_id": "your_team_id",
     "private_key_path": "/path/to/key.p8",
     "storefront": "us"
   }
   ```

2. **Automatic Ingestion During Setup**
   When you run the setup flow in the mobile app, if `appleMusic: true` is in the permissions and the environment variables are set, the system will automatically fetch and ingest Apple Music data.

## Data Processing

The integration processes three types of music data:

1. **Songs**: Name, artist, album, duration, genres
2. **Albums**: Name, artist, release date, genres
3. **Artists**: Name, genres

Each item is converted to text format and embedded into the vector database for semantic search.

## Entity Extraction

The entity extraction system has been updated to recognize music-related topics:
- Keywords: song, album, artist, band, music, playlist, track, genre, concert, vinyl, spotify, apple music
- Topic tag: `music`

This allows you to filter queries by music-related content.

## Limitations

### Current Implementation

The current implementation uses the Apple Music Catalog API to search for popular music. This is a simplified version that:
- Does not require user OAuth authorization
- Fetches catalog data rather than personal library data
- Uses a search query ("popular") to get sample data

### Full Library Access

To access a user's personal music library (playlists, listening history, etc.), you would need to:
1. Implement user OAuth authorization flow
2. Store user MusicKit tokens securely
3. Use the user-specific API endpoints

This would require additional frontend UI for OAuth consent and backend token management.

## Security Notes

- The `.p8` private key file is sensitive and should never be shared
- JWT tokens are generated with a 6-month expiration
- In production, consider storing credentials in a secure vault (e.g., AWS Secrets Manager, HashiCorp Vault)
- Never commit credentials to version control

## Troubleshooting

### "Private key file not found"
- Ensure the path in `APPLE_MUSIC_PRIVATE_KEY_PATH` is correct
- Use absolute paths to avoid path resolution issues

### "Failed to generate developer token"
- Verify your Key ID and Team ID are correct
- Ensure the .p8 file is valid and not corrupted
- Check that pyjwt[crypto] is installed correctly

### "API error: 401"
- Your credentials may be invalid or expired
- Verify you have an active Apple Developer membership
- Check that the MusicKit identifier is properly configured

### "No data fetched"
- The API may be rate-limited
- Try a different storefront (e.g., "gb", "de", "jp")
- Check the API response in the logs for more details

## Future Enhancements

Potential improvements for the integration:
1. User OAuth for personal library access
2. Playlist ingestion and analysis
3. Listening history tracking
4. Music recommendation features
5. Integration with other music services (Spotify, etc.)
6. Advanced music analytics (genre distribution, listening patterns)
