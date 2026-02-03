import asyncio
import os
import sys
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.di.container import Container
from src.core.config.settings import settings
from src.modules.ai.memory.repositories.vector_memory_repository import VectorMemoryRepository

async def main():
    print(f"Testing Hybrid Search with semantic_top_k={settings.memory.semantic_top_k}")
    
    # Initialize container
    container = Container()
    container.wire(modules=[
        "src.modules.ai.memory.services.hybrid_memory_service",
        "src.modules.ai.memory.repositories.impl.supabase.vector_memory_repository",
        "src.modules.ai.memory.repositories.impl.postgres.vector_memory_repository",
    ])
    
    # Get repository
    try:
        repo = container.vector_memory_repository()
        print(f"Repository type: {type(repo)}")
        
        query = "qual minha bebida favorita"
        print(f"Searching for: '{query}'")
        
        # IDs from previous successful run
        user_id = 'E1NHCGGK10J4PA32R6MB8E6AAC'
        owner_id = '3QKHCGGK10J7TZPS33TKSXTTX6'
        
        retrieval_filter = {
            "owner_id": owner_id,
            "user_id": user_id
        }
        
        print(f"Using filter: {retrieval_filter}")
        
        if settings.memory.enable_hybrid_retrieval:
            print("Hybrid retrieval is ENABLED")
            results = repo.hybrid_search_relevant(
                query,
                limit=settings.memory.semantic_top_k,
                match_threshold=settings.memory.semantic_match_threshold,
                filter=retrieval_filter, # Applying filter this time
                weight_vector=settings.memory.hybrid_weight_vector,
                weight_text=settings.memory.hybrid_weight_text,
                rrf_k=settings.memory.hybrid_rrf_k,
                fts_language=settings.memory.fts_language,
            )
        else:
            print("Hybrid retrieval is DISABLED, using vector_search_relevant")
            results = repo.vector_search_relevant(
                query, 
                limit=settings.memory.semantic_top_k,
                match_threshold=settings.memory.semantic_match_threshold,
                filter=retrieval_filter
            )
            
        print(f"Found {len(results)} results:")
        for i, res in enumerate(results):
            print(f"Result {i+1}:")
            print(f"  Content: {res.get('content')}")
            print(f"  Similarity/Score: {res.get('score', res.get('similarity'))}")
            print(f"  Metadata: {res.get('metadata')}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
