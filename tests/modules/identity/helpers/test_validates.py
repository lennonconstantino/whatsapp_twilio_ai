import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.modules.identity.helpers.validates import PathValidator

class TestPathValidator(unittest.TestCase):

    def test_validate_none_path(self):
        result = PathValidator.validate_and_check_next_directory(None)
        self.assertFalse(result["valid_path"])
        self.assertEqual(result["message"], "Invalid path: must be a non-empty string")

    def test_validate_non_string_path(self):
        result = PathValidator.validate_and_check_next_directory(123)
        self.assertFalse(result["valid_path"])
        self.assertEqual(result["message"], "Invalid path: must be a non-empty string")

    def test_validate_empty_path_after_strip(self):
        result = PathValidator.validate_and_check_next_directory("   ")
        self.assertFalse(result["valid_path"])
        self.assertEqual(result["message"], "Invalid path: empty string after normalization")

    def test_validate_dangerous_characters(self):
        result = PathValidator.validate_and_check_next_directory("some/../path")
        self.assertFalse(result["valid_path"])
        self.assertEqual(result["message"], "Path contains invalid or dangerous characters")

    @patch('src.modules.identity.helpers.validates.Path')
    def test_path_does_not_exist(self, mock_path_cls):
        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = False
        mock_path_cls.return_value = mock_path_obj

        result = PathValidator.validate_and_check_next_directory("some/path")
        
        self.assertTrue(result["valid_path"])
        self.assertFalse(result["path_exists"])
        self.assertEqual(result["message"], "The path does not exist in the file system")

    @patch('src.modules.identity.helpers.validates.Path')
    def test_path_is_not_directory(self, mock_path_cls):
        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = True
        mock_path_obj.is_dir.return_value = False
        mock_path_cls.return_value = mock_path_obj

        result = PathValidator.validate_and_check_next_directory("some/file.txt")
        
        self.assertTrue(result["valid_path"])
        self.assertTrue(result["path_exists"])
        self.assertEqual(result["message"], "The path exists but is not a directory")

    @patch('src.modules.identity.helpers.validates.Path')
    def test_next_directory_does_not_exist(self, mock_path_cls):
        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = True
        mock_path_obj.is_dir.return_value = True
        
        # Mocking the next path (finance)
        mock_next_path = MagicMock()
        mock_next_path.exists.return_value = False
        mock_path_obj.__truediv__.return_value = mock_next_path # overload / operator
        
        mock_path_cls.return_value = mock_path_obj

        result = PathValidator.validate_and_check_next_directory("some/path")
        
        self.assertTrue(result["valid_path"])
        self.assertTrue(result["path_exists"])
        self.assertFalse(result["next_directory_exists"])
        self.assertIn("The 'finance' directory was not found", result["message"])

    @patch('src.modules.identity.helpers.validates.Path')
    def test_success(self, mock_path_cls):
        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = True
        mock_path_obj.is_dir.return_value = True
        
        # Mocking the next path (finance)
        mock_next_path = MagicMock()
        mock_next_path.exists.return_value = True
        mock_next_path.is_dir.return_value = True
        mock_path_obj.__truediv__.return_value = mock_next_path
        
        mock_path_cls.return_value = mock_path_obj

        result = PathValidator.validate_and_check_next_directory("some/path")
        
        self.assertTrue(result["valid_path"])
        self.assertTrue(result["path_exists"])
        self.assertTrue(result["next_directory_exists"])
        self.assertEqual(result["feature"], "finance")
        self.assertIn("Success!", result["message"])

    @patch('src.modules.identity.helpers.validates.Path')
    def test_exception_handling(self, mock_path_cls):
        mock_path_cls.side_effect = Exception("Disk error")

        result = PathValidator.validate_and_check_next_directory("some/path")
        
        self.assertIn("Error processing path: Disk error", result["message"])
