"""
Base repository with common CRUD operations.
Provides reusable database operations for all repositories.
"""
from typing import TypeVar, Generic, Optional, List, Dict, Any
from supabase import Client

from ..utils import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """
    Base repository class with common CRUD operations.
    
    Attributes:
        table_name: Name of the database table
        model_class: Pydantic model class for this repository
    """
    
    def __init__(self, client: Client, table_name: str, model_class: type):
        """
        Initialize base repository.
        
        Args:
            client: Supabase client instance
            table_name: Name of the database table
            model_class: Pydantic model class
        """
        self.client = client
        self.table_name = table_name
        self.model_class = model_class
    
    def create(self, data: Dict[str, Any]) -> Optional[T]:
        """
        Create a new record.
        
        Args:
            data: Data to insert
            
        Returns:
            Created model instance or None
        """
        try:
            result = self.client.table(self.table_name).insert(data).execute()
            if result.data:
                return self.model_class(**result.data[0])
            return None
        except Exception as e:
            logger.error(f"Error creating record in {self.table_name}", error=str(e))
            raise
    
    def find_by_id(self, id_value: Any, id_column: str = "id") -> Optional[T]:
        """
        Find a record by ID.
        
        Args:
            id_value: ID value to search for
            id_column: Name of the ID column
            
        Returns:
            Model instance or None
        """
        try:
            result = self.client.table(self.table_name)\
                .select("*")\
                .eq(id_column, id_value)\
                .execute()
            
            if result.data:
                return self.model_class(**result.data[0])
            return None
        except Exception as e:
            logger.error(
                f"Error finding record by {id_column} in {self.table_name}",
                error=str(e)
            )
            raise
    
    def find_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """
        Find all records with pagination.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of model instances
        """
        try:
            result = self.client.table(self.table_name)\
                .select("*")\
                .range(offset, offset + limit - 1)\
                .execute()
            
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error(f"Error finding all records in {self.table_name}", error=str(e))
            raise
    
    def update(self, id_value: Any, data: Dict[str, Any], id_column: str = "id") -> Optional[T]:
        """
        Update a record.
        
        Args:
            id_value: ID value of the record to update
            data: Data to update
            id_column: Name of the ID column
            
        Returns:
            Updated model instance or None
        """
        try:
            result = self.client.table(self.table_name)\
                .update(data)\
                .eq(id_column, id_value)\
                .execute()
            
            if result.data:
                return self.model_class(**result.data[0])
            return None
        except Exception as e:
            logger.error(
                f"Error updating record in {self.table_name}",
                error=str(e)
            )
            raise
    
    def delete(self, id_value: Any, id_column: str = "id") -> bool:
        """
        Delete a record.
        
        Args:
            id_value: ID value of the record to delete
            id_column: Name of the ID column
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            result = self.client.table(self.table_name)\
                .delete()\
                .eq(id_column, id_value)\
                .execute()
            
            return len(result.data) > 0
        except Exception as e:
            logger.error(
                f"Error deleting record from {self.table_name}",
                error=str(e)
            )
            raise
    
    def find_by(self, filters: Dict[str, Any], limit: int = 100) -> List[T]:
        """
        Find records by multiple filters.
        
        Args:
            filters: Dictionary of column:value pairs to filter by
            limit: Maximum number of records to return
            
        Returns:
            List of model instances
        """
        try:
            query = self.client.table(self.table_name).select("*")
            
            for column, value in filters.items():
                query = query.eq(column, value)
            
            result = query.limit(limit).execute()
            
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error(
                f"Error finding records by filters in {self.table_name}",
                error=str(e)
            )
            raise
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records matching filters.
        
        Args:
            filters: Optional dictionary of column:value pairs to filter by
            
        Returns:
            Number of matching records
        """
        try:
            query = self.client.table(self.table_name).select("*", count="exact")
            
            if filters:
                for column, value in filters.items():
                    query = query.eq(column, value)
            
            result = query.execute()
            return result.count or 0
        except Exception as e:
            logger.error(
                f"Error counting records in {self.table_name}",
                error=str(e)
            )
            raise
