"""
SQLAlchemy implementation of the Repository Pattern.
Compatible with PostgreSQL, MySQL, SQLite, and others supported by SQLAlchemy.
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from src.core.database.interface import IRepository
from src.core.utils import get_logger

logger = get_logger(__name__)

T = TypeVar("T")  # Pydantic Model
M = TypeVar("M")  # SQLAlchemy Model


class SQLAlchemyRepository(Generic[T, M]):
    """
    Generic SQL implementation of IRepository using SQLAlchemy.

    This class works with ANY database supported by SQLAlchemy (Postgres, MySQL, SQLite, etc).
    It handles the mapping between SQLAlchemy ORM models and Pydantic models.
    """

    def __init__(self, session: Session, orm_model: Type[M], pydantic_model: Type[T]):
        """
        Initialize SQLAlchemy repository.

        Args:
            session: SQLAlchemy Session instance
            orm_model: SQLAlchemy ORM model class
            pydantic_model: Pydantic model class (for return types)
        """
        self.session = session
        self.orm_model = orm_model
        self.pydantic_model = pydantic_model

    def _to_pydantic(self, orm_obj: Optional[M]) -> Optional[T]:
        """Convert SQLAlchemy ORM object to Pydantic model."""
        if not orm_obj:
            return None
        return self.pydantic_model.model_validate(orm_obj, from_attributes=True)

    def create(self, data: Dict[str, Any]) -> Optional[T]:
        """Create a new record."""
        try:
            orm_obj = self.orm_model(**data)
            self.session.add(orm_obj)
            self.session.commit()
            self.session.refresh(orm_obj)
            return self._to_pydantic(orm_obj)
        except Exception as e:
            self.session.rollback()
            logger.error(
                f"Error creating record in {self.orm_model.__tablename__}", error=str(e)
            )
            raise

    def find_by_id(self, id_value: Any, id_column: str = "id") -> Optional[T]:
        """Find a record by ID."""
        stmt = select(self.orm_model).where(
            getattr(self.orm_model, id_column) == id_value
        )
        result = self.session.execute(stmt).scalar_one_or_none()
        return self._to_pydantic(result)

    def update(
        self, id_value: Union[int, str], data: Dict[str, Any], id_column: str = "id"
    ) -> Optional[T]:
        """Update a record."""
        try:
            stmt = (
                update(self.orm_model)
                .where(getattr(self.orm_model, id_column) == id_value)
                .values(**data)
                .execution_options(synchronize_session="fetch")
            )
            result = self.session.execute(stmt)

            if result.rowcount == 0:
                return None

            self.session.commit()
            return self.find_by_id(id_value, id_column)
        except Exception as e:
            self.session.rollback()
            logger.error(
                f"Error updating record in {self.orm_model.__tablename__}", error=str(e)
            )
            raise

    def delete(self, id_value: Union[int, str], id_column: str = "id") -> bool:
        """Delete a record."""
        try:
            stmt = delete(self.orm_model).where(
                getattr(self.orm_model, id_column) == id_value
            )
            result = self.session.execute(stmt)
            self.session.commit()
            return result.rowcount > 0
        except Exception as e:
            self.session.rollback()
            logger.error(
                f"Error deleting record in {self.orm_model.__tablename__}", error=str(e)
            )
            raise

    def find_by(self, filters: Dict[str, Any], limit: int = 100) -> List[T]:
        """Find records by simple equality filters."""
        stmt = select(self.orm_model)

        for key, value in filters.items():
            if hasattr(self.orm_model, key):
                stmt = stmt.where(getattr(self.orm_model, key) == value)

        stmt = stmt.limit(limit)
        results = self.session.execute(stmt).scalars().all()

        return [self._to_pydantic(obj) for obj in results]

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records matching filters."""
        stmt = select(func.count()).select_from(self.orm_model)

        if filters:
            for key, value in filters.items():
                if hasattr(self.orm_model, key):
                    stmt = stmt.where(getattr(self.orm_model, key) == value)

        return self.session.execute(stmt).scalar()

    def query_dynamic(
        self, select_columns: List[str] = None, filters: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute dynamic query (generic implementation)."""
        stmt = select(self.orm_model)

        if filters:
            for f in filters:
                col = f.get("column")
                val = f.get("value")
                op = f.get("operator", "eq")

                if hasattr(self.orm_model, col):
                    column_attr = getattr(self.orm_model, col)
                    if op == "eq":
                        stmt = stmt.where(column_attr == val)
                    elif op == "gt":
                        stmt = stmt.where(column_attr > val)
                    elif op == "lt":
                        stmt = stmt.where(column_attr < val)

        results = self.session.execute(stmt).scalars().all()
        return [self._to_pydantic(obj).model_dump() for obj in results]
