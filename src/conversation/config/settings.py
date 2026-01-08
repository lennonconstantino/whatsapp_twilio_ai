"""
Configurações da aplicação
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """
    Configurações da aplicação carregadas de variáveis de ambiente.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Supabase
    supabase_url: str
    supabase_key: str
    
    # Database
    database_schema: str = "conversations"
    
    # Conversation Settings
    conversation_expiry_hours: int = 24
    idle_timeout_minutes: int = 30
    
    # Closure Detection
    closure_keywords: List[str] = [
        "obrigado",
        "obrigada",
        "tchau",
        "até logo",
        "até mais",
        "valeu",
        "encerrar",
        "finalizar",
        "pode fechar",
        "já resolvi",
        "já está resolvido",
        "sem mais",
        "é só isso",
        "só isso",
        "tudo certo",
        "já entendi",
        "entendi",
        "ok obrigado",
        "ok obrigada",
        "bye",
        "thanks",
        "thank you",
    ]
    
    # Background Jobs
    cleanup_job_interval_minutes: int = 15
    expiry_check_interval_minutes: int = 5
    
    # Logging
    log_level: str = "INFO"
    
    @property
    def conversation_expiry_seconds(self) -> int:
        """Retorna o tempo de expiração em segundos"""
        return self.conversation_expiry_hours * 3600
    
    @property
    def idle_timeout_seconds(self) -> int:
        """Retorna o timeout de inatividade em segundos"""
        return self.idle_timeout_minutes * 60


# Instância global das configurações
settings = Settings()
