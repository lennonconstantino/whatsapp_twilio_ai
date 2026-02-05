
import pytest
from datetime import datetime, date
from pydantic import ValidationError
from src.modules.ai.engines.lchain.feature.relationships.models.models import (
    Person, PersonCreate, PersonUpdate,
    Interaction, InteractionCreate, InteractionUpdate,
    Reminder, ReminderCreate, ReminderUpdate,
    validate_date, validate_date_only
)

class TestRelationshipValidators:
    def test_validate_date(self):
        # datetime input
        dt = datetime(2023, 1, 1, 12, 0, 0)
        assert validate_date(dt) == dt

        # date input
        d = date(2023, 1, 1)
        expected = datetime(2023, 1, 1, 0, 0, 0)
        assert validate_date(d) == expected

        # str iso input
        assert validate_date("2023-01-01T12:00:00") == dt

        # str format inputs
        assert validate_date("2023-01-01") == expected
        assert validate_date("2023-01-01 12:00:00") == dt

        # invalid input
        with pytest.raises(ValueError):
            validate_date("invalid")

    def test_validate_date_only(self):
        # date input
        d = date(2023, 1, 1)
        assert validate_date_only(d) == d

        # datetime input
        dt = datetime(2023, 1, 1, 12, 0, 0)
        assert validate_date_only(dt) == d

        # str inputs
        assert validate_date_only("2023-01-01") == d
        assert validate_date_only("2023-01-01T12:00:00") == d

        # invalid input
        with pytest.raises(ValueError):
            validate_date_only("invalid")

class TestPersonModels:
    def test_person_create(self):
        p = PersonCreate(
            first_name="John",
            last_name="Doe",
            phone="+123",
            birthday="2000-01-01"
        )
        assert p.birthday == date(2000, 1, 1)
        assert p.first_name == "John"

    def test_person_create_invalid_date(self):
        with pytest.raises(ValidationError):
            PersonCreate(
                first_name="John",
                last_name="Doe",
                phone="+123",
                birthday="invalid"
            )

    def test_person_update(self):
        p = PersonUpdate(first_name="Jane")
        assert p.first_name == "Jane"
        assert p.last_name is None

    def test_person_from_attributes(self):
        data = {
            "id": 1,
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+123",
            "tags": "friend",
            "birthday": date(2000, 1, 1),
            "city": "NY",
            "notes": "note"
        }
        # Simulate object
        class MockObj:
            def __init__(self, **kwargs):
                for k,v in kwargs.items():
                    setattr(self, k, v)
        
        obj = MockObj(**data)
        p = Person.model_validate(obj)
        assert p.id == 1
        assert p.first_name == "John"

class TestInteractionModels:
    def test_interaction_create(self):
        i = InteractionCreate(
            person_id=1,
            date="2023-01-01 10:00:00",
            channel="whatsapp",
            type="text",
            summary="chat"
        )
        assert i.date == datetime(2023, 1, 1, 10, 0, 0)
        assert i.person_id == 1

    def test_interaction_invalid_date(self):
        with pytest.raises(ValidationError):
            InteractionCreate(
                person_id=1,
                date="invalid",
                channel="whatsapp",
                type="text"
            )

class TestReminderModels:
    def test_reminder_create(self):
        r = ReminderCreate(
            person_id=1,
            due_date="2023-01-01 09:00:00",
            reason="call"
        )
        assert r.due_date == datetime(2023, 1, 1, 9, 0, 0)
        assert r.status == "open"

