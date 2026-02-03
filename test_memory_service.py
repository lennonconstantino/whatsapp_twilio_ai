import asyncio
import os
import sys
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.di.container import Container
from src.core.config.settings import settings
from src.core.utils.logging import get_logger

# Configure logging to show info
import logging
logging.basicConfig(level=logging.INFO)

async def main():
    print("Testing HybridMemoryService.get_context")
    
    # Initialize container
    container = Container()
    # Wire relevant modules
    container.wire(modules=[
        __name__, # Current module
        "src.modules.ai.memory.services.hybrid_memory_service",
    ])
    
    # Get service
    try:
        memory_service = container.hybrid_memory_service()
        print(f"Service type: {type(memory_service)}")
        
        query = "qual minha bebida favorita"
        
        # IDs from previous successful run
        user_id = 'E1NHCGGK10J4PA32R6MB8E6AAC'
        owner_id = '3QKHCGGK10J7TZPS33TKSXTTX6'
        user_phone = "whatsapp:+5511991490733" # Example phone from logs
        
        # Construct session_id as RoutingAgent does
        session_id = f"{owner_id}:{user_phone}"
        print(f"Session ID: {session_id}")
        
        print(f"Calling get_context with:")
        print(f"  query='{query}'")
        print(f"  owner_id='{owner_id}'")
        print(f"  user_id=None (Simulating missing user)")
        
        context = memory_service.get_context(
            session_id=session_id,
            limit=10,
            query=query,
            owner_id=owner_id,
            user_id=None # Simulating missing user
        )
        
        print(f"Found {len(context)} messages in context")
        for msg in context:
            role = msg.get('role')
            content = msg.get('content', '')
            print(f"[{role}] {content[:100]}...")
            if role == 'system' and 'Relevant Information' in content:
                print("SUCCESS: Semantic information found in context!")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
