import unittest
from unittest.mock import MagicMock
from src.modules.identity.services.owner_service import OwnerService
from src.modules.identity.repositories.interfaces import IOwnerRepository
from src.modules.identity.dtos.owner_dto import OwnerCreateDTO
from src.modules.identity.models.owner import Owner
from src.core.utils.custom_ulid import generate_ulid

class TestOwnerService(unittest.TestCase):

    def setUp(self):
        self.mock_repository = MagicMock(spec=IOwnerRepository)
        self.service = OwnerService(self.mock_repository)
        self.owner_id = generate_ulid()

    def test_create_owner_success(self):
        dto = OwnerCreateDTO(name="Test Org", email="test@example.com")
        
        # Mocking find_by_email to return None (no existing owner)
        self.mock_repository.find_by_email.return_value = None
        
        # Mocking create_owner to return an Owner object
        expected_owner = Owner(owner_id=self.owner_id, name=dto.name, email=dto.email)
        self.mock_repository.create_owner.return_value = expected_owner
        
        result = self.service.create_owner(dto)
        
        self.mock_repository.find_by_email.assert_called_with(dto.email)
        self.mock_repository.create_owner.assert_called_with(dto.name, dto.email)
        self.assertEqual(result, expected_owner)

    def test_create_owner_email_exists(self):
        dto = OwnerCreateDTO(name="Test Org", email="test@example.com")
        
        # Mocking find_by_email to return an existing owner
        existing_owner = Owner(owner_id=generate_ulid(), name="Existing", email=dto.email)
        self.mock_repository.find_by_email.return_value = existing_owner
        
        with self.assertRaises(ValueError) as context:
            self.service.create_owner(dto)
        
        self.assertIn(f"Owner with email '{dto.email}' already exists", str(context.exception))
        self.mock_repository.create_owner.assert_not_called()

    def test_get_owner_by_email(self):
        email = "test@example.com"
        expected_owner = Owner(owner_id=self.owner_id, email=email, name="Test Owner")
        self.mock_repository.find_by_email.return_value = expected_owner
        
        result = self.service.get_owner_by_email(email)
        
        self.mock_repository.find_by_email.assert_called_with(email)
        self.assertEqual(result, expected_owner)

    def test_get_active_owners(self):
        expected_owners = [Owner(owner_id=self.owner_id, is_active=True, name="Test Owner", email="test@example.com")]
        self.mock_repository.find_active_owners.return_value = expected_owners
        
        result = self.service.get_active_owners()
        
        self.mock_repository.find_active_owners.assert_called_once()
        self.assertEqual(result, expected_owners)

    def test_get_owner_by_id(self):
        expected_owner = Owner(owner_id=self.owner_id, name="Test Owner", email="test@example.com")
        self.mock_repository.find_by_id.return_value = expected_owner
        
        result = self.service.get_owner_by_id(self.owner_id)
        
        self.mock_repository.find_by_id.assert_called_with(self.owner_id)
        self.assertEqual(result, expected_owner)

    def test_deactivate_owner(self):
        expected_owner = Owner(owner_id=self.owner_id, is_active=False, name="Test Owner", email="test@example.com")
        self.mock_repository.deactivate_owner.return_value = expected_owner
        
        result = self.service.deactivate_owner(self.owner_id)
        
        self.mock_repository.deactivate_owner.assert_called_with(self.owner_id)
        self.assertEqual(result, expected_owner)

    def test_activate_owner(self):
        expected_owner = Owner(owner_id=self.owner_id, is_active=True, name="Test Owner", email="test@example.com")
        self.mock_repository.activate_owner.return_value = expected_owner
        
        result = self.service.activate_owner(self.owner_id)
        
        self.mock_repository.activate_owner.assert_called_with(self.owner_id)
        self.assertEqual(result, expected_owner)

    def test_delete_owner(self):
        self.mock_repository.delete.return_value = True
        
        result = self.service.delete_owner(self.owner_id)
        
        self.mock_repository.delete.assert_called_with(self.owner_id, id_column="owner_id")
        self.assertTrue(result)
