import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form, Body
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import UploadDocumentsRequest
from utils import RAW_DOCS_DIR
import utils
from services.google_services import fetch_calendar_data, fetch_gmail_data, fetch_google_drive_data
from services.apple_services import fetch_apple_calendar, fetch_apple_music_data
from data_processor import process_and_ingest_data
from oauth import has_oauth_token, get_user_credentials

router = APIRouter()


@router.post("/upload-messages")
async def upload_messages(file: UploadFile = File(...), user_id: str = Form(...)):
    """Upload and process mobile message export file"""
    print(f"[MESSAGE UPLOAD] Starting message upload for user {user_id}")
    print(f"[MESSAGE UPLOAD] File: {file.filename}, Type: {file.content_type}")

    try:
        # Create message_exports directory if it doesn't exist
        message_exports_dir = RAW_DOCS_DIR / "message_exports"
        message_exports_dir.mkdir(parents=True, exist_ok=True)

        # Save uploaded file
        file_path = message_exports_dir / file.filename
        print(f"[MESSAGE UPLOAD] Saving file to {file_path}")

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Process the message file using parse_messages script
        print(f"[MESSAGE UPLOAD] Processing message file...")
        sys.path.append(str(Path(__file__).parent.parent.parent / "scripts"))
        from parse_messages import parse_messages

        # Call parse_messages with the uploaded file
        parse_messages(input_file=file_path)

        print(f"[MESSAGE UPLOAD] Message processing complete")

        return {
            "message": f"Successfully uploaded and processed {file.filename}",
            "file": file.filename
        }

    except Exception as e:
        print(f"[MESSAGE UPLOAD] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-android-sms")
async def upload_android_sms(user_id: str = Body(...), messages: List[dict] = Body(...)):
    """Receive and process SMS messages from Android device"""
    print(f"[ANDROID SMS] Starting SMS upload for user {user_id}")
    print(f"[ANDROID SMS] Received {len(messages)} messages")

    try:
        # Create message_exports directory if it doesn't exist
        message_exports_dir = RAW_DOCS_DIR / "message_exports"
        message_exports_dir.mkdir(parents=True, exist_ok=True)

        # Save messages as JSON file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = message_exports_dir / f"android_sms_{timestamp}.json"

        with open(file_path, "w") as f:
            json.dump(messages, f, indent=2)

        print(f"[ANDROID SMS] Saved messages to {file_path}")

        # Process the messages using parse_messages script
        print(f"[ANDROID SMS] Processing messages...")
        sys.path.append(str(Path(__file__).parent.parent.parent / "scripts"))
        from parse_messages import parse_messages

        # Call parse_messages with the JSON file
        parse_messages(input_file=file_path)

        print(f"[ANDROID SMS] Message processing complete")

        return {
            "message": f"Successfully processed {len(messages)} SMS messages",
            "count": len(messages)
        }

    except Exception as e:
        print(f"[ANDROID SMS] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-documents")
async def upload_documents(request: UploadDocumentsRequest, background_tasks: BackgroundTasks):
    """Upload documents based on user permissions"""
    print(f"[UPLOAD] Starting document upload for user {request.user_id}")
    print(f"[UPLOAD] Permissions: {request.permissions}")
    try:
        # Get user's Pinecone index
        if not utils.supabase:
            raise HTTPException(status_code=503, detail="Supabase not initialized")

        print(f"[UPLOAD] Fetching user settings...")
        user_settings = utils.supabase.table("user_settings").select("*").eq("user_id", request.user_id).execute()

        if not user_settings.data:
            print(f"[UPLOAD] ERROR: User database not found")
            raise HTTPException(status_code=400, detail="User database not found. Please create database first.")

        pinecone_index_name = user_settings.data[0].get("pinecone_index")
        print(f"[UPLOAD] Using Pinecone index: {pinecone_index_name}")

        # Get existing permissions and uploaded data sources
        existing_permissions = user_settings.data[0].get("permissions", {})
        uploaded_data_sources = user_settings.data[0].get("uploaded_data_sources", {})
        print(f"[UPLOAD] Existing permissions: {existing_permissions}")
        print(f"[UPLOAD] Uploaded data sources: {uploaded_data_sources}")

        # Determine which permissions need data uploaded
        # A permission needs upload if it's True and hasn't been uploaded yet
        permissions_to_upload = {}
        for key, value in request.permissions.items():
            if value and not uploaded_data_sources.get(key):
                permissions_to_upload[key] = value
                print(f"[UPLOAD] Permission needs upload: {key} = {value} (uploaded: {uploaded_data_sources.get(key)})")

        if not permissions_to_upload:
            print(f"[UPLOAD] No new data to upload. All enabled permissions already uploaded.")
            # Still save the permissions to ensure they're up to date
            utils.supabase.table("user_settings").update({
                "permissions": request.permissions,
                "setup_step": 3
            }).eq("user_id", request.user_id).execute()
            return {"message": "No new data to upload", "results": {}}

        print(f"[UPLOAD] Permissions to upload data for: {permissions_to_upload}")

        # Save permissions to Supabase
        print(f"[UPLOAD] Saving permissions to Supabase...")
        utils.supabase.table("user_settings").update({
            "permissions": request.permissions,
            "setup_step": 3
        }).eq("user_id", request.user_id).execute()

        # Fetch data based on permissions that need upload
        results = {}

        if permissions_to_upload.get("appleCalendar"):
            print(f"[UPLOAD] Processing appleCalendar permission (NEW)...")
            try:
                calendar_response = await fetch_apple_calendar(request.apple_calendar_email, request.apple_calendar_password)
                events_data = calendar_response["events"]
                count = await process_and_ingest_data(request.user_id, 'apple_calendar', events_data, pinecone_index_name)
                results['appleCalendar'] = count
                print(f"[UPLOAD] Apple Calendar processing complete: {count} documents")
            except Exception as e:
                print(f"[UPLOAD] ERROR fetching apple calendar: {e}")
                import traceback
                traceback.print_exc()
                results['appleCalendar'] = 0
        elif request.permissions.get("appleCalendar"):
            print(f"[UPLOAD] Skipping appleCalendar (data already uploaded)")

        if permissions_to_upload.get("calendar"):
            print(f"[UPLOAD] Processing Google Calendar permission (NEW)...")
            try:
                # Check if OAuth token exists before attempting to fetch
                if not has_oauth_token(request.user_id, 'calendar'):
                    print(f"[UPLOAD] No OAuth token found for Google Calendar, skipping. User needs to authorize via /auth/calendar endpoint.")
                    results['calendar'] = 0
                else:
                    creds = get_user_credentials(request.user_id, 'calendar')
                    calendar_data = await fetch_calendar_data(request.user_id, creds)
                    count = await process_and_ingest_data(request.user_id, 'google_calendar', calendar_data, pinecone_index_name)
                    results['calendar'] = count
                    print(f"[UPLOAD] Google Calendar processing complete: {count} documents")
            except Exception as e:
                print(f"[UPLOAD] ERROR fetching google calendar: {e}")
                import traceback
                traceback.print_exc()
                results['calendar'] = 0
        elif request.permissions.get("calendar"):
            print(f"[UPLOAD] Skipping calendar (data already uploaded)")

        if permissions_to_upload.get("email"):
            print(f"[UPLOAD] Processing email permission (NEW)...")
            try:
                # Check if OAuth token exists before attempting to fetch
                if not has_oauth_token(request.user_id, 'gmail'):
                    print(f"[UPLOAD] No OAuth token found for Gmail, skipping. User needs to authorize via /auth/gmail endpoint.")
                    results['email'] = 0
                else:
                    creds = get_user_credentials(request.user_id, 'gmail')
                    gmail_data = await fetch_gmail_data(request.user_id, creds)
                    count = await process_and_ingest_data(request.user_id, 'gmail', gmail_data, pinecone_index_name)
                    results['email'] = count
                    print(f"[UPLOAD] Gmail processing complete: {count} documents")
            except Exception as e:
                print(f"[UPLOAD] ERROR fetching gmail: {e}")
                import traceback
                traceback.print_exc()
                results['email'] = 0
        elif request.permissions.get("email"):
            print(f"[UPLOAD] Skipping email (data already uploaded)")

        if permissions_to_upload.get("googleDrive"):
            print(f"[UPLOAD] Processing googleDrive permission (NEW)...")
            try:
                # Check if OAuth token exists before attempting to fetch
                if not has_oauth_token(request.user_id, 'google_drive'):
                    print(f"[UPLOAD] No OAuth token found for Google Drive, skipping. User needs to authorize via /auth/google_drive endpoint.")
                    results['googleDrive'] = 0
                else:
                    creds = get_user_credentials(request.user_id, 'google_drive')
                    drive_data = await fetch_google_drive_data(request.user_id, creds)
                    count = await process_and_ingest_data(request.user_id, 'google_drive', drive_data, pinecone_index_name)
                    results['googleDrive'] = count
                    print(f"[UPLOAD] Google Drive processing complete: {count} documents")
            except Exception as e:
                print(f"[UPLOAD] ERROR fetching google drive: {e}")
                import traceback
                traceback.print_exc()
                results['googleDrive'] = 0
        elif request.permissions.get("googleDrive"):
            print(f"[UPLOAD] Skipping googleDrive (data already uploaded)")

        if permissions_to_upload.get("notes"):
            print(f"[UPLOAD] Processing notes permission (NEW)...")
            try:
                from services.apple_services import fetch_apple_notes
                notes_response = await fetch_apple_notes()
                notes_data = notes_response["notes"]
                count = await process_and_ingest_data(request.user_id, 'apple_notes', notes_data, pinecone_index_name)
                results['notes'] = count
                print(f"[UPLOAD] Apple Notes processing complete: {count} documents")
            except Exception as e:
                print(f"[UPLOAD] ERROR fetching apple notes: {e}")
                import traceback
                traceback.print_exc()
                results['notes'] = 0
        elif request.permissions.get("notes"):
            print(f"[UPLOAD] Skipping notes (data already uploaded)")

        if permissions_to_upload.get("appleMusic"):
            print(f"[UPLOAD] Processing appleMusic permission (NEW)...")
            try:
                # Apple Music requires developer credentials (key_id, team_id, private_key_path)
                # These would need to be stored in user settings or environment variables
                # For now, we'll check if they're available in environment
                key_id = os.getenv("APPLE_MUSIC_KEY_ID")
                team_id = os.getenv("APPLE_MUSIC_TEAM_ID")
                private_key_path = os.getenv("APPLE_MUSIC_PRIVATE_KEY_PATH")
                
                if key_id and team_id and private_key_path:
                    music_data = await fetch_apple_music_data(key_id, team_id, private_key_path)
                    count = await process_and_ingest_data(request.user_id, 'apple_music', music_data, pinecone_index_name)
                    results['appleMusic'] = count
                    print(f"[UPLOAD] Apple Music processing complete: {count} documents")
                else:
                    print(f"[UPLOAD] Apple Music credentials not found in environment, skipping")
                    results['appleMusic'] = 0
            except Exception as e:
                print(f"[UPLOAD] ERROR fetching apple music: {e}")
                import traceback
                traceback.print_exc()
                results['appleMusic'] = 0
        elif request.permissions.get("appleMusic"):
            print(f"[UPLOAD] Skipping appleMusic (data already uploaded)")

        # Update uploaded_data_sources to mark successfully uploaded data sources
        successfully_uploaded = {}
        for key, count in results.items():
            if count > 0:
                successfully_uploaded[key] = True

        if successfully_uploaded:
            print(f"[UPLOAD] Marking data sources as uploaded: {successfully_uploaded}")
            # Merge with existing uploaded_data_sources
            updated_uploaded_data_sources = {**uploaded_data_sources, **successfully_uploaded}
            utils.supabase.table("user_settings").update({
                "uploaded_data_sources": updated_uploaded_data_sources
            }).eq("user_id", request.user_id).execute()

        total_processed = sum(results.values())
        print(f"[UPLOAD] Total documents processed: {total_processed}")
        print(f"[UPLOAD] Results breakdown: {results}")

        # Mark setup as complete
        print(f"[UPLOAD] Marking setup as complete...")
        utils.supabase.table("user_settings").update({
            "setup_step": 4  # 4 = complete
        }).eq("user_id", request.user_id).execute()

        return {
            "message": f"Successfully processed {total_processed} documents",
            "details": results
        }

    except Exception as e:
        print(f"[UPLOAD] FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
