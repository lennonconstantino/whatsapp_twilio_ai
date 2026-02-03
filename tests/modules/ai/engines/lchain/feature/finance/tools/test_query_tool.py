"""Tests for Query Tool."""

from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest
from pydantic import BaseModel, Field, ValidationError

from src.modules.ai.engines.lchain.core.models.tool_result import ToolResult
from src.modules.ai.engines.lchain.feature.finance.tools.query import (
    QueryConfig, QueryDataTool, WhereStatement, build_simple_query,
    query_data_function, supabase_query_from_config)

# --- Mocks for Models and Repositories ---


class MockModel(BaseModel):
    """Mock Pydantic model."""

    id: str
    name: str
    value: int
    active: bool = True


class MockRepo:
    """Mock Repository."""

    def query_dynamic(self, select_columns, filters):
        return []


# --- Tests ---


class TestQueryModels:
    """Tests for QueryConfig and WhereStatement."""

    def test_where_statement_validation_valid(self):
        """Test valid WhereStatement operators."""
        valid_ops = ["eq", "gt", "lt", "gte", "lte", "ne", "ct", "=", ">", "contains"]
        for op in valid_ops:
            ws = WhereStatement(column="col", operator=op, value="val")
            assert ws.operator in ["eq", "gt", "lt", "gte", "lte", "ne", "ct"]

    def test_where_statement_validation_invalid(self):
        """Test invalid WhereStatement operator."""
        with pytest.raises(ValueError):
            WhereStatement(column="col", operator="invalid", value="val")

    def test_query_config_parse_where_list(self):
        """Test parsing list of conditions in QueryConfig."""
        # [column, op, value] format
        where = [["col1", "=", "val1"], ["col2", "gt", 10]]
        config = QueryConfig(table_name="test", where=where)
        assert len(config.where) == 2
        assert config.where[0].column == "col1"
        assert config.where[0].operator == "eq"
        assert config.where[1].operator == "gt"

    def test_query_config_parse_where_dict(self):
        """Test parsing dict conditions in QueryConfig."""
        where = {"col1": "val1", "col2": {"$gt": 10}}
        config = QueryConfig(table_name="test", where=where)
        assert len(config.where) == 2
        # Order is not guaranteed in dict, so check presence
        col1 = next(w for w in config.where if w.column == "col1")
        col2 = next(w for w in config.where if w.column == "col2")

        assert col1.operator == "eq"
        assert col1.value == "val1"
        assert col2.operator == "gt"
        assert col2.value == 10

    def test_query_config_parse_where_string(self):
        """Test parsing string conditions in QueryConfig."""
        where = "col1 = 'val1' AND col2 > 10"
        config = QueryConfig(table_name="test", where=where)
        assert len(config.where) == 2
        assert config.where[0].column == "col1"
        assert config.where[1].column == "col2"

    def test_query_config_parse_invalid(self):
        """Test parsing invalid formats."""
        with pytest.raises(ValidationError):
            QueryConfig(table_name="test", where=[123])  # Invalid type inside list


class TestQueryExecution:
    """Tests for query execution logic."""

    @pytest.fixture
    def mock_tables(self):
        """Patch TABLES dictionary."""
        mock_repo = Mock()
        mock_repo_factory = Mock(return_value=mock_repo)
        tables = {"mock_table": (MockModel, mock_repo_factory)}
        with patch(
            "src.modules.ai.engines.lchain.feature.finance.tools.query.TABLES", tables
        ):
            yield tables

    def test_supabase_query_from_config_success(self):
        """Test successful query execution."""
        mock_repo = Mock()
        expected_data = [{"id": "1", "name": "Test", "value": 10}]
        mock_repo.query_dynamic.return_value = expected_data

        config = QueryConfig(
            table_name="mock_table",
            select_columns=["id", "name"],
            where=[WhereStatement(column="value", operator="gt", value=5)],
        )

        result = supabase_query_from_config(config, MockModel, mock_repo)

        assert result == expected_data
        mock_repo.query_dynamic.assert_called_once()
        call_args = mock_repo.query_dynamic.call_args[1]
        assert call_args["select_columns"] == ["id", "name"]
        assert call_args["filters"][0]["column"] == "value"

    def test_supabase_query_from_config_invalid_column(self):
        """Test validation of non-existent column."""
        mock_repo = Mock()

        # Invalid select
        config = QueryConfig(table_name="mock_table", select_columns=["invalid"])
        with pytest.raises(ValueError, match="Column invalid not found"):
            supabase_query_from_config(config, MockModel, mock_repo)

        # Invalid where
        config = QueryConfig(
            table_name="mock_table",
            where=[WhereStatement(column="invalid", operator="eq", value=1)],
        )
        with pytest.raises(ValueError, match="Column invalid not found"):
            supabase_query_from_config(config, MockModel, mock_repo)

    def test_query_data_function_success(self, mock_tables):
        """Test query_data_function success path."""
        # mock_tables['mock_table'][1] is the factory, return_value is the repo mock
        mock_repo = mock_tables["mock_table"][1].return_value
        mock_repo.query_dynamic.return_value = [
            {"id": "1", "name": "Test", "value": 10}
        ]

        config = QueryConfig(table_name="mock_table")
        result = query_data_function(config)

        assert result.success is True
        assert "Test" in result.content

    def test_query_data_function_table_not_found(self):
        """Test query_data_function with invalid table."""
        config = QueryConfig(table_name="invalid_table")
        result = query_data_function(config)

        assert result.success is False
        assert "Table name 'invalid_table' not found" in result.content

    def test_query_data_function_empty_result(self, mock_tables):
        """Test query_data_function with no results."""
        mock_repo = mock_tables["mock_table"][1].return_value
        mock_repo.query_dynamic.return_value = []

        config = QueryConfig(table_name="mock_table")
        result = query_data_function(config)

        assert result.success is True
        assert "No results found" in result.content

    def test_query_data_function_validation_error(self, mock_tables):
        """Test query_data_function catching validation error."""
        config = QueryConfig(table_name="mock_table", select_columns=["invalid"])

        # No need to mock repo return, validation happens before
        result = query_data_function(config)

        assert result.success is False
        assert "Validation error" in result.content

    def test_query_data_function_unexpected_error(self, mock_tables):
        """Test query_data_function catching unexpected error."""
        mock_repo = mock_tables["mock_table"][1].return_value
        mock_repo.query_dynamic.side_effect = Exception("Boom")

        config = QueryConfig(table_name="mock_table")
        result = query_data_function(config)

        assert result.success is False
        assert "Query error" in result.content


class TestQueryHelpers:
    """Tests for helper functions."""

    def test_build_simple_query(self):
        """Test build_simple_query helper."""
        config = build_simple_query(
            table_name="test", filters={"col1": "val1"}, columns=["col1"]
        )

        assert config.table_name == "test"
        assert config.select_columns == ["col1"]
        assert len(config.where) == 1
        assert config.where[0].column == "col1"
        assert config.where[0].value == "val1"


class TestQueryDataTool:
    """Test Tool class wrapper."""

    def test_tool_execution(self):
        """Test tool execution."""
        tool = QueryDataTool()

        with patch.object(
            QueryDataTool, "execute", return_value=ToolResult(content="Ok", success=True)
        ) as mock_execute:
            result = tool._run(table_name="expense")

            assert result.content == "Ok"
            mock_execute.assert_called_once()
