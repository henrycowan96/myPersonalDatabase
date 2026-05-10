"""
Enhanced insights engine that feeds from fact_changes instead of raw documents.
Phase B/C integration: generates insights from validated fact transitions.
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, HTTPException
import utils

router = APIRouter()


async def get_feature_flag(user_id: str, flag_name: str) -> Dict:
    """Get feature flag configuration for a user"""
    if not utils.supabase:
        return {"is_enabled": False, "config": {}}
    
    try:
        result = utils.supabase.table("feature_flags").select("*").eq("user_id", user_id).eq("flag_name", flag_name).execute()
        if result.data:
            return {
                "is_enabled": result.data[0]["is_enabled"],
                "config": result.data[0].get("config", {})
            }
        else:
            return {"is_enabled": False, "config": {}}
    except Exception as e:
        print(f"[INSIGHTS_V2] Error getting feature flag: {e}")
        return {"is_enabled": False, "config": {}}


async def generate_insights_from_fact_changes(user_id: str, days_back: int = 30) -> List[Dict]:
    """Generate insight cards from recent fact_changes"""
    if not utils.supabase:
        return []
    
    try:
        # Get recent fact changes
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        changes_result = utils.supabase.table("fact_changes").select(
            "*", 
            "old_fact!inner(*)", 
            "new_fact!inner(*)"
        ).eq("user_id", user_id).gte("source_timestamp", cutoff_date.isoformat()).order("source_timestamp", desc=True).execute()
        
        if not changes_result.data:
            return []
        
        insights = []
        
        for change in changes_result.data:
            # Skip if we already created an insight for this change
            existing_insight = utils.supabase.table("user_insights").select("*").eq("user_id", user_id).eq("fact_change_id", change["id"]).execute()
            if existing_insight.data:
                continue
            
            # Create insight from fact change
            insight = create_insight_from_fact_change(change, user_id)
            if insight:
                insights.append(insight)
        
        return insights
        
    except Exception as e:
        print(f"[INSIGHTS_V2] Error generating insights from fact changes: {e}")
        return []


def create_insight_from_fact_change(change: Dict, user_id: str) -> Optional[Dict]:
    """Create an insight card from a fact change"""
    try:
        entity_category = change["entity_category"]
        entity_key = change["entity_key"]
        old_value = change.get("old_value")
        new_value = change["new_value"]
        source_timestamp = change["source_timestamp"]
        confidence = change["confidence"]
        detection_reason = change["detection_reason"]
        is_reversion = change.get("is_reversion", False)
        
        # Skip low-confidence changes
        if confidence < 0.7:
            return None
        
        # Create title and description based on change type
        if is_reversion:
            title = f"Reverted: {entity_key.replace('_', ' ').title()}"
            description = f"Reverted {entity_key} from '{new_value}' back to '{old_value}'. {detection_reason}"
            category = "interesting"
        elif old_value:
            title = f"Changed: {entity_key.replace('_', ' ').title()}"
            description = f"{entity_key.replace('_', ' ').title()} changed from '{old_value}' to '{new_value}'. {detection_reason}"
            category = "milestone" if entity_category in ["work", "relationships", "location"] else "interesting"
        else:
            title = f"Added: {entity_key.replace('_', ' ').title()}"
            description = f"New {entity_key.replace('_', ' ').title()}: '{new_value}'. {detection_reason}"
            category = "milestone" if entity_category in ["work", "relationships", "location"] else "interesting"
        
        # Calculate significance based on category and confidence
        significance_map = {"milestone": 0.9, "interesting": 0.7, "urgent": 1.0}
        significance_score = significance_map.get(category, 0.6) * confidence
        
        return {
            "id": f"fact_change_{change['id']}",
            "category": category,
            "title": title,
            "description": description,
            "significance_score": significance_score,
            "sources": [],  # Fact changes are self-contained
            "detected_at": change["detected_at"],
            "time_context": {
                "source_timestamp": source_timestamp,
                "fact_change_id": change["id"],
                "entity_category": entity_category,
                "confidence": confidence
            },
            "entities": [entity_key, new_value],
            "actionable": entity_category == "work" and "job" in entity_key.lower(),
            "fact_change_id": change["id"]  # Link back to prevent duplicates
        }
        
    except Exception as e:
        print(f"[INSIGHTS_V2] Error creating insight from fact change: {e}")
        return None


async def generate_insights_from_current_facts(user_id: str, limit: int = 10) -> List[Dict]:
    """Generate 'Recently Confirmed Facts' insights from current facts"""
    if not utils.supabase:
        return []
    
    try:
        # Get most recently confirmed current facts
        facts_result = utils.supabase.table("facts").select(
            "*"
        ).eq("user_id", user_id).eq("is_current", True).order("last_confirmed_at", desc=True).limit(limit).execute()
        
        if not facts_result.data:
            return []
        
        insights = []
        
        for fact in facts_result.data:
            insight = {
                "id": f"current_fact_{fact['id']}",
                "category": "interesting",
                "title": f"Current: {fact['entity_key'].replace('_', ' ').title()}",
                "description": f"{fact['value']} (confirmed {fact['last_confirmed_at'][:10]})",
                "significance_score": 0.6,  # Lower significance for current facts
                "sources": [],
                "detected_at": fact["last_confirmed_at"],
                "time_context": {
                    "fact_id": fact["id"],
                    "entity_category": fact["entity_category"],
                    "confidence": fact["confidence"]
                },
                "entities": [fact["entity_key"], fact["value"]],
                "actionable": False
            }
            insights.append(insight)
        
        return insights
        
    except Exception as e:
        print(f"[INSIGHTS_V2] Error generating current facts insights: {e}")
        return []


@router.post("/insights/v2")
async def get_insights_v2(user_id: str, limit: int = 20, days_back: int = 30):
    """Enhanced insights endpoint that uses fact_changes as primary source"""
    try:
        # Check feature flag for fact-based detection
        flag = await get_feature_flag(user_id, "fact_based_detection")
        
        insights = []
        
        if flag["is_enabled"] or flag["config"].get("parallel_mode", False):
            # Generate insights from fact changes
            fact_insights = await generate_insights_from_fact_changes(user_id, days_back)
            insights.extend(fact_insights)
            
            # Add recently confirmed facts
            current_facts_insights = await generate_insights_from_current_facts(user_id, 8)
            insights.extend(current_facts_insights)
        
        if flag["config"].get("parallel_mode", False) or not flag["is_enabled"]:
            # Fall back to original insights engine for comparison or if flag is off
            try:
                from insights_engine import analyze_documents_for_insights
                import pinecone
                
                # Get some recent documents for original analysis
                if utils.pinecone_index:
                    query_embedding = utils.embedding_model.encode(
                        "important events activities people places work personal life"
                    ).tolist()
                    
                    results = utils.pinecone_index.query(
                        vector=query_embedding,
                        top_k=10,
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
                    
                    original_insights = analyze_documents_for_insights(documents, user_id)
                    
                    # Mark original insights with different prefix to distinguish
                    for insight in original_insights:
                        insight["id"] = f"original_{insight['id']}"
                    
                    insights.extend(original_insights)
                    
            except Exception as e:
                print(f"[INSIGHTS_V2] Error in original insights fallback: {e}")
        
        # Sort by significance and limit
        insights.sort(key=lambda x: x.get('significance_score', 0), reverse=True)
        
        return {
            "insights": insights[:limit],
            "total_insights": len(insights),
            "feature_flag": flag,
            "fact_based_count": len([i for i in insights if i.get('id', '').startswith(('fact_change_', 'current_fact_'))]),
            "original_count": len([i for i in insights if i.get('id', '').startswith('original_')])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/insights/v2/save")
async def save_insights_v2(request: dict):
    """Save insights with fact_change_id deduplication"""
    if not utils.supabase:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        user_id = request.get("user_id")
        insights = request.get("insights", [])
        
        saved_count = 0
        for insight in insights:
            record = {
                'user_id': user_id,
                'insight_id': insight['id'],
                'category': insight['category'],
                'title': insight['title'],
                'description': insight['description'],
                'significance_score': insight['significance_score'],
                'sources': insight.get('sources', []),
                'detected_at': insight['detected_at'],
                'time_context': insight.get('time_context', {}),
                'entities': insight.get('entities', []),
                'actionable': insight.get('actionable', False),
                'fact_change_id': insight.get('fact_change_id')  # Can be None for original insights
            }
            
            # Upsert will handle the unique constraint on fact_change_id
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
        print(f"[INSIGHTS_V2 SAVE] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/insights/v2/compare")
async def compare_detection_methods(user_id: str, days_back: int = 30):
    """Compare fact-based vs regex detection output for the same time window"""
    try:
        # Get fact-based insights
        fact_insights = await generate_insights_from_fact_changes(user_id, days_back)
        
        # Get original insights for same period (simplified)
        original_insights = []
        try:
            from insights_engine import analyze_documents_for_insights
            # This would need to be enhanced to filter by date range
            # For now, just get recent insights
            if utils.pinecone_index:
                query_embedding = utils.embedding_model.encode(
                    "important events activities people places work personal life"
                ).tolist()
                
                results = utils.pinecone_index.query(
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
                
                original_insights = analyze_documents_for_insights(documents, user_id)
        except Exception as e:
            print(f"[INSIGHTS_V2] Error in original insights for comparison: {e}")
        
        # Categorize and compare
        fact_categories = {}
        for insight in fact_insights:
            cat = insight['category']
            fact_categories[cat] = fact_categories.get(cat, 0) + 1
        
        original_categories = {}
        for insight in original_insights:
            cat = insight['category']
            original_categories[cat] = original_categories.get(cat, 0) + 1
        
        return {
            "fact_based": {
                "total": len(fact_insights),
                "categories": fact_categories,
                "sample": fact_insights[:3]
            },
            "original": {
                "total": len(original_insights),
                "categories": original_categories,
                "sample": original_insights[:3]
            },
            "comparison": {
                "fact_better_coverage": set(fact_categories.keys()) - set(original_categories.keys()),
                "original_better_coverage": set(original_categories.keys()) - set(fact_categories.keys()),
                "overlap": set(fact_categories.keys()) & set(original_categories.keys())
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
