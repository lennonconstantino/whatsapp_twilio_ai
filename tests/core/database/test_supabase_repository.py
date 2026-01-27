import unittest
from unittest.mock import MagicMock

from pydantic import BaseModel

from src.core.database.interface import IDatabaseSession
from src.core.database.supabase_repository import SupabaseRepository


class TestModel(BaseModel):
    id: str
    name: str


class TestSupabaseRepository(unittest.TestCase):

    def setUp(self):
        self.mock_session = MagicMock(spec=IDatabaseSession)
        self.mock_table = MagicMock()
        self.mock_session.table.return_value = self.mock_table

        self.repo = SupabaseRepository(
            client=self.mock_session,
            table_name="test_table",
            model_class=TestModel,
            validates_ulid=True,
        )

    def test_init(self):
        self.assertEqual(self.repo.table_name, "test_table")
        self.assertEqual(self.repo.model_class, TestModel)
        self.assertTrue(self.repo.validates_ulid)

    def test_validate_id_success(self):
        # Valid ULID
        valid_ulid = "01HRZ32M1X6Z4P5R7W8K9A0M1N"
        self.repo._validate_id(valid_ulid)

    def test_validate_id_invalid(self):
        # Invalid ULID
        with self.assertRaises(ValueError):
            self.repo._validate_id("invalid-ulid")

    def test_validate_id_skipped(self):
        repo_no_validate = SupabaseRepository(
            client=self.mock_session,
            table_name="test_table",
            model_class=TestModel,
            validates_ulid=False,
        )
        repo_no_validate._validate_id("invalid-ulid")

    def test_create_success(self):
        data = {"name": "test"}
        mock_response = MagicMock()
        mock_response.data = [{"id": "01HRZ32M1X6Z4P5R7W8K9A0M1N", "name": "test"}]
        self.mock_table.insert.return_value.execute.return_value = mock_response

        result = self.repo.create(data)

        self.assertIsInstance(result, TestModel)
        self.assertEqual(result.id, "01HRZ32M1X6Z4P5R7W8K9A0M1N")
        self.assertEqual(result.name, "test")

    def test_create_validation_error(self):
        # Data with invalid ULID
        data = {"other_id": "invalid"}

        with self.assertRaises(ValueError):
            self.repo.create(data)

    def test_get_by_id_success(self):
        valid_ulid = "01HRZ32M1X6Z4P5R7W8K9A0M1N"
        mock_response = MagicMock()
        mock_response.data = [{"id": valid_ulid, "name": "test"}]
        self.mock_table.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        result = self.repo.find_by_id(valid_ulid)

        self.assertIsNotNone(result)
        self.assertEqual(result.id, valid_ulid)

    def test_get_by_id_not_found(self):
        valid_ulid = "01HRZ32M1X6Z4P5R7W8K9A0M1N"
        mock_response = MagicMock()
        mock_response.data = []
        self.mock_table.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        result = self.repo.find_by_id(valid_ulid)

        self.assertIsNone(result)

    def test_update_success(self):
        valid_ulid = "01HRZ32M1X6Z4P5R7W8K9A0M1N"
        data = {"name": "updated"}
        mock_response = MagicMock()
        mock_response.data = [{"id": valid_ulid, "name": "updated"}]
        self.mock_table.update.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        result = self.repo.update(valid_ulid, data)

        self.assertIsNotNone(result)
        self.assertEqual(result.name, "updated")

    def test_delete_success(self):
        valid_ulid = "01HRZ32M1X6Z4P5R7W8K9A0M1N"
        mock_response = MagicMock()
        mock_response.data = [{"id": valid_ulid}]
        self.mock_table.delete.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        result = self.repo.delete(valid_ulid)

        self.assertTrue(result)

    def test_list_all(self):
        mock_response = MagicMock()
        mock_response.data = [
            {"id": "01HRZ32M1X6Z4P5R7W8K9A0M1N", "name": "test1"},
            {"id": "01HRZ32M1X6Z4P5R7W8K9A0M1M", "name": "test2"},
        ]
        self.mock_table.select.return_value.range.return_value.execute.return_value = (
            mock_response
        )

        results = self.repo.find_all()

        self.assertEqual(len(results), 2)
        self.assertIsInstance(results[0], TestModel)
