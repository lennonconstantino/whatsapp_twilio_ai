from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from src.core.utils.logging import get_logger
from src.core.config import settings

from dotenv import load_dotenv
_ = load_dotenv()

logger = get_logger(__name__)


_PROVIDER_MAP = {
    "openai": ChatOpenAI,
    "google": ChatGoogleGenerativeAI,
    "groq": ChatGroq,
    "ollama": ChatOllama,
}

MODEL_CONFIGS = [
    {
        "provider": "ollama",
        "model_name": "gpt-oss:20b",
        "temperature": 0,
        "validate_model_on_init": True,
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


def _create_chat_model(
    model_name: str, provider: str, temperature: float | None = None, **extra_params
):
    if provider not in _PROVIDER_MAP:
        raise ValueError(
            f"Provedor nao suportado: {provider}. Provedores suportados sao: {list(_PROVIDER_MAP.keys())}"
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

    # Para Groq, use model_kwargs para parâmetros não-padrão
    if provider == "groq":
        model_kwargs = {}
        if "max_tokens" in extra_params:
            params["max_tokens"] = extra_params["max_tokens"]  # max_tokens é aceito diretamente
        if "top_p" in extra_params:
            model_kwargs["top_p"] = extra_params["top_p"]  # top_p vai para model_kwargs
        if model_kwargs:
            params["model_kwargs"] = model_kwargs
    
    if provider == "ollama":
        if "validate_model_on_init" in extra_params:
            params["validate_model_on_init"] = extra_params["validate_model_on_init"]
        
        # Check for explicit base_url or try to use environment variable via os
        import os
        base_url = extra_params.get("base_url") or os.getenv("OLLAMA_BASE_URL")
        if base_url:
            params["base_url"] = base_url

    return model_class(**params)


models = {}

for config in MODEL_CONFIGS:
    try:
        # Gera o key_name dinamicamente
        key_name = f"{config['provider']}/{config['model_name']}"
        
        # Extraia os parâmetros extras (tudo exceto provider, model_name e temperature)
        extra_params = {k: v for k, v in config.items() 
                       if k not in ["provider", "model_name", "temperature"]}
        
        # Cria o modelo SEM passar key_name para ele
        models[key_name] = _create_chat_model(
            model_name=config["model_name"],
            provider=config["provider"],
            temperature=config.get("temperature"),
            **extra_params
        )
        
        logger.info(f"Model initialized: {key_name}")
        
    except Exception as exc:
        logger.warning(
            "llm_init_warning",
            message=f"Failed to initialize model {config['provider']}/{config['model_name']}",
            error=str(exc),
        )

LLM = f"{settings.llm_model.provider}/{settings.llm_model.model_name}"

if LLM not in models:
    logger.warning(
        "llm_init_missing",
        message=f"Default LLM {LLM} not found in pre-configured models. Attempting dynamic initialization.",
    )
    try:
        models[LLM] = _create_chat_model(
            model_name=settings.llm_model.model_name,
            provider=settings.llm_model.provider,
            temperature=0,
        )
        logger.info(f"Dynamically initialized default LLM: {LLM}")
    except Exception as e:
        logger.error(
            "llm_init_critical_failure",
            message=f"Failed to dynamically initialize default LLM {LLM}",
            error=str(e),
        )

