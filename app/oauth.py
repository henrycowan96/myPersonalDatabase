import os
import sys
import json as json_module
from pathlib import Path
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from urllib.parse import urlencode
import requests
sys.path.insert(0, str(Path(__file__).parent))

from utils import CREDENTIALS_DIR
import utils

# OAuth2 scopes for different Google services
GOOGLE_SCOPES = {
    'calendar': ['https://www.googleapis.com/auth/calendar.readonly'],
    'gmail': ['https://www.googleapis.com/auth/gmail.readonly'],
    'google_drive': ['https://www.googleapis.com/auth/drive.readonly']
}

# OAuth state storage (in production, use Redis or database)
oauth_states = {}


def get_oauth_config():
    """Load OAuth client configuration"""
    client_secrets_file = CREDENTIALS_DIR / "client_secret.json"
    if not client_secrets_file.exists():
        raise FileNotFoundError("Google OAuth credentials not found")
    
    with open(client_secrets_file, 'r') as f:
        return json_module.load(f)


def has_oauth_token(user_id: str, service: str) -> bool:
    """Check if OAuth token exists for a user and service"""
    print(f"[CREDS] Checking if OAuth token exists for user {user_id}, service {service}")
    if not utils.supabase:
        return False

    try:
        token_data = utils.supabase.table("oauth_tokens").select("*").eq("user_id", user_id).eq("service", service).execute()
        has_token = len(token_data.data) > 0
        print(f"[CREDS] OAuth token exists: {has_token}")
        return has_token
    except Exception as e:
        print(f"[CREDS] Error checking OAuth token: {e}")
        return False


def get_user_credentials(user_id: str, service: str):
    """Get OAuth credentials for a user and service from Supabase"""
    print(f"[CREDS] Getting credentials for user {user_id}, service {service}")
    if not utils.supabase:
        raise Exception("Supabase not initialized")

    try:
        token_data = utils.supabase.table("oauth_tokens").select("*").eq("user_id", user_id).eq("service", service).execute()

        if not token_data.data:
            print(f"[CREDS] ERROR: No OAuth token found for user {user_id} and service {service}")
            raise Exception(f"No OAuth token found for user {user_id} and service {service}")

        token = token_data.data[0]
        print(f"[CREDS] Found token for service {service}, expired: {token.get('expiry')}")

        # Create Credentials object
        creds = Credentials(
            token=token["token"],
            refresh_token=token["refresh_token"],
            token_uri=token["token_uri"],
            client_id=token["client_id"],
            client_secret=token["client_secret"],
            scopes=token["scopes"]
        )

        # Set expiry if available
        if token["expiry"]:
            creds.expiry = datetime.fromisoformat(token["expiry"])

        # Refresh if expired
        if creds.expired and creds.refresh_token:
            print(f"[CREDS] Token expired, refreshing...")
            creds.refresh(Request())

            # Update token in Supabase
            utils.supabase.table("oauth_tokens").update({
                "token": creds.token,
                "expiry": creds.expiry.isoformat() if creds.expiry else None
            }).eq("user_id", user_id).eq("service", service).execute()
            print(f"[CREDS] Token refreshed successfully")
        else:
            print(f"[CREDS] Token is valid, no refresh needed")

        return creds
    
    except Exception as e:
        raise Exception(f"Error getting credentials: {str(e)}")


def get_spotify_credentials(user_id: str):
    """Get Spotify OAuth credentials for a user from Supabase"""
    print(f"[SPOTIFY CREDS] Getting credentials for user {user_id}")
    if not utils.supabase:
        raise Exception("Supabase not initialized")

    try:
        token_data = utils.supabase.table("oauth_tokens").select("*").eq("user_id", user_id).eq("service", "spotify").execute()

        if not token_data.data:
            print(f"[SPOTIFY CREDS] ERROR: No Spotify token found for user {user_id}")
            raise Exception(f"No Spotify token found for user {user_id}")

        token = token_data.data[0]
        print(f"[SPOTIFY CREDS] Found Spotify token")

        # Check if token needs refresh
        expiry = token.get("expiry")
        if expiry:
            expiry_time = datetime.fromtimestamp(expiry)
            if datetime.now() >= expiry_time:
                print(f"[SPOTIFY CREDS] Token expired, refreshing...")
                # Refresh token
                refresh_token = token.get("refresh_token")
                client_id = token.get("client_id")
                client_secret = token.get("client_secret")
                
                token_url = "https://accounts.spotify.com/api/token"
                token_data_req = {
                    'grant_type': 'refresh_token',
                    'refresh_token': refresh_token,
                    'client_id': client_id,
                    'client_secret': client_secret
                }
                
                token_response = requests.post(token_url, data=token_data_req)
                token_response.raise_for_status()
                token_json = token_response.json()
                
                # Update token in Supabase
                new_expiry = datetime.now().timestamp() + token_json.get('expires_in', 3600)
                utils.supabase.table("oauth_tokens").update({
                    "token": token_json['access_token'],
                    "expiry": new_expiry
                }).eq("user_id", user_id).eq("service", "spotify").execute()
                
                return token_json['access_token']
            else:
                print(f"[SPOTIFY CREDS] Token is valid")
                return token["token"]
        else:
            return token["token"]
    
    except Exception as e:
        raise Exception(f"Error getting Spotify credentials: {str(e)}")
