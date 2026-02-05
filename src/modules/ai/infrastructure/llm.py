from typing import Any, Dict, Optional, List
import os
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from src.core.utils.logging import get_logger
from src.core.config import settings

logger = get_logger(__name__)

# Provider mapping
_PROVIDER_MAP = {
    "openai": ChatOpenAI,
    "google": ChatGoogleGenerativeAI,
    "groq": ChatGroq,
    "ollama": ChatOllama,
}

# Static configuration for known models
MODEL_CONFIGS = [
    {
        "provider": "ollama",
        "model_name": "gpt-oss:20b",
        "temperature": 0,
        "validate_model_on_init": False,
    },
    {
        "provider": "groq",
        "model_name": "deepseek-r1-distill-llama-70b",
        "temperature": 0,
        "max_tokens": 1000,
        "top_p": 0.1,
    },
    {
        "provider": "groq",
        "model_name": "llama3-8b-8192",
        "temperature": 0,
        "max_tokens": 500,
        "top_p": 0.1,
    },
    {
        "provider": "google",
        "model_name": "gemini-2.5-flash",
        "temperature": 0,
    },
    {
        "provider": "openai",
        "model_name": "gpt-3.5-turbo",
    },
    {
        "provider": "openai",
        "model_name": "o4-mini-2025-04-16",
    },
    {
        "provider": "openai",
        "model_name": "gpt-4o-2024-08-06",
    },
]

class LLMFactory:
    """
    Factory for creating and managing LLM instances with lazy loading.
    """

    def __init__(self):
        self._instances: Dict[str, BaseChatModel] = {}
        self._configs: Dict[str, Dict[str, Any]] = {}
        
        # Pre-populate configs from static list
        for config in MODEL_CONFIGS:
            key = f"{config['provider']}/{config['model_name']}"
            self._configs[key] = config

    def get_model(self, key: str) -> BaseChatModel:
        """
        Get an LLM instance by key (provider/model_name).
        Creates it if it doesn't exist.
        """
        if key in self._instances:
            return self._instances[key]

        # Check if we have config for this key
        config = self._configs.get(key)
        
        if not config:
            # Try to infer config from key if it follows provider/model format
            try:
                provider, model_name = key.split("/", 1)
                logger.info(f"Implicit configuration for model: {key}")
                config = {
                    "provider": provider,
                    "model_name": model_name,
                    "temperature": 0
                }
            except ValueError:
                raise ValueError(f"Invalid model key format or unknown model: {key}")

        try:
            instance = self._create_instance(config)
            self._instances[key] = instance
            logger.info(f"Lazy loaded LLM: {key}")
            return instance
        except Exception as e:
            logger.error(f"Failed to lazy load LLM {key}: {e}")
            raise e

    def _create_instance(self, config: Dict[str, Any]) -> BaseChatModel:
        """Internal method to create an LLM instance."""
        provider = config.get("provider")
        model_name = config.get("model_name")
        temperature = config.get("temperature")
        
        # Extract extra params
        extra_params = {k: v for k, v in config.items() 
                       if k not in ["provider", "model_name", "temperature"]}

        if provider not in _PROVIDER_MAP:
            raise ValueError(
                f"Unsupported provider: {provider}. Supported: {list(_PROVIDER_MAP.keys())}"
            )

        model_class = _PROVIDER_MAP[provider]
        params = {"model": model_name}

        if temperature is not None:
            params["temperature"] = temperature

        if provider == "google":
            from langchain_google_genai import HarmBlockThreshold, HarmCategory
            safety_settings = {
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            }
            params["safety_settings"] = safety_settings

        # Groq specific
        if provider == "groq":
            model_kwargs = {}
            if "max_tokens" in extra_params:
                params["max_tokens"] = extra_params["max_tokens"]
            if "top_p" in extra_params:
                model_kwargs["top_p"] = extra_params["top_p"]
            if model_kwargs:
                params["model_kwargs"] = model_kwargs
        
        # Ollama specific
        if provider == "ollama":
            if "validate_model_on_init" in extra_params:
                params["validate_model_on_init"] = extra_params["validate_model_on_init"]
            
            base_url = extra_params.get("base_url") or os.getenv("OLLAMA_BASE_URL")
            if base_url:
                params["base_url"] = base_url

        return model_class(**params)

    def check_health(self, key: Optional[str] = None) -> Dict[str, Any]:
        """
        Performs a health check on the specified model or the default one.
        Returns a dict with status and details.
        """
        target_key = key or LLM
        result = {
            "model": target_key,
            "status": "unknown",
            "latency_ms": 0,
            "error": None
        }
        
        import time
        start_time = time.time()
        
        try:
            model = self.get_model(target_key)
            # Simple invocation to check connectivity
            # We use invoke with a simple string to test basic connectivity
            # For chat models, we send a simple message
            from langchain_core.messages import HumanMessage
            response = model.invoke([HumanMessage(content="ping")])
            
            result["status"] = "ok"
            result["response_preview"] = str(response.content)[:50]
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.warning(f"Health check failed for {target_key}: {e}")
            
        result["latency_ms"] = int((time.time() - start_time) * 1000)
        return result

# Singleton instance
llm_factory = LLMFactory()

# Default LLM Key
LLM = f"{settings.llm_model.provider}/{settings.llm_model.model_name}"

# Backward compatibility proxy for 'models' dict
# This allows existing code using models[key] to work, 
# but triggers lazy loading.
class LazyModelDict(dict):
    def __init__(self, factory: LLMFactory):
        self._factory = factory
    
    def __getitem__(self, key):
        return self._factory.get_model(key)
    
    def get(self, key, default=None):
        try:
            return self._factory.get_model(key)
        except Exception:
            return default
            
    def __contains__(self, key):
        # We assume it exists if it's in configs or valid format
        return True 

    def keys(self):
        return self._factory._configs.keys()

    def values(self):
        # Warning: This triggers instantiation of ALL configured models
        return [self[k] for k in self.keys()]

    def items(self):
        # Warning: This triggers instantiation of ALL configured models
        return [(k, self[k]) for k in self.keys()]
    
    def __iter__(self):
        return iter(self.keys())
    
    def __len__(self):
        return len(self._factory._configs)

models = LazyModelDict(llm_factory)
