import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
from langchain_openai import ChatOpenAI

load_dotenv()

# Configuration
PINECONE_INDEX_NAME = "personal-database"

def load_vector_store():
    """Load the Pinecone index"""
    if not os.getenv("PINECONE_API_KEY"):
        raise ValueError("PINECONE_API_KEY not found in environment variables")
    
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index(PINECONE_INDEX_NAME)
    
    # Initialize embedding model
    embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    
    print(f"Loaded Pinecone index '{PINECONE_INDEX_NAME}'")
    return index, embedding_model

def query(question, index, embedding_model, llm=None):
    """Query the Pinecone index with a question"""
    # Generate query embedding
    query_embedding = embedding_model.encode(question).tolist()
    
    # Search Pinecone
    results = index.query(
        vector=query_embedding,
        top_k=4,
        include_metadata=True
    )
    
    # Extract sources and context
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
    
    # Generate answer using LLM if available
    if llm and context_parts:
        context = "\n\n".join(context_parts)
        prompt = f"""You are a helpful assistant that answers questions based on the provided context.

IMPORTANT: All information in the context below is from the user's personal perspective. When interpreting events, actions, communications, or any data, assume it reflects the user's own experiences, activities, and information. For example:
- "sent an email" means the user sent it
- "meeting with X" means the user attended the meeting
- "purchased Y" means the user made the purchase
- Any references to "I", "my", or personal activities refer to the user

Use the following pieces of context to answer the question at the end. If you don't know the answer based on the context, just say that you don't know, don't try to make up an answer.

Context: {context}

Question: {question}

Answer:"""
        
        answer = llm.invoke(prompt).content
    else:
        answer = "No LLM configured. Here are the relevant document excerpts:\n\n" + "\n\n".join(context_parts)
    
    return {
        "answer": answer,
        "sources": sources
    }

def main():
    print("Loading Pinecone index...")
    index, embedding_model = load_vector_store()
    
    # Initialize OpenRouter LLM
    try:
        llm = ChatOpenAI(
            model="openrouter/free",
            temperature=0.7,
            openai_api_key=os.getenv("OPEN_ROUTER_API_KEY"),
            openai_api_base="https://openrouter.ai/api/v1"
        )
        print("OpenRouter LLM initialized successfully")
    except Exception as e:
        print(f"Warning: Could not initialize OpenRouter LLM: {e}")
        print("Make sure OPEN_ROUTER_API_KEY is set in .env file")
        llm = None
    
    print("\nQuery system ready! Type 'quit' to exit.\n")
    
    while True:
        question = input("Your question: ").strip()
        
        if question.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        
        if not question:
            continue
        
        print("\nSearching...")
        result = query(question, index, embedding_model, llm)
        
        print(f"\nAnswer: {result['answer']}\n")
        
        print("Sources:")
        for i, source in enumerate(result['sources'], 1):
            print(f"\n{i}. {source['content']}")
            print(f"   Metadata: {source['metadata']}")
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    main()
