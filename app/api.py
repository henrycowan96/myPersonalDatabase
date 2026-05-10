import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from routes import query, chat, user, auth, ingestion, upload, apple_ingestion, google_ingestion, spotify_ingestion, insights, llm_thoughts, chat_context, cleanup, timeline
import utils

# Create FastAPI app with lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize services on startup
    utils.initialize_services()
    yield
    # Cleanup on shutdown if needed

app = FastAPI(title="Personal Database API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(query.router)
app.include_router(chat.router)
app.include_router(user.router)
app.include_router(auth.router)
app.include_router(ingestion.router)
app.include_router(apple_ingestion.router)
app.include_router(google_ingestion.router)
app.include_router(spotify_ingestion.router)
app.include_router(upload.router)
app.include_router(insights.router)
app.include_router(llm_thoughts.router)
app.include_router(chat_context.router)
app.include_router(cleanup.router)
app.include_router(timeline.router)

@app.get("/")
async def root():
    return {"message": "Personal Database API is running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "pinecone_connected": utils.pinecone_index is not None,
        "embedding_model_loaded": utils.embedding_model is not None,
        "openrouter_loaded": utils.llm is not None,
        "supabase_connected": utils.supabase is not None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
