
import unittest
from unittest.mock import MagicMock, patch
from typing import Dict, Any, List

from src.core.database.base_repository import BaseRepository
from src.modules.ai.engines.lchain.feature.finance.tools.query import (
    QueryConfig, 
    supabase_query_from_config, 
    WhereStatement
)
from pydantic import BaseModel

# Mock Models
class MockModel(BaseModel):
    id: int
    name: str
    amount: float
    category: str

class TestQueryDynamicRefactor(unittest.TestCase):
    
    def setUp(self):
        # Setup mock client
        self.mock_client = MagicMock()
        self.mock_table = MagicMock()
        self.mock_select = MagicMock()
        
        # Chain setup: client.table().select()
        self.mock_client.table.return_value = self.mock_table
        self.mock_table.select.return_value = self.mock_select
        
        # Repository instance with mock client
        self.repo = BaseRepository(
            client=self.mock_client,
            table_name="test_table",
            model_class=MockModel,
            validates_ulid=False
        )

    def test_base_repository_query_dynamic_basic(self):
        """Test query_dynamic with basic selection"""
        # Setup return value
        expected_data = [{"id": 1, "name": "Test", "amount": 100.0, "category": "A"}]
        self.mock_select.execute.return_value.data = expected_data
        
        # Execute
        result = self.repo.query_dynamic(select_columns=["id", "name"])
        
        # Verify
        self.mock_client.table.assert_called_with("test_table")
        self.mock_table.select.assert_called_with("id, name")
        self.assertEqual(result, expected_data)

    def test_base_repository_query_dynamic_filters(self):
        """Test query_dynamic with filters"""
        # Setup chain for filters
        mock_eq = MagicMock()
        mock_gt = MagicMock()
        
        self.mock_select.eq.return_value = mock_eq
        mock_eq.gt.return_value = mock_gt
        mock_gt.execute.return_value.data = []
        
        filters = [
            {"column": "category", "operator": "eq", "value": "A"},
            {"column": "amount", "operator": "gt", "value": 50}
        ]
        
        # Execute
        self.repo.query_dynamic(filters=filters)
        
        # Verify calls
        self.mock_select.eq.assert_called_with("category", "A")
        mock_eq.gt.assert_called_with("amount", 50)

    def test_tool_integration(self):
        """Test integration between tool logic and repository"""
        # Mock repository method to verify it's called
        self.repo.query_dynamic = MagicMock(return_value=[])
        
        # Config
        config = QueryConfig(
            table_name="test_table",
            select_columns=["name", "amount"],
            where=[
                WhereStatement(column="amount", operator="gt", value=100)
            ]
        )
        
        # Execute tool logic
        supabase_query_from_config(config, MockModel, self.repo)
        
        # Verify repository was called correctly
        self.repo.query_dynamic.assert_called_once()
        call_args = self.repo.query_dynamic.call_args
        
        self.assertEqual(call_args.kwargs['select_columns'], ["name", "amount"])
        self.assertEqual(len(call_args.kwargs['filters']), 1)
        self.assertEqual(call_args.kwargs['filters'][0]['column'], "amount")
        self.assertEqual(call_args.kwargs['filters'][0]['operator'], "gt")
        self.assertEqual(call_args.kwargs['filters'][0]['value'], 100) # Note: Pydantic might keep it as int/str depending on definition, here value is Any

    def test_tool_validation_error(self):
        """Test tool validation for non-existent columns"""
        config = QueryConfig(
            table_name="test_table",
            select_columns=["non_existent_column"]
        )
        
        with self.assertRaises(ValueError) as cm:
            supabase_query_from_config(config, MockModel, self.repo)
            
        self.assertIn("not found in model", str(cm.exception))

if __name__ == '__main__':
    unittest.main()
