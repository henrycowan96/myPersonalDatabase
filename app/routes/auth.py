import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from urllib.parse import urlencode
import requests
from google.oauth2.credentials import Credentials

from oauth import get_oauth_config, GOOGLE_SCOPES, oauth_states, has_oauth_token
import utils

router = APIRouter()


@router.get("/auth/callback")
async def oauth_callback(code: str = None, state: str = None, error: str = None, iss: str = None, scope: str = None):
    """Handle OAuth callback from Google"""
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")

    if state not in oauth_states:
        print(f"[OAUTH CALLBACK] Invalid state parameter: {state}")
        print(f"[OAUTH CALLBACK] Available states: {list(oauth_states.keys())}")
        
        # Check if this might be a duplicate callback - if tokens were just saved, return success
        # We can't check by user_id since we don't have it from the state, but we can check
        # if tokens were saved very recently (within last 30 seconds)
        if utils.supabase and scope:
            returned_scopes = scope.split(' ') if scope else []
            scope_to_service = {
                'https://www.googleapis.com/auth/calendar.readonly': 'calendar',
                'https://www.googleapis.com/auth/gmail.readonly': 'gmail',
                'https://www.googleapis.com/auth/drive.readonly': 'google_drive'
            }
            
            # Check if any of the services in the scope have tokens created very recently
            recent_threshold = datetime.utcnow() - timedelta(seconds=30)
            
            for returned_scope in returned_scopes:
                if returned_scope in scope_to_service:
                    service_to_check = scope_to_service[returned_scope]
                    # Look for tokens created in the last 30 seconds
                    existing_tokens = utils.supabase.table("oauth_tokens").select("*").eq("service", service_to_check).gte("created_at", recent_threshold.isoformat()).execute()
                    if existing_tokens.data:
                        print(f"[OAUTH CALLBACK] Found recently created tokens for {service_to_check}, treating as duplicate callback")
                        return {"service": service_to_check, "success": True}
        
        raise HTTPException(
            status_code=400,
            detail="Invalid state parameter. The authorization may have expired or the server was restarted. Please try authorizing again."
        )

    state_data = oauth_states[state]
    user_id = state_data["user_id"]
    service = state_data["service"]
    
    print(f"[OAUTH CALLBACK] Received callback for service: {service}")
    print(f"[OAUTH CALLBACK] Received scopes: {scope}")
    
    try:
        # Manually exchange authorization code for tokens
        config = get_oauth_config()
        client_id = config['web']['client_id']
        client_secret = config['web']['client_secret']
        
        token_url = "https://oauth2.googleapis.com/token"
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        token_data = {
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': f'{base_url}/auth/callback',
            'grant_type': 'authorization_code'
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_response.raise_for_status()
        token_json = token_response.json()
        
        # Parse returned scopes to determine which services were authorized
        returned_scopes = scope.split(' ') if scope else []
        print(f"[OAUTH CALLBACK] Parsed returned scopes: {returned_scopes}")
        
        # Only save token for the specific service that was requested (from state)
        # Don't save for all services in the returned scopes
        service_to_save = service
        print(f"[OAUTH CALLBACK] Saving token for service: {service_to_save}")
        
        # Google doesn't always return a refresh token on subsequent authorizations
        # Preserve existing refresh token if not provided in response
        refresh_token = token_json.get('refresh_token')
        if not refresh_token and utils.supabase:
            # Try to get existing token to preserve refresh token
            existing_tokens = utils.supabase.table("oauth_tokens").select("*").eq("user_id", user_id).eq("service", service_to_save).execute()
            if existing_tokens.data:
                existing_refresh_token = existing_tokens.data[0].get("refresh_token")
                if existing_refresh_token:
                    print(f"[OAUTH CALLBACK] Preserving existing refresh token for {service_to_save}")
                    refresh_token = existing_refresh_token
        
        # Create Credentials object from token response
        creds = Credentials(
            token=token_json['access_token'],
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=client_id,
            client_secret=client_secret,
            scopes=GOOGLE_SCOPES[service_to_save]
        )
        
        # Store credentials in Supabase
        if utils.supabase:
            credentials_data = {
                "user_id": user_id,
                "service": service_to_save,
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": creds.scopes,
                "expiry": creds.expiry.isoformat() if creds.expiry else None
            }

            # Delete existing token for this user/service if it exists, then insert new one
            utils.supabase.table("oauth_tokens").delete().eq("user_id", user_id).eq("service", service_to_save).execute()
            utils.supabase.table("oauth_tokens").insert(credentials_data).execute()
        
        # Clean up state
        del oauth_states[state]

        # Redirect to mobile app deep link
        from fastapi.responses import RedirectResponse
        return {"service": service, "success": True}

    except Exception as e:
        return {"service": service, "success": False, "error": str(e)}


@router.get("/auth/{service}")
async def authorize_google_service(service: str, user_id: str = Query(..., description="User ID")):
    """Initiate OAuth flow for a Google service"""
    # Prevent this route from matching 'callback' as a service
    if service == "callback":
        raise HTTPException(status_code=404, detail="Not found")
    
    if service not in GOOGLE_SCOPES:
        raise HTTPException(status_code=400, detail=f"Unknown service: {service}")
    
    try:
        config = get_oauth_config()
        client_id = config['web']['client_id']
        
        # Generate state parameter to prevent CSRF
        state = str(uuid.uuid4())
        oauth_states[state] = {
            "user_id": user_id,
            "service": service
        }
        
        # Manually construct authorization URL without PKCE
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        params = {
            'client_id': client_id,
            'redirect_uri': f'{base_url}/auth/callback',
            'scope': ' '.join(GOOGLE_SCOPES[service]),
            'response_type': 'code',
            'access_type': 'offline',
            'include_granted_scopes': 'true',
            'state': state
        }
        
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        
        return {"authorization_url": auth_url, "state": state}
    
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Google OAuth credentials not configured")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/status/{user_id}")
async def get_auth_status(user_id: str):
    """Get authorization status for all services for a user"""
    if not utils.supabase:
        raise HTTPException(status_code=503, detail="Supabase not initialized")
    
    try:
        # Get all OAuth tokens for the user
        tokens = utils.supabase.table("oauth_tokens").select("*").eq("user_id", user_id).execute()
        
        # Get user settings which contains stored permissions
        user_settings = utils.supabase.table("user_settings").select("*").eq("user_id", user_id).execute()
        stored_permissions = {}
        if user_settings.data:
            stored_permissions = user_settings.data[0].get("permissions", {})
        
        status = {}
        for service in GOOGLE_SCOPES.keys():
            service_tokens = [t for t in tokens.data if t["service"] == service]
            status[service] = len(service_tokens) > 0
        
        # Add local permissions from stored settings
        status["notes"] = stored_permissions.get("notes", False)
        status["appleCalendar"] = stored_permissions.get("appleCalendar", False)
        status["spotify"] = stored_permissions.get("spotify", False)
        
        return {"status": status}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Spotify OAuth Endpoints

@router.get("/spotify/authorize")
async def authorize_spotify(user_id: str = Query(..., description="User ID")):
    """Initiate Spotify OAuth flow"""
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", f"{base_url}/spotify/callback")
    
    if not client_id:
        raise HTTPException(status_code=500, detail="SPOTIFY_CLIENT_ID not configured")
    
    try:
        # Generate state parameter to prevent CSRF
        state = str(uuid.uuid4())
        oauth_states[state] = {
            "user_id": user_id,
            "service": "spotify"
        }
        
        # Spotify OAuth scopes
        scopes = [
            "user-read-private",
            "user-read-email",
            "user-library-read",
            "user-top-read",
            "user-read-playback-state",
            "user-read-recently-played",
            "playlist-read-private",
            "playlist-read-collaborative"
        ]
        
        params = {
            'client_id': client_id,
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'scope': ' '.join(scopes),
            'state': state
        }
        
        auth_url = f"https://accounts.spotify.com/authorize?{urlencode(params)}"
        
        return {"authorization_url": auth_url, "state": state}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/spotify/callback")
async def spotify_callback(code: str = None, state: str = None, error: str = None):
    """Handle Spotify OAuth callback"""
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")
    
    if state not in oauth_states:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    state_data = oauth_states[state]
    user_id = state_data["user_id"]
    
    try:
        # Exchange authorization code for tokens
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", f"{base_url}/spotify/callback")
        
        if not client_id or not client_secret:
            raise HTTPException(status_code=500, detail="Spotify credentials not configured")
        
        token_url = "https://accounts.spotify.com/api/token"
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_response.raise_for_status()
        token_json = token_response.json()
        
        # Store tokens in Supabase
        if utils.supabase:
            credentials_data = {
                "user_id": user_id,
                "service": "spotify",
                "token": token_json['access_token'],
                "refresh_token": token_json.get('refresh_token'),
                "token_uri": "https://accounts.spotify.com/api/token",
                "client_id": client_id,
                "client_secret": client_secret,
                "scopes": token_json.get('scope', ''),
                "expiry": (datetime.now().timestamp() + token_json.get('expires_in', 3600))
            }
            
            # Delete existing token for this user/service if it exists, then insert new one
            utils.supabase.table("oauth_tokens").delete().eq("user_id", user_id).eq("service", "spotify").execute()
            utils.supabase.table("oauth_tokens").insert(credentials_data).execute()
            
            # Update user settings to mark Spotify as authorized
            user_settings = utils.supabase.table("user_settings").select("*").eq("user_id", user_id).execute()
            if user_settings.data:
                current_permissions = user_settings.data[0].get("permissions", {})
                current_permissions["spotify"] = True
                
                utils.supabase.table("user_settings").update({
                    "permissions": current_permissions
                }).eq("user_id", user_id).execute()
        
        # Clean up state
        del oauth_states[state]
        
        # Redirect to mobile app deep link
        from fastapi.responses import RedirectResponse
        return {"service": "spotify", "success": True}
    
    except Exception as e:
        return {"service": "spotify", "success": False, "error": str(e)}
