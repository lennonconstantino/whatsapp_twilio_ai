"""Tests for BaseRepository."""

from typing import Any, Dict, Optional
from unittest.mock import MagicMock, Mock

import pytest
from pydantic import BaseModel, Field

from src.core.database.base_repository import BaseRepository


class MockModel(BaseModel):
    """Test model for repository tests."""

    id: str
    name: str
    value: int


class MockModelInt(BaseModel):
    """Test model with integer ID."""

    id: int
    name: str


class MockRepository(BaseRepository[MockModel]):
    """Test repository implementation."""

    pass


class MockRepositoryInt(BaseRepository[MockModelInt]):
    """Test repository implementation for int IDs."""

    pass


@pytest.fixture
def mock_client():
    """Mock Supabase client."""
    return MagicMock()


@pytest.fixture
def repository(mock_client):
    """Create repository instance with mock client."""
    return MockRepository(
        client=mock_client,
        table_name="test_table",
        model_class=MockModel,
        validates_ulid=True,
    )


@pytest.fixture
def repository_int(mock_client):
    """Create repository instance for int IDs."""
    return MockRepositoryInt(
        client=mock_client,
        table_name="test_table_int",
        model_class=MockModelInt,
        validates_ulid=False,
    )


class TestBaseRepository:
    """Test suite for BaseRepository."""

    def test_init(self, mock_client):
        """Test repository initialization."""
        repo = BaseRepository(mock_client, "test", MockModel)
        assert repo.client == mock_client
        assert repo.table_name == "test"
        assert repo.model_class == MockModel
        assert repo.validates_ulid is True

    def test_validate_id_ulid(self, repository):
        """Test ULID validation."""
        # Valid ULID
        valid_ulid = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        repository._validate_id(valid_ulid)

        # Invalid ULID (wrong length) - should check inside is_valid_ulid if passed directly?
        # The _validate_id method:
        # if isinstance(id_value, str):
        #    if not is_valid_ulid(id_value):
        #        raise ValueError(...)

        with pytest.raises(ValueError, match="Invalid ULID format"):
            repository._validate_id("invalid-ulid")  # Short string fails is_valid_ulid

        # None value (should skip)
        repository._validate_id(None)

    def test_validate_id_int(self, repository_int):
        """Test integer ID validation (should skip ULID check)."""
        repository_int._validate_id(123)
        # Should not raise for string if validation disabled
        repository_int._validate_id("some-string")

    def test_create_success(self, repository, mock_client):
        """Test successful creation."""
        data = {"name": "Test", "value": 10}
        expected_data = {"id": "01ARZ3NDEKTSV4RRFFQ69G5FAV", **data}

        # Setup mock chain
        mock_table = mock_client.table.return_value
        mock_insert = mock_table.insert.return_value
        mock_execute = mock_insert.execute.return_value
        mock_execute.data = [expected_data]

        result = repository.create(data)

        assert isinstance(result, MockModel)
        assert result.id == expected_data["id"]
        assert result.name == expected_data["name"]

        mock_client.table.assert_called_with("test_table")
        mock_table.insert.assert_called_with(data)

    def test_create_validation_error(self, repository):
        """Test creation with invalid ULID in data."""
        # Need 26 chars to trigger validation logic inside create method
        # 'I' is invalid in Crockford Base32
        invalid_ulid = "01ARZ3NDEKTSV4RRFFQ69G5FAI"
        data = {"id": invalid_ulid, "name": "Test", "value": 10}

        with pytest.raises(ValueError, match="Invalid ULID format"):
            repository.create(data)

    def test_create_db_error(self, repository, mock_client):
        """Test handling of database errors during create."""
        mock_client.table.side_effect = Exception("DB Error")

        with pytest.raises(Exception, match="DB Error"):
            repository.create({"name": "Test", "value": 10})

    def test_find_by_id_success(self, repository, mock_client):
        """Test successful find by ID."""
        ulid = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        expected_data = {"id": ulid, "name": "Test", "value": 10}

        mock_table = mock_client.table.return_value
        mock_select = mock_table.select.return_value
        mock_eq = mock_select.eq.return_value
        mock_execute = mock_eq.execute.return_value
        mock_execute.data = [expected_data]

        result = repository.find_by_id(ulid)

        assert isinstance(result, MockModel)
        assert result.id == ulid

        mock_select.eq.assert_called_with("id", ulid)

    def test_find_by_id_not_found(self, repository, mock_client):
        """Test find by ID when record doesn't exist."""
        ulid = "01ARZ3NDEKTSV4RRFFQ69G5FAV"

        mock_table = mock_client.table.return_value
        mock_select = mock_table.select.return_value
        mock_eq = mock_select.eq.return_value
        mock_execute = mock_eq.execute.return_value
        mock_execute.data = []

        result = repository.find_by_id(ulid)
        assert result is None

    def test_find_by_id_invalid_ulid(self, repository):
        """Test find by ID with invalid ULID."""
        # _validate_id calls is_valid_ulid directly, so any invalid string fails
        with pytest.raises(ValueError, match="Invalid ULID format"):
            repository.find_by_id("invalid-ulid")

    def test_find_all(self, repository, mock_client):
        """Test find all with pagination."""
        expected_data = [
            {"id": "01ARZ3NDEKTSV4RRFFQ69G5FAV", "name": "Test1", "value": 1},
            {"id": "01ARZ3NDEKTSV4RRFFQ69G5FAW", "name": "Test2", "value": 2},
        ]

        mock_table = mock_client.table.return_value
        mock_select = mock_table.select.return_value
        mock_range = mock_select.range.return_value
        mock_execute = mock_range.execute.return_value
        mock_execute.data = expected_data

        results = repository.find_all(limit=10, offset=0)

        assert len(results) == 2
        assert isinstance(results[0], MockModel)
        mock_select.range.assert_called_with(0, 9)

    def test_update_success(self, repository, mock_client):
        """Test successful update."""
        ulid = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        update_data = {"name": "Updated"}
        expected_data = {"id": ulid, "name": "Updated", "value": 10}

        mock_table = mock_client.table.return_value
        mock_update = mock_table.update.return_value
        mock_eq = mock_update.eq.return_value
        mock_execute = mock_eq.execute.return_value
        mock_execute.data = [expected_data]

        result = repository.update(ulid, update_data)

        assert isinstance(result, MockModel)
        assert result.name == "Updated"
        mock_table.update.assert_called_with(update_data)
        mock_update.eq.assert_called_with("id", ulid)

    def test_update_validation_error(self, repository):
        """Test update with invalid ULID."""
        # Invalid ID passed as argument
        with pytest.raises(ValueError, match="Invalid ULID format"):
            repository.update("invalid", {"name": "Test"})

        # Invalid ID in data (must be 26 chars to trigger check)
        ulid = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        invalid_related_id = "01ARZ3NDEKTSV4RRFFQ69G5FAI"
        with pytest.raises(ValueError, match="Invalid ULID format"):
            repository.update(ulid, {"related_id": invalid_related_id})

    def test_delete_success(self, repository, mock_client):
        """Test successful deletion."""
        ulid = "01ARZ3NDEKTSV4RRFFQ69G5FAV"

        mock_table = mock_client.table.return_value
        mock_delete = mock_table.delete.return_value
        mock_eq = mock_delete.eq.return_value
        mock_execute = mock_eq.execute.return_value
        mock_execute.data = [{"id": ulid}]

        result = repository.delete(ulid)
        assert result is True

    def test_find_by_filters(self, repository, mock_client):
        """Test find by filters."""
        filters = {"name": "Test", "value": 10}
        expected_data = [
            {"id": "01ARZ3NDEKTSV4RRFFQ69G5FAV", "name": "Test", "value": 10}
        ]

        query_mock = MagicMock()
        mock_client.table.return_value.select.return_value = query_mock
        query_mock.eq.return_value = query_mock
        query_mock.limit.return_value = query_mock
        query_mock.execute.return_value.data = expected_data

        results = repository.find_by(filters)

        assert len(results) == 1
        assert results[0].name == "Test"
        # Verify calls - eq should be called twice
        assert query_mock.eq.call_count == 2
        query_mock.limit.assert_called_with(100)

    def test_count(self, repository, mock_client):
        """Test count records."""
        mock_table = mock_client.table.return_value
        mock_select = mock_table.select.return_value
        mock_select.execute.return_value.count = 42

        count = repository.count()

        assert count == 42
        mock_table.select.assert_called_with("*", count="exact")

    def test_query_dynamic(self, repository, mock_client):
        """Test dynamic query execution."""
        filters = [
            {"column": "name", "operator": "eq", "value": "Test"},
            {"column": "value", "operator": "gt", "value": 5},
        ]
        expected_data = [
            {"id": "01ARZ3NDEKTSV4RRFFQ69G5FAV", "name": "Test", "value": 10}
        ]

        query_mock = MagicMock()
        mock_client.table.return_value.select.return_value = query_mock
        query_mock.eq.return_value = query_mock
        query_mock.gt.return_value = query_mock
        query_mock.execute.return_value.data = expected_data

        results = repository.query_dynamic(
            select_columns=["id", "name"], filters=filters
        )

        assert results == expected_data
        mock_client.table.return_value.select.assert_called_with("id, name")
        query_mock.eq.assert_called_with("name", "Test")
        query_mock.gt.assert_called_with("value", 5)
