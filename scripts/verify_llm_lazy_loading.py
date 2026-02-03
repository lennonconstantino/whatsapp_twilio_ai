
import sys
import os
import logging
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.getcwd())

# Mock environment variables to avoid loading real .env if not needed
# But the module loads .env, so we let it be.

# We need to mock the actual provider classes to avoid real network calls or dependencies
# We can patch the _PROVIDER_MAP in the module before we trigger any instantiation
import src.modules.ai.infrastructure.llm as llm_module

# Mock the provider classes
MockChatOpenAI = MagicMock()
MockChatGoogle = MagicMock()
MockChatGroq = MagicMock()
MockChatOllama = MagicMock()

# Patch the provider map
llm_module._PROVIDER_MAP = {
    "openai": MockChatOpenAI,
    "google": MockChatGoogle,
    "groq": MockChatGroq,
    "ollama": MockChatOllama,
}

def verify_lazy_loading():
    print("--- Verifying Lazy Loading ---")
    
    factory = llm_module.llm_factory
    models = llm_module.models
    
    # 1. Verify types
    print(f"models type: {type(models)}")
    if not isinstance(models, llm_module.LazyModelDict):
        print("FAIL: models is not LazyModelDict")
        return False
    
    # 2. Verify initial state (empty instances)
    print(f"Initial instances: {len(factory._instances)}")
    if len(factory._instances) != 0:
        print("FAIL: instances should be empty initially")
        return False
        
    # 3. Access a static config model
    key = "openai/gpt-3.5-turbo"
    print(f"Accessing {key}...")
    model = models[key]
    
    if len(factory._instances) != 1:
        print(f"FAIL: Should have 1 instance, got {len(factory._instances)}")
        return False
    
    if key not in factory._instances:
        print(f"FAIL: {key} not in instances")
        return False
        
    print("SUCCESS: Static model lazy loaded")
    
    # 4. Access a dynamic model
    dynamic_key = "openai/gpt-4-turbo-dynamic"
    print(f"Accessing dynamic {dynamic_key}...")
    model_dyn = models[dynamic_key]
    
    if len(factory._instances) != 2:
        print(f"FAIL: Should have 2 instances, got {len(factory._instances)}")
        return False
        
    print("SUCCESS: Dynamic model lazy loaded")
    
    return True

def verify_health_check():
    print("\n--- Verifying Health Check ---")
    factory = llm_module.llm_factory
    
    # Mock get_model to return a mock that responds to invoke
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "pong"
    mock_model.invoke.return_value = mock_response
    
    # Patch get_model on the factory instance for this test
    original_get_model = factory.get_model
    factory.get_model = MagicMock(return_value=mock_model)
    
    try:
        result = factory.check_health("dummy/model")
        print(f"Health check result: {result}")
        
        if result["status"] != "ok":
            print("FAIL: Status should be ok")
            return False
            
        if result["response_preview"] != "pong":
            print("FAIL: response_preview mismatch")
            return False
            
        print("SUCCESS: Health check passed")
        
    finally:
        # Restore
        factory.get_model = original_get_model
        
    return True

if __name__ == "__main__":
    if verify_lazy_loading() and verify_health_check():
        print("\nALL TESTS PASSED")
        sys.exit(0)
    else:
        print("\nTESTS FAILED")
        sys.exit(1)
