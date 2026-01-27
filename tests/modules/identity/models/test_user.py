from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.modules.identity.models.owner import Owner
from src.modules.identity.models.user import User, UserRole, UserWithOwner


class TestUserModel:
    def test_user_creation_valid(self):
        user = User(
            user_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            email="test@example.com",
            role=UserRole.ADMIN,
        )
        assert user.user_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        assert user.owner_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        assert user.email == "test@example.com"
        assert user.role == UserRole.ADMIN

    def test_user_owner_id_validation(self):
        # Valid owner_id
        user = User(owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV")
        assert user.owner_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"

        # Invalid owner_id format
        with pytest.raises(ValidationError) as exc:
            User(owner_id="invalid-ulid")
        assert "Invalid ULID format" in str(exc.value)

        # Missing owner_id - handled by Pydantic MissingError, but let's check empty string if validation logic catches it
        with pytest.raises(ValidationError) as exc:
            User(owner_id="")
        assert "owner_id is required" in str(exc.value)

    def test_user_repr(self):
        user = User(
            user_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            email="test@example.com",
        )
        repr_str = repr(user)
        assert "User(id=01ARZ3NDEKTSV4RRFFQ69G5FAV" in repr_str
        assert "email=test@example.com" in repr_str

    def test_user_equality(self):
        user1 = User(
            user_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            email="test@example.com",
        )
        user2 = User(
            user_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            email="test@example.com",
        )
        user3 = User(
            user_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            email="other@example.com",
        )

        assert user1 == user2
        assert user1 != user3
        assert user1 != "some string"

    def test_user_hash(self):
        user1 = User(
            user_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            email="test@example.com",
        )
        user2 = User(
            user_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            email="test@example.com",
        )

        assert hash(user1) == hash(user2)


class TestUserWithOwnerModel:
    def test_user_with_owner_creation(self):
        owner = Owner(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            name="Test Org",
            document="123",
            email="org@test.com",
        )
        user = UserWithOwner(
            user_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            email="test@example.com",
            owner=owner,
        )
        assert user.owner == owner

    def test_user_with_owner_repr(self):
        owner = Owner(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            name="Test Org",
            document="123",
            email="org@test.com",
        )
        user = UserWithOwner(
            user_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            email="test@example.com",
            owner=owner,
        )
        repr_str = repr(user)
        assert "UserWithOwner" in repr_str
        assert "owner=" in repr_str

    def test_user_with_owner_equality(self):
        owner = Owner(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            name="Test Org",
            document="123",
            email="org@test.com",
        )
        user1 = UserWithOwner(
            user_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            email="test@example.com",
            owner=owner,
        )
        user2 = UserWithOwner(
            user_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            email="test@example.com",
            owner=owner,
        )

        assert user1 == user2
        assert user1 != "some string"
