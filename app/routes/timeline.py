"""
Timeline API endpoint for the Personal Knowledge Graph.
Returns chronological fact changes (supersessions) for the user's timeline view.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import utils

router = APIRouter()


@router.get("/timeline")
async def get_timeline(
    user_id: str,
    category: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200)
):
    """Get the user's personal timeline — fact changes ordered by source timestamp."""
    if not utils.supabase:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        query = (
            utils.supabase.table("fact_changes")
            .select("*")
            .eq("user_id", user_id)
            .order("source_timestamp", desc=True)
            .limit(limit)
        )

        if category:
            query = query.eq("entity_category", category)

        result = query.execute()
        return {"timeline": result.data or []}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeline/categories")
async def get_timeline_categories(user_id: str):
    """Get the list of entity categories that have timeline events."""
    if not utils.supabase:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        result = (
            utils.supabase.table("fact_changes")
            .select("entity_category")
            .eq("user_id", user_id)
            .execute()
        )

        categories = sorted({row["entity_category"] for row in (result.data or []) if row.get("entity_category")})
        return {"categories": categories}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/facts/current")
async def get_current_facts(user_id: str, category: Optional[str] = None):
    """Get the user's current (non-superseded) facts."""
    if not utils.supabase:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        query = (
            utils.supabase.table("facts")
            .select("*")
            .eq("user_id", user_id)
            .eq("is_current", True)
            .order("entity_category")
            .order("entity_key")
        )

        if category:
            query = query.eq("entity_category", category)

        result = query.execute()
        return {"facts": result.data or []}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
