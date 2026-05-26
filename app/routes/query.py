import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, HTTPException
from pinecone import Pinecone

from models import QueryRequest, QueryResponse, RelationshipQueryRequest, RelationshipQueryResponse
import utils

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Query the document database with a question"""
    if not utils.embedding_model:
        raise HTTPException(
            status_code=503,
            detail="Services not initialized. Please check configuration."
        )

    # Get user-specific Pinecone index if user_id provided
    index_to_use = utils.pinecone_index
    if request.user_id and utils.supabase:
        try:
            user_settings = utils.supabase.table("user_settings").select("*").eq("user_id", request.user_id).execute()
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
        # Generate query embedding
        query_embedding = utils.embedding_model.encode(request.question).tolist()

        # Search Pinecone with higher top_k for better retrieval
        results = index_to_use.query(
            vector=query_embedding,
            top_k=10,
            include_metadata=True
        )

        # Filter by score (relevance threshold) - lowered to 0.5 to avoid filtering too aggressively
        filtered_matches = [match for match in results['matches'] if match.get('score', 0) >= 0.5]

        # If no matches pass the filter, use the top matches anyway
        if not filtered_matches:
            filtered_matches = results['matches'][:5]

        # Rerank using cross-encoder if available
        if utils.reranker and len(filtered_matches) > 1:
            pairs = [[request.question, match.get('metadata', {}).get('text', '')] for match in filtered_matches]
            scores = utils.reranker.predict(pairs)
            for match, score in zip(filtered_matches, scores):
                match['rerank_score'] = score
            filtered_matches.sort(key=lambda x: x['rerank_score'], reverse=True)

        # Take top 5 results after filtering/reranking
        top_matches = filtered_matches[:5]

        # Extract sources with enhanced metadata
        sources = []
        context_parts = []
        for match in top_matches:
            metadata = match.get('metadata', {})
            content = metadata.get('text', '')
            if content:
                source_info = {
                    "content": content[:200] + "..." if len(content) > 200 else content,
                    "metadata": {
                        "filename": metadata.get('filename', 'Unknown'),
                        "source_type": metadata.get('source_type', 'document'),
                        "date": metadata.get('date', 'Unknown'),
                        "relevance_score": float(match.get('score', 0)),
                        "rerank_score": float(match.get('rerank_score', 0)) if match.get('rerank_score') is not None else None
                    }
                }
                sources.append(source_info)
                context_parts.append(content)

        # Context window management - truncate if too long
        max_context_length = 4000
        context = "\n\n".join(context_parts)
        if len(context) > max_context_length:
            # Truncate by keeping most relevant chunks first
            truncated_context = []
            current_length = 0
            for part in context_parts:
                if current_length + len(part) <= max_context_length:
                    truncated_context.append(part)
                    current_length += len(part)
                else:
                    break
            context = "\n\n".join(truncated_context)

        # Process conversation history with summarization
        conversation_context = ""
        if request.conversation_history:
            summary_result = utils.summarize_conversation(request.conversation_history)
            
            if summary_result["summary"]:
                conversation_context = f"\n\nCONVERSATION SUMMARY (earlier context):\n{summary_result['summary']}\n"
            
            if summary_result["recent_turns"]:
                recent_conversation = "\n".join([
                    f"User: {turn.get('query', '')}\nAssistant: {turn.get('answer', '')}"
                    for turn in summary_result["recent_turns"]
                ])
                conversation_context += f"\nRECENT CONVERSATION:\n{recent_conversation}\n"

        # Build persona snapshot from structured facts
        persona_block = ""
        notes_count = 0
        if request.user_id and utils.supabase:
            try:
                # Get facts for persona
                facts_res = utils.supabase.table("facts").select("entity_key,value,last_confirmed_at").eq("user_id", request.user_id).eq("is_current", True).order("entity_category").order("entity_key").execute()
                if facts_res.data:
                    lines = []
                    for f in facts_res.data:
                        ts_str = f.get("last_confirmed_at", "")
                        if isinstance(ts_str, str) and len(ts_str) >= 7:
                            ts_display = ts_str[:7]
                        else:
                            ts_display = "unknown"
                        lines.append(f"- {f['entity_key']}: {f['value']} (as of {ts_display})")
                    persona_block = "Current known facts about this person:\n" + "\n".join(lines) + "\n\n"
                
                # Get count of Apple Notes ingested
                notes_res = utils.supabase.table("ingested_chunks").select("id", count="exact").eq("user_id", request.user_id).eq("source_type", "apple_notes").eq("is_deleted", False).execute()
                notes_count = notes_res.count or 0
            except Exception as e:
                print(f"[QUERY] Error fetching persona snapshot: {e}")

        # Determine routing decision
        routing_decision = "knowledge" if context_parts else "general"
        routing_reason = "Found relevant documents in knowledge base" if context_parts else "No relevant documents found, using general conversation"

        # Generate answer using LLM with improved prompt
        if utils.llm and context_parts:
            # Check if this is the first message in a new session (no conversation history)
            is_first_message = not request.conversation_history or len(request.conversation_history) == 0
            
            prompt = f"""You are a precise, factual assistant that answers questions about the user based ONLY on the provided context.

IMPORTANT: All information in the context below is from the user's personal perspective. When interpreting events, actions, communications, or any data, assume it reflects the user's own experiences, activities, and information. For example:
- "sent an email" means the user sent it
- "meeting with X" means the user attended the meeting
- "purchased Y" means the user made the purchase
- Any references to "I", "my", or personal activities in the context refer to the user

INSTRUCTIONS:
- Answer the question using the given context
- Interpret all context as the user's personal information and experiences
- Always refer to the user as "you" or "your" - never as "I" or "my"
- If the answer is not in the context, state "I don't have enough information to answer this"
- Be specific and cite relevant details
- Do not make up or infer information beyond what's provided
- Keep answers concise and well-structured
- Use conversation history to understand context, but base factual answers on the provided document context
- Always consider the persona facts when answering to provide contextually relevant responses
{conversation_context}

{persona_block}CONTEXT (from {len(context_parts)} sources):
{context}

QUESTION: {request.question}

ANSWER:"""

            answer = utils.llm.invoke(prompt).content
            
            # Add greeting for first message
            if is_first_message:
                greeting = f"I've read {notes_count} of your Apple Notes and am ready to discuss them. "
                answer = greeting + answer
        else:
            if not utils.llm:
                print(f"[QUERY] LLM not initialized")
            if not context_parts:
                print(f"[QUERY] No context parts found. Matches: {len(results.get('matches', []))}, Filtered: {len(filtered_matches)}")
            answer = "No LLM configured or no relevant documents found. Here are the relevant document excerpts:\n\n" + "\n\n".join(context_parts)

        return QueryResponse(answer=answer, sources=sources, routing_decision=routing_decision, routing_reason=routing_reason)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query-relationships", response_model=RelationshipQueryResponse)
async def query_by_relationships(request: RelationshipQueryRequest):
    """Query documents by relationships (entity, topic, source) with optional semantic search"""
    if not utils.embedding_model:
        raise HTTPException(
            status_code=503,
            detail="Services not initialized. Please check configuration."
        )
    
    # Get user-specific Pinecone index if user_id provided
    index_to_use = utils.pinecone_index
    if request.user_id and utils.supabase:
        try:
            user_settings = utils.supabase.table("user_settings").select("*").eq("user_id", request.user_id).execute()
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
        # Build metadata filter
        filter_dict = {}
        filters_applied = {}
        
        if request.entity_id:
            filter_dict['entity_ids'] = {'$in': [request.entity_id]}
            filters_applied['entity_id'] = request.entity_id
        
        if request.topic:
            filter_dict['topics'] = {'$in': [request.topic]}
            filters_applied['topic'] = request.topic
        
        if request.source:
            filter_dict['source'] = request.source
            filters_applied['source'] = request.source
        
        # If no filters provided, return error
        if not filter_dict and not request.question:
            raise HTTPException(
                status_code=400,
                detail="Must provide at least one filter (entity_id, topic, source) or a question"
            )
        
        # Search with or without semantic query
        if request.question:
            query_embedding = utils.embedding_model.encode(request.question).tolist()
            results = index_to_use.query(
                vector=query_embedding,
                top_k=10,
                include_metadata=True,
                filter=filter_dict if filter_dict else None
            )
        else:
            # Metadata-only search (no vector)
            results = index_to_use.query(
                vector=[0] * 384,  # Dummy vector for metadata-only search
                top_k=20,
                include_metadata=True,
                filter=filter_dict
            )
        
        # Extract sources
        sources = []
        context_parts = []
        for match in results['matches']:
            metadata = match.get('metadata', {})
            content = metadata.get('text', '')
            if content:
                sources.append({
                    "content": content[:200] + "..." if len(content) > 200 else content,
                    "metadata": metadata
                })
                context_parts.append(content)
        
        # Process conversation history with summarization
        conversation_context = ""
        if request.conversation_history:
            summary_result = utils.summarize_conversation(request.conversation_history)
            
            if summary_result["summary"]:
                conversation_context = f"\n\nCONVERSATION SUMMARY (earlier context):\n{summary_result['summary']}\n"
            
            if summary_result["recent_turns"]:
                recent_conversation = "\n".join([
                    f"User: {turn.get('query', '')}\nAssistant: {turn.get('answer', '')}"
                    for turn in summary_result["recent_turns"]
                ])
                conversation_context += f"\nRECENT CONVERSATION:\n{recent_conversation}\n"

        # Build persona snapshot from structured facts
        persona_block = ""
        notes_count = 0
        if request.user_id and utils.supabase:
            try:
                # Get facts for persona
                facts_res = utils.supabase.table("facts").select("entity_key,value,last_confirmed_at").eq("user_id", request.user_id).eq("is_current", True).order("entity_category").order("entity_key").execute()
                if facts_res.data:
                    lines = []
                    for f in facts_res.data:
                        ts_str = f.get("last_confirmed_at", "")
                        if isinstance(ts_str, str) and len(ts_str) >= 7:
                            ts_display = ts_str[:7]
                        else:
                            ts_display = "unknown"
                        lines.append(f"- {f['entity_key']}: {f['value']} (as of {ts_display})")
                    persona_block = "Current known facts about this person:\n" + "\n".join(lines) + "\n\n"
                
                # Get count of Apple Notes ingested
                notes_res = utils.supabase.table("ingested_chunks").select("id", count="exact").eq("user_id", request.user_id).eq("source_type", "apple_notes").eq("is_deleted", False).execute()
                notes_count = notes_res.count or 0
            except Exception as e:
                print(f"[QUERY-REL] Error fetching persona snapshot: {e}")

        # Generate answer using LLM if question provided
        if request.question and utils.llm and context_parts:
            context = "\n\n".join(context_parts)
            
            # Check if this is the first message in a new session (no conversation history)
            is_first_message = not request.conversation_history or len(request.conversation_history) == 0
            
            prompt = f"""You are a helpful assistant that answers questions about the user based on the provided context.

IMPORTANT: All information in the context below is from the user's personal perspective. When interpreting events, actions, communications, or any data, assume it reflects the user's own experiences, activities, and information. For example:
- "sent an email" means the user sent it
- "meeting with X" means the user attended the meeting
- "purchased Y" means the user made the purchase
- Any references to "I", "my", or personal activities in the context refer to the user

Use the following pieces of context to answer the question at the end. If you don't know the answer based on the context, just say that you don't know, don't try to make up an answer.
- Always refer to the user as "you" or "your" - never as "I" or "my"
- Always consider the persona facts when answering to provide contextually relevant responses
{conversation_context}

{persona_block}Context: {context}

Question: {request.question}

Answer:"""
            
            answer = utils.llm.invoke(prompt).content
            
            # Add greeting for first message
            if is_first_message:
                greeting = f"I've read {notes_count} of your Apple Notes and am ready to discuss them. "
                answer = greeting + answer
        elif context_parts:
            answer = f"Found {len(sources)} related documents based on filters: {filters_applied}"
        else:
            answer = f"No documents found matching filters: {filters_applied}"
        
        return RelationshipQueryResponse(
            answer=answer,
            sources=sources,
            filters_applied=filters_applied
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
