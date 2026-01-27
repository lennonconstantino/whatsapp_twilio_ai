import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

_ = load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

_PROVIDER_MAP = {
    "openai": ChatOpenAI,
    "google": ChatGoogleGenerativeAI,
    "groq": ChatGroq,
    "ollama": ChatOllama,
}

MODEL_CONFIGS = [
    {
        "key_name": "ogptoss20b",  # um pouco lento, mas funcionou de primeira
        "provider": "ollama",
        "model_name": "gpt-oss:20b",
        "temprature": 0,
        "validate_model_on_init": True,
    },
    {
        "key_name": "dsr1llama70b",
        "provider": "groq",
        "model_name": "deepseek-r1-distill-llama-70b",  # "mixtral-8x7b-32768"  # Melhor para raciocínio
        "temprature": 0,
        "max_tokens": 1000,  # Contexto adequado
        "top_p": 0.1,  # Reduzir aleatoriedade
        # "frequency_penalty": 0.1,  # Evitar repetições
        # funciona bem depois de aquecido
    },
    {
        "key_name": "llama388b8192",
        "provider": "groq",
        "model_name": "llama3-8b-8192",  # Mais rápido para execução, Nao é bom para trabalhar com chamadas de tools em cadeia
        "temprature": 0,
        "max_tokens": 500,  # Limitar para foco
        "top_p": 0.1,  # Reduzir aleatoriedade
    },
    {
        "key_name": "g25flash",  # Topzera e custo beneficio
        "provider": "google",
        "model_name": "gemini-2.5-flash",
        "temprature": 0,
    },
    {
        "key_name": "3.5-turbo",  # Nao é eficiente para o uso e chamada de ferramentas
        "provider": "openai",
        "model_name": "gpt-3.5-turbo",
    },
    {
        "key_name": "o4",  # Melhor custo beneficio
        "provider": "openai",
        "model_name": "o4-mini-2025-04-16",
    },
    {
        "key_name": "gpt_4o",  # Topzera
        "provider": "openai",
        "model_name": "gpt-4o-2024-08-06",
    },
]


def _create_chat_model(
    model_name: str, provider: str, temperature: float | None = None
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
        # Importar as classes necessárias para safety_settings
        from langchain_google_genai import HarmBlockThreshold, HarmCategory

        safety_settings = {
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        }
        params["safety_settings"] = safety_settings

    return model_class(**params)


models = {}

for config in MODEL_CONFIGS:
    try:
        models[config["key_name"]] = _create_chat_model(
            model_name=config["model_name"],
            provider=config["provider"],
            temperature=config.get("temperature"),
        )
    except Exception as exc:
        # Evita falhar a inicialização caso uma integração (ex: GROQ) não tenha API key.
        # Os modelos que puderem ser iniciados (ex: ollama) ficarão disponíveis em `models`.
        # print ao invés de logging para não depender de config de logging aqui.
        print(
            f"[llm] Warning: failed to initialize model {config.get('key_name')}: {exc}"
        )

LLM = "ogptoss20b"

if __name__ == "__main__":
    print()
