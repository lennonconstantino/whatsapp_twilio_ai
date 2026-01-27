import unittest
from unittest.mock import MagicMock
from src.modules.identity.services.user_service import UserService
from src.modules.identity.repositories.interfaces import IUserRepository
from src.modules.identity.dtos.user_dto import UserCreateDTO
from src.modules.identity.models.user import User, UserRole
from src.core.utils.custom_ulid import generate_ulid

class TestUserService(unittest.TestCase):

    def setUp(self):
        self.mock_repository = MagicMock(spec=IUserRepository)
        self.service = UserService(self.mock_repository)
        self.owner_id = generate_ulid()
        self.user_id = generate_ulid()

    def test_create_user_success(self):
        dto = UserCreateDTO(owner_id=self.owner_id, phone="+5511999999999")
        
        # Mocking find_by_phone to return None (no existing user)
        self.mock_repository.find_by_phone.return_value = None
        
        # Mocking create to return a User object
        expected_user = User(user_id=self.user_id, owner_id=self.owner_id, phone=dto.phone)
        self.mock_repository.create.return_value = expected_user
        
        result = self.service.create_user(dto)
        
        self.mock_repository.find_by_phone.assert_called_with(dto.phone)
        self.mock_repository.create.assert_called_once()
        self.assertEqual(result, expected_user)

    def test_create_user_phone_exists(self):
        dto = UserCreateDTO(owner_id=self.owner_id, phone="+5511999999999")
        
        # Mocking find_by_phone to return an existing user
        existing_user = User(user_id=generate_ulid(), owner_id=self.owner_id, phone=dto.phone)
        self.mock_repository.find_by_phone.return_value = existing_user
        
        with self.assertRaises(ValueError) as context:
            self.service.create_user(dto)
        
        self.assertIn(f"User with phone '{dto.phone}' already exists", str(context.exception))
        self.mock_repository.create.assert_not_called()

    def test_create_user_no_phone(self):
        dto = UserCreateDTO(owner_id=self.owner_id, phone=None)
        
        # Mocking create to return a User object
        expected_user = User(user_id=self.user_id, owner_id=self.owner_id, phone=None)
        self.mock_repository.create.return_value = expected_user
        
        result = self.service.create_user(dto)
        
        self.mock_repository.find_by_phone.assert_not_called()
        self.mock_repository.create.assert_called_once()
        self.assertEqual(result, expected_user)

    def test_get_users_by_owner(self):
        expected_users = [User(user_id=self.user_id, owner_id=self.owner_id)]
        self.mock_repository.find_by_owner.return_value = expected_users
        
        result = self.service.get_users_by_owner(self.owner_id)
        
        self.mock_repository.find_by_owner.assert_called_with(self.owner_id)
        self.assertEqual(result, expected_users)

    def test_get_active_users_by_owner(self):
        expected_users = [User(user_id=self.user_id, owner_id=self.owner_id, is_active=True)]
        self.mock_repository.find_active_by_owner.return_value = expected_users
        
        result = self.service.get_active_users_by_owner(self.owner_id)
        
        self.mock_repository.find_active_by_owner.assert_called_with(self.owner_id)
        self.assertEqual(result, expected_users)

    def test_get_user_by_phone(self):
        phone = "+5511999999999"
        expected_user = User(user_id=self.user_id, owner_id=self.owner_id, phone=phone)
        self.mock_repository.find_by_phone.return_value = expected_user
        
        result = self.service.get_user_by_phone(phone)
        
        self.mock_repository.find_by_phone.assert_called_with(phone)
        self.assertEqual(result, expected_user)

    def test_get_user_by_email(self):
        email = "test@example.com"
        expected_user = User(user_id=self.user_id, owner_id=self.owner_id, email=email)
        self.mock_repository.find_by_email.return_value = expected_user
        
        result = self.service.get_user_by_email(email)
        
        self.mock_repository.find_by_email.assert_called_with(email)
        self.assertEqual(result, expected_user)

    def test_get_user_by_auth_id(self):
        auth_id = "auth_123"
        expected_user = User(user_id=self.user_id, owner_id=self.owner_id, auth_id=auth_id)
        self.mock_repository.find_by_auth_id.return_value = expected_user
        
        result = self.service.get_user_by_auth_id(auth_id)
        
        self.mock_repository.find_by_auth_id.assert_called_with(auth_id)
        self.assertEqual(result, expected_user)

    def test_update_user(self):
        data = {"first_name": "Updated"}
        expected_user = User(user_id=self.user_id, owner_id=self.owner_id, first_name="Updated")
        self.mock_repository.update.return_value = expected_user
        
        result = self.service.update_user(self.user_id, data)
        
        self.mock_repository.update.assert_called_with(self.user_id, data, id_column="user_id")
        self.assertEqual(result, expected_user)

    def test_get_user_by_id(self):
        expected_user = User(user_id=self.user_id, owner_id=self.owner_id)
        self.mock_repository.find_by_id.return_value = expected_user
        
        result = self.service.get_user_by_id(self.user_id)
        
        self.mock_repository.find_by_id.assert_called_with(self.user_id)
        self.assertEqual(result, expected_user)

    def test_get_users_by_role(self):
        role = UserRole.ADMIN
        expected_users = [User(user_id=self.user_id, owner_id=self.owner_id, role=role)]
        self.mock_repository.find_by_role.return_value = expected_users
        
        result = self.service.get_users_by_role(self.owner_id, role)
        
        self.mock_repository.find_by_role.assert_called_with(self.owner_id, role)
        self.assertEqual(result, expected_users)

    def test_deactivate_user(self):
        expected_user = User(user_id=self.user_id, owner_id=self.owner_id, is_active=False)
        self.mock_repository.deactivate_user.return_value = expected_user
        
        result = self.service.deactivate_user(self.user_id)
        
        self.mock_repository.deactivate_user.assert_called_with(self.user_id)
        self.assertEqual(result, expected_user)

    def test_activate_user(self):
        expected_user = User(user_id=self.user_id, owner_id=self.owner_id, is_active=True)
        self.mock_repository.activate_user.return_value = expected_user
        
        result = self.service.activate_user(self.user_id)
        
        self.mock_repository.activate_user.assert_called_with(self.user_id)
        self.assertEqual(result, expected_user)
