import os
import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, HTTPException
from pinecone import Pinecone
from typing import List, Dict, Optional

from models import QueryRequest, QueryResponse, SaveInsightsRequest
import utils
from insights_engine import analyze_documents_for_insights

router = APIRouter()


@router.post("/insights")
async def get_insights(user_id: str, limit: int = 20):
    """Generate proactive insights from user's personal data"""
    try:
        # Initialize services if not already done
        if not utils.embedding_model or not utils.pinecone_index:
            print("[INSIGHTS] Initializing services...")
            utils.initialize_services()
        
        if not utils.embedding_model:
            raise HTTPException(
                status_code=503,
                detail="Embedding model not initialized. Please check configuration."
            )
        
        if not utils.pinecone_index:
            raise HTTPException(
                status_code=503,
                detail="Vector database not available. Please complete setup first."
            )
    
    except Exception as e:
        print(f"[INSIGHTS] Error initializing services: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Service initialization failed: {str(e)}"
        )
    
    # Get user-specific Pinecone index if user_id provided
    index_to_use = utils.pinecone_index
    if user_id and utils.supabase:
        try:
            user_settings = utils.supabase.table("user_settings").select("*").eq("user_id", user_id).execute()
            if user_settings.data:
                pinecone_index_name = user_settings.data[0].get("pinecone_index")
                if pinecone_index_name:
                    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
                    index_to_use = pc.Index(pinecone_index_name)
        except Exception as e:
            print(f"Error getting user index: {e}")
    
    if not index_to_use:
        raise HTTPException(
            status_code=503,
            detail="Vector database not available. Please complete setup first."
        )
    
    try:
        print("[INSIGHTS API] Starting Pinecone query...")
        # Fetch recent documents from Pinecone
        # Use a general query vector to get diverse documents
        query_embedding = utils.embedding_model.encode(
            "important events activities people places work personal life"
        ).tolist()
        
        print("[INSIGHTS API] Querying Pinecone for 20 documents...")
        results = index_to_use.query(
            vector=query_embedding,
            top_k=20,
            include_metadata=True
        )
        print(f"[INSIGHTS API] Pinecone query returned {len(results.get('matches', []))} matches")
        
        # Convert to document format for insights engine
        documents = []
        for match in results['matches']:
            metadata = match.get('metadata', {})
            if metadata.get('text'):
                documents.append({
                    'id': match.get('id'),
                    'metadata': metadata,
                    'score': match.get('score', 0)
                })
        
        # Generate insights
        print(f"[INSIGHTS API] Starting insights generation for {len(documents)} documents...")
        insights = analyze_documents_for_insights(documents, user_id)
        print(f"[INSIGHTS API] Generated {len(insights)} insights")
        
        # LLM insights are already included in the insights from analyze_documents_for_insights
        
        # Apply user feedback weights if available
        if user_id and utils.supabase:
            try:
                feedback_data = utils.supabase.table("user_feedback").select("*").eq("user_id", user_id).execute()
                if feedback_data.data:
                    # Adjust scores based on user feedback
                    feedback_weights = {}
                    for feedback in feedback_data.data:
                        entity = feedback.get('entity')
                        weight = feedback.get('weight', 1.0)
                        feedback_weights[entity] = weight
                    
                    for insight in insights:
                        for entity in insight.get('entities', []):
                            if entity in feedback_weights:
                                insight['significance_score'] *= feedback_weights[entity]
                    
                    # Re-sort by adjusted scores
                    insights.sort(key=lambda x: x['significance_score'], reverse=True)
            except Exception as e:
                print(f"Error applying user feedback: {e}")
        
        return {
            "insights": insights[:limit],
            "total_insights": len(insights),
            "documents_analyzed": len(documents)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/insights/save")
async def save_insights(request: SaveInsightsRequest):
    """Save insights to Supabase for persistent storage across sessions"""
    if not utils.supabase:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        # Upsert insights: delete existing for this user, then insert new ones
        # We use upsert logic per insight_id to avoid duplicates
        saved_count = 0
        for insight in request.insights:
            record = {
                'user_id': request.user_id,
                'insight_id': insight.id,
                'category': insight.category,
                'title': insight.title,
                'description': insight.description,
                'significance_score': insight.significance_score,
                'sources': insight.sources,
                'detected_at': insight.detected_at,
                'time_context': insight.time_context,
                'entities': insight.entities,
                'actionable': insight.actionable,
            }
            # Upsert on conflict (user_id, insight_id)
            result = utils.supabase.table("user_insights").upsert(
                record,
                on_conflict="user_id,insight_id"
            ).execute()
            if result.data:
                saved_count += 1
        
        return {
            "status": "success",
            "message": f"Saved {saved_count} insights",
            "count": saved_count
        }
    
    except Exception as e:
        print(f"[INSIGHTS SAVE] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights/load/{user_id}")
async def load_insights(user_id: str, limit: int = 20):
    """Load persisted insights from Supabase"""
    if not utils.supabase:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        response = utils.supabase.table("user_insights").select("*").eq("user_id", user_id).order("significance_score", desc=True).limit(limit).execute()
        
        insights = []
        for row in response.data:
            insights.append({
                'id': row['insight_id'],
                'category': row['category'],
                'title': row['title'],
                'description': row['description'],
                'significance_score': row['significance_score'],
                'sources': row.get('sources', []),
                'detected_at': row['detected_at'],
                'time_context': row.get('time_context', {}),
                'entities': row.get('entities', []),
                'actionable': row.get('actionable', False),
            })
        
        return {
            "insights": insights,
            "count": len(insights)
        }
    
    except Exception as e:
        print(f"[INSIGHTS LOAD] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/insights/feedback")
async def submit_feedback(user_id: str, insight_id: str, feedback_type: str, entity: Optional[str] = None):
    """Submit user feedback on insights to improve future recommendations"""
    if not utils.supabase:
        raise HTTPException(
            status_code=503,
            detail="Database not available"
        )
    
    try:
        # Calculate weight based on feedback type
        weight_map = {
            'helpful': 1.2,
            'not_helpful': 0.8,
            'important': 1.5,
            'not_important': 0.5,
            'actioned': 1.3,
            'dismissed': 0.7
        }
        
        weight = weight_map.get(feedback_type, 1.0)
        
        # Store feedback
        feedback_data = {
            'user_id': user_id,
            'insight_id': insight_id,
            'feedback_type': feedback_type,
            'entity': entity,
            'weight': weight
        }
        
        utils.supabase.table("user_feedback").insert(feedback_data).execute()
        
        return {"status": "success", "message": "Feedback recorded"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights/stats")
async def get_insights_stats(user_id: str):
    """Get statistics about user's insights and data"""
    if not utils.supabase:
        raise HTTPException(
            status_code=503,
            detail="Database not available"
        )
    
    try:
        # Get document count
        index_to_use = utils.pinecone_index
        if user_id:
            try:
                user_settings = utils.supabase.table("user_settings").select("*").eq("user_id", user_id).execute()
                if user_settings.data:
                    pinecone_index_name = user_settings.data[0].get("pinecone_index")
                    if pinecone_index_name:
                        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
                        index_to_use = pc.Index(pinecone_index_name)
            except:
                pass
        
        # Get stats from Pinecone
        stats = index_to_use.describe_index_stats()
        
        # Get feedback stats
        feedback_stats = utils.supabase.table("user_feedback").select("*").eq("user_id", user_id).execute()
        
        return {
            "total_vectors": stats.get('total_vector_count', 0),
            "dimensions": stats.get('dimension', 0),
            "feedback_count": len(feedback_stats.data) if feedback_stats.data else 0
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
