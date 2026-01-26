"""
Database connection utilities.
Handles Supabase client initialization and management.
"""
import logging
from typing import Optional, Any
from supabase import create_client, Client

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
    _instance: Optional['DatabaseConnection'] = None
    _client: Optional[Client] = None
    _session: Optional[IDatabaseSession] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize database connection."""
        if self._client is None:
            self._connect()
    
    def _connect(self):
        """Establish connection to Supabase."""
        try:
            self._client = create_client(
                settings.supabase.url,
                settings.supabase.key
            )
            self._session = SupabaseSession(self._client)
            logger.info("Successfully connected to Supabase")
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
