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
from insights_engine import analyze_documents_for_insights
from pinecone import Pinecone

router = APIRouter()


async def regenerate_and_save_insights(user_id: str):
    """Background task to regenerate insights after new data is uploaded"""
    try:
        print(f"[INSIGHTS REGEN] Starting insight regeneration for user {user_id}")
        
        if not utils.embedding_model:
            print("[INSIGHTS REGEN] Embedding model not initialized, skipping")
            return
        
        # Get user's Pinecone index
        user_settings = utils.supabase.table("user_settings").select("*").eq("user_id", user_id).execute()
        if not user_settings.data:
            print("[INSIGHTS REGEN] User settings not found, skipping")
            return
        
        pinecone_index_name = user_settings.data[0].get("pinecone_index")
        if not pinecone_index_name:
            print("[INSIGHTS REGEN] No Pinecone index found, skipping")
            return
        
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index_to_use = pc.Index(pinecone_index_name)
        
        # Query Pinecone for documents
        query_embedding = utils.embedding_model.encode(
            "important events activities people places work personal life"
        ).tolist()
        
        results = index_to_use.query(
            vector=query_embedding,
            top_k=20,
            include_metadata=True
        )
        
        documents = []
        for match in results.get('matches', []):
            metadata = match.get('metadata', {})
            if metadata.get('text'):
                documents.append({
                    'id': match.get('id'),
                    'metadata': metadata,
                    'score': match.get('score', 0)
                })
        
        if not documents:
            print("[INSIGHTS REGEN] No documents found, skipping")
            return
        
        # Generate insights
        insights = analyze_documents_for_insights(documents, user_id)
        print(f"[INSIGHTS REGEN] Generated {len(insights)} insights")
        
        if not insights:
            return
        
        # Save insights to Supabase
        saved_count = 0
        for insight in insights:
            record = {
                'user_id': user_id,
                'insight_id': insight.get('id', f"insight_{saved_count}"),
                'category': insight.get('category', 'general'),
                'title': insight.get('title', 'Untitled Insight'),
                'description': insight.get('description', ''),
                'significance_score': insight.get('significance_score', 0.5),
                'sources': insight.get('sources', []),
                'detected_at': insight.get('detected_at', datetime.now().isoformat()),
                'time_context': insight.get('time_context', {}),
                'entities': insight.get('entities', []),
                'actionable': insight.get('actionable', False),
            }
            result = utils.supabase.table("user_insights").upsert(
                record,
                on_conflict="user_id,insight_id"
            ).execute()
            if result.data:
                saved_count += 1
        
        print(f"[INSIGHTS REGEN] Saved {saved_count} insights to database")
        
        # Generate and save LLM thoughts based on new insights
        from services.llm_service import LLMService
        llm_service = LLMService()
        
        prompts = [
            {"type": "summary", "title": "Life Summary", "prompt": f"Based on these insights, provide a comprehensive summary. Insights: {insights}"},
            {"type": "recommendations", "title": "Actionable Recommendations", "prompt": f"Based on these insights, provide 3-5 actionable recommendations. Insights: {insights}"},
            {"type": "patterns", "title": "Emerging Patterns", "prompt": f"Analyze these insights and identify significant patterns. Insights: {insights}"},
            {"type": "opportunities", "title": "Growth Opportunities", "prompt": f"What are the biggest opportunities for personal growth? Insights: {insights}"},
            {"type": "reflection", "title": "Deep Reflection", "prompt": f"Provide a thoughtful reflection on what these insights reveal. Insights: {insights}"},
        ]
        
        thoughts = []
        for prompt_data in prompts:
            try:
                response = await llm_service.generate_response(prompt_data["prompt"])
                thoughts.append({
                    'id': f"{prompt_data['type']}_{datetime.now().timestamp()}",
                    'thought_type': prompt_data["type"],
                    'title': prompt_data["title"],
                    'content': response,
                    'prompt_used': prompt_data["prompt"],
                    'generated_at': datetime.now().isoformat(),
                })
            except Exception as e:
                print(f"[INSIGHTS REGEN] Error generating thought: {e}")
                continue
        
        # Save thoughts to Supabase
        thought_count = 0
        for thought in thoughts:
            result = utils.supabase.table("llm_thoughts").upsert(
                {
                    'user_id': user_id,
                    'thought_id': thought['id'],
                    'thought_type': thought['thought_type'],
                    'title': thought['title'],
                    'content': thought['content'],
                    'prompt_used': thought['prompt_used'],
                    'generated_at': thought['generated_at'],
                },
                on_conflict="user_id,thought_id"
            ).execute()
            if result.data:
                thought_count += 1
        
        print(f"[INSIGHTS REGEN] Saved {thought_count} thoughts to database")

        # Promote confirmed candidate facts to real facts
        try:
            from facts.pipeline import promote_confirmed_candidates
            promoted = await promote_confirmed_candidates(user_id)
            print(f"[INSIGHTS REGEN] Promoted {promoted} candidate facts")
        except Exception as e:
            print(f"[INSIGHTS REGEN] Error promoting candidates: {e}")
        
    except Exception as e:
        print(f"[INSIGHTS REGEN] ERROR: {e}")
        import traceback
        traceback.print_exc()


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
    print(f"[UPLOAD] ===== STARTING DOCUMENT UPLOAD =====")
    print(f"[UPLOAD] User ID: {request.user_id}")
    print(f"[UPLOAD] Requested permissions: {request.permissions}")
    print(f"[UPLOAD] Timestamp: {datetime.now().isoformat()}")
    
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
        
        # Detailed analysis of each permission
        print(f"[UPLOAD] ===== PERMISSION ANALYSIS =====")
        for key, value in request.permissions.items():
            existing_value = existing_permissions.get(key, False)
            upload_status = uploaded_data_sources.get(key)
            print(f"[UPLOAD] {key}: requested={value}, existing={existing_value}, upload_status={upload_status}")
        print(f"[UPLOAD] ===== END PERMISSION ANALYSIS =====")

        # Determine which permissions need data uploaded
        # Upload data if permission is True and either:
        # 1. Permission is newly granted (was False before, now True)
        # 2. Permission existed but data has never been uploaded before (upload_status is None)
        permissions_to_upload = {}
        for key, value in request.permissions.items():
            existing_value = existing_permissions.get(key, False)  # Default to False if not existing
            upload_status = uploaded_data_sources.get(key)
            
            # Upload if:
            # 1. Permission is True now
            # 2. Either permission is newly granted OR data has never been uploaded before (upload_status is None)
            # Note: We do NOT upload if upload_status is False (failed upload) to prevent infinite loops
            if value and (not existing_value or upload_status is None):
                permissions_to_upload[key] = value
                if not existing_value:
                    print(f"[UPLOAD] Permission newly granted: {key} = {value} (was: {existing_value}, uploaded: {upload_status})")
                else:
                    print(f"[UPLOAD] Permission exists but never uploaded: {key} = {value} (uploaded: {upload_status})")
            elif value and existing_value and upload_status is True:
                print(f"[UPLOAD] Permission already uploaded: {key} = {value} (uploaded: {upload_status})")
            elif value and existing_value and upload_status is False:
                print(f"[UPLOAD] Permission previously failed, skipping to prevent infinite loop: {key} = {value} (uploaded: {upload_status})")

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

        # Update uploaded_data_sources to mark both successfully uploaded and attempted data sources
        # This prevents infinite loops when uploads fail
        upload_status = {}
        for key, count in results.items():
            # Mark as uploaded if successful, mark as attempted if failed
            if count > 0:
                upload_status[key] = True  # Successfully uploaded
            else:
                upload_status[key] = False  # Attempted but failed

        if upload_status:
            print(f"[UPLOAD] Marking data sources upload status: {upload_status}")
            # Merge with existing uploaded_data_sources, but only mark successful ones as uploaded
            # Failed ones are marked as False to prevent infinite retries
            updated_uploaded_data_sources = {**uploaded_data_sources}
            for key, status in upload_status.items():
                if status:  # Only mark as uploaded if successful
                    updated_uploaded_data_sources[key] = True
                else:  # Mark as attempted but failed to prevent infinite loops
                    updated_uploaded_data_sources[key] = False
            
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

        # Trigger background insight regeneration if new data was processed
        if total_processed > 0:
            print(f"[UPLOAD] Triggering background insight regeneration...")
            background_tasks.add_task(regenerate_and_save_insights, request.user_id)

        return {
            "message": f"Successfully processed {total_processed} documents",
            "details": results
        }

    except Exception as e:
        print(f"[UPLOAD] FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-upload-status")
async def reset_upload_status(user_id: str = Body(...), data_sources: List[str] = Body(default=[])):
    """Reset upload status for specific data sources to allow retrying failed uploads"""
    print(f"[RESET UPLOAD] Resetting upload status for user {user_id}")
    print(f"[RESET UPLOAD] Data sources to reset: {data_sources}")
    
    try:
        if not utils.supabase:
            raise HTTPException(status_code=503, detail="Supabase not initialized")
        
        # Get current user settings
        user_settings = utils.supabase.table("user_settings").select("*").eq("user_id", user_id).execute()
        
        if not user_settings.data:
            raise HTTPException(status_code=400, detail="User not found")
        
        uploaded_data_sources = user_settings.data[0].get("uploaded_data_sources", {})
        
        # Reset specified data sources (or all if none specified)
        if not data_sources:
            # Reset all failed uploads (False values) and allow retry
            data_sources_to_reset = [key for key, status in uploaded_data_sources.items() if status is False]
            print(f"[RESET UPLOAD] Auto-detected failed sources: {data_sources_to_reset}")
        else:
            data_sources_to_reset = data_sources
        
        # Remove the specified data sources from uploaded_data_sources
        updated_uploaded_data_sources = uploaded_data_sources.copy()
        for source in data_sources_to_reset:
            if source in updated_uploaded_data_sources:
                del updated_uploaded_data_sources[source]
                print(f"[RESET UPLOAD] Reset upload status for: {source}")
        
        # Update the database
        utils.supabase.table("user_settings").update({
            "uploaded_data_sources": updated_uploaded_data_sources
        }).eq("user_id", user_id).execute()
        
        return {
            "message": f"Reset upload status for {len(data_sources_to_reset)} data sources",
            "reset_sources": data_sources_to_reset,
            "remaining_status": updated_uploaded_data_sources
        }
        
    except Exception as e:
        print(f"[RESET UPLOAD] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upload-status/{user_id}")
async def get_upload_status(user_id: str):
    """Get current upload status for all data sources"""
    print(f"[UPLOAD STATUS] Getting upload status for user {user_id}")
    
    try:
        if not utils.supabase:
            raise HTTPException(status_code=503, detail="Supabase not initialized")
        
        # Get current user settings
        user_settings = utils.supabase.table("user_settings").select("*").eq("user_id", user_id).execute()
        
        if not user_settings.data:
            raise HTTPException(status_code=400, detail="User not found")
        
        settings = user_settings.data[0]
        permissions = settings.get("permissions", {})
        uploaded_data_sources = settings.get("uploaded_data_sources", {})
        
        # Build detailed status
        status_details = {}
        for key, permission_value in permissions.items():
            upload_status = uploaded_data_sources.get(key)
            status_details[key] = {
                "permission_enabled": permission_value,
                "upload_status": upload_status,
                "status_description": (
                    "Successfully uploaded" if upload_status is True
                    else "Upload failed" if upload_status is False
                    else "Not uploaded yet" if upload_status is None and permission_value
                    else "Permission disabled" if not permission_value
                    else "Unknown status"
                )
            }
        
        return {
            "user_id": user_id,
            "permissions": permissions,
            "uploaded_data_sources": uploaded_data_sources,
            "status_details": status_details
        }
        
    except Exception as e:
        print(f"[UPLOAD STATUS] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
