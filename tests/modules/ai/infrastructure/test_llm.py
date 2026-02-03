
import pytest
from unittest.mock import MagicMock, patch, ANY
from src.modules.ai.infrastructure.llm import LLMFactory, LazyModelDict, MODEL_CONFIGS

@pytest.fixture
def factory():
    """Create a fresh LLMFactory instance for each test."""
    return LLMFactory()

@pytest.fixture
def lazy_models(factory):
    """Create a LazyModelDict linked to the fresh factory."""
    return LazyModelDict(factory)

class TestLLMFactory:
    def test_initial_state(self, factory):
        """Test that the factory starts with empty instances but populated configs."""
        assert len(factory._instances) == 0
        # Configs should be populated from MODEL_CONFIGS
        assert len(factory._configs) >= len(MODEL_CONFIGS)

    def test_get_model_static_config(self, factory):
        """Test getting a model that is statically configured."""
        # Find an openai config to test
        openai_config = next(c for c in MODEL_CONFIGS if c["provider"] == "openai")
        key = f"{openai_config['provider']}/{openai_config['model_name']}"
        
        mock_chat_cls = MagicMock()
        
        # Patch the provider map specifically
        with patch.dict("src.modules.ai.infrastructure.llm._PROVIDER_MAP", {"openai": mock_chat_cls}):
            # Should create instance
            model = factory.get_model(key)
            
            assert model is not None
            assert key in factory._instances
            mock_chat_cls.assert_called_once()
            
            # Second call should return cached instance
            model2 = factory.get_model(key)
            assert model2 is model
            mock_chat_cls.assert_called_once() # Still called only once

    def test_get_model_dynamic_config(self, factory):
        """Test getting a model that is NOT statically configured (dynamic)."""
        key = "openai/gpt-4-turbo-custom"
        mock_chat_cls = MagicMock()
        
        with patch.dict("src.modules.ai.infrastructure.llm._PROVIDER_MAP", {"openai": mock_chat_cls}):
            # Should create instance via inference
            model = factory.get_model(key)
            
            assert model is not None
            assert key in factory._instances
            
            # Verify call args
            _, kwargs = mock_chat_cls.call_args
            assert kwargs["model"] == "gpt-4-turbo-custom"
            assert kwargs["temperature"] == 0 # Default

    def test_get_model_invalid_provider(self, factory):
        """Test that invalid provider raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported provider"):
            factory.get_model("invalid_provider/model-name")

    def test_get_model_invalid_format(self, factory):
        """Test that invalid key format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid model key format"):
            factory.get_model("invalid-format")

    def test_check_health_success(self, factory):
        """Test health check success."""
        key = "openai/test-model"
        
        # Mock get_model and the model instance
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "pong"
        mock_model.invoke.return_value = mock_response
        
        with patch.object(factory, 'get_model', return_value=mock_model):
            result = factory.check_health(key)
            
            assert result["status"] == "ok"
            assert result["response_preview"] == "pong"
            assert result["error"] is None
            assert result["latency_ms"] >= 0

    def test_check_health_failure(self, factory):
        """Test health check failure."""
        key = "openai/fail-model"
        
        with patch.object(factory, 'get_model', side_effect=Exception("Connection failed")):
            result = factory.check_health(key)
            
            assert result["status"] == "error"
            assert "Connection failed" in result["error"]

class TestLazyModelDict:
    def test_getitem_triggers_factory(self, factory, lazy_models):
        """Test that accessing via [] triggers factory.get_model."""
        with patch.object(factory, 'get_model') as mock_get_model:
            mock_get_model.return_value = "mock_instance"
            
            instance = lazy_models["test/model"]
            
            assert instance == "mock_instance"
            mock_get_model.assert_called_with("test/model")

    def test_get_safe_access(self, factory, lazy_models):
        """Test .get() method behavior."""
        with patch.object(factory, 'get_model') as mock_get_model:
            # Success case
            mock_get_model.return_value = "mock_instance"
            assert lazy_models.get("test/model") == "mock_instance"
            
            # Failure case
            mock_get_model.side_effect = Exception("Failed")
            assert lazy_models.get("test/fail") is None
            assert lazy_models.get("test/fail", "default") == "default"

    def test_dict_methods(self, factory, lazy_models):
        """Test compatibility with dict methods (keys, values, etc)."""
        # Ensure factory has some configs
        assert len(lazy_models.keys()) > 0
        assert "openai/gpt-3.5-turbo" in lazy_models
        
        # Test iteration
        keys = list(lazy_models)
        assert len(keys) == len(factory._configs)
