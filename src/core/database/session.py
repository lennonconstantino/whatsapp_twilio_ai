"""
Database connection utilities.
Handles Supabase client initialization and management.
"""
import logging
from typing import Optional
from supabase import create_client, Client

from src.core.config import settings

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Singleton class to manage Supabase database connection.
    """
    _instance: Optional['DatabaseConnection'] = None
    _client: Optional[Client] = None
    
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
            logger.info("Successfully connected to Supabase")
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            raise
    
    @property
    def client(self) -> Client:
        """Get Supabase client instance."""
        if self._client is None:
            self._connect()
        return self._client
    
    def disconnect(self):
        """Disconnect from database."""
        # Supabase client doesn't require explicit disconnection
        self._client = None
        logger.info("Disconnected from Supabase")


# Global database connection instance
db = DatabaseConnection()


def get_db() -> Client:
    """
    Get database client instance.
    Used for dependency injection in FastAPI.
    
    Returns:
        Supabase client instance
    """
    return db.client
