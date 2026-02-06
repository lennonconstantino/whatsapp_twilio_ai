"""
Database connection utilities.
Handles Supabase client initialization and management.
"""

import logging
from typing import Any, Optional

from supabase import Client, ClientOptions, create_client

from src.core.config import settings
from src.core.database.interface import IDatabaseSession

logger = logging.getLogger(__name__)


class SupabaseSession(IDatabaseSession):
    """
    Wrapper for Supabase client implementing IDatabaseSession.
    """

    def __init__(self, client: Client):
        self._client = client

    def table(self, name: str) -> Any:
        return self._client.table(name)


class DatabaseConnection:
    """
    Singleton class to manage Supabase database connection.
    """

    _instance: Optional["DatabaseConnection"] = None
    _client: Optional[Client] = None
    _session: Optional[IDatabaseSession] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize database connection."""
        pass

    def _validate_supabase_settings(self) -> None:
        missing: list[str] = []
        if not settings.supabase.url:
            missing.append("SUPABASE_URL")
        if not settings.supabase.key:
            missing.append("SUPABASE_KEY")
        if missing:
            raise RuntimeError(
                "Supabase backend selecionado, mas variáveis ausentes: "
                + ", ".join(missing)
            )

    def _connect(self):
        """Establish connection to Supabase."""
        if settings.database.backend != "supabase":
            raise RuntimeError(
                f"DatabaseConnection (Supabase) não pode ser usado quando DATABASE_BACKEND={settings.database.backend}"
            )
        try:
            self._validate_supabase_settings()
            
            # Use Service Key if available (Backend should use Service Role to bypass RLS)
            # Otherwise fall back to Anon Key
            api_key = settings.supabase.service_key or settings.supabase.key
            key_type = "SERVICE_KEY" if settings.supabase.service_key else "ANON_KEY"
            
            if not api_key:
                 raise RuntimeError("No Supabase API key found (neither SERVICE_KEY nor KEY)")

            options = ClientOptions(schema=settings.supabase.db_schema)
            self._client = create_client(
                settings.supabase.url, api_key, options=options
            )
            self._session = SupabaseSession(self._client)
            logger.info(
                f"Successfully connected to Supabase (schema={settings.supabase.db_schema}, key_type={key_type})"
            )
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            raise

    @property
    def client(self) -> Client:
        """Get Supabase client instance (Deprecated - prefer session)."""
        if self._client is None:
            self._connect()
        return self._client

    @property
    def session(self) -> IDatabaseSession:
        """Get database session instance."""
        if self._client is None:
            self._connect()
        return self._session

    def disconnect(self):
        """Disconnect from database."""
        # Supabase client doesn't require explicit disconnection
        self._client = None
        self._session = None
        logger.info("Disconnected from Supabase")


# Global database connection instance
db = DatabaseConnection()


def get_db() -> IDatabaseSession:
    """
    Get database session instance.
    Used for dependency injection in FastAPI.

    Returns:
        IDatabaseSession instance
    """
    return db.session
