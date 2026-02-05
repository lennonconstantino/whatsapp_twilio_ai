import pytest
from datetime import datetime, timezone
from src.core.utils.custom_ulid import (
    generate_ulid,
    is_valid_ulid,
    validate_ulid_field,
    ulid_to_timestamp,
    ulid_to_unix_ms,
    ULID_LENGTH
)

class TestCustomUlid:
    def test_generate_ulid(self):
        ulid = generate_ulid()
        assert isinstance(ulid, str)
        assert len(ulid) == ULID_LENGTH
        assert is_valid_ulid(ulid)

    def test_is_valid_ulid(self):
        valid_ulid = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        assert is_valid_ulid(valid_ulid) is True

        # Invalid length
        assert is_valid_ulid("123") is False
        
        # Invalid characters (I, L, O, U are excluded from Crockford Base32)
        assert is_valid_ulid("01ARZ3NDEKTSV4RRFFQ69G5FAI") is False
        
        # Not a string
        assert is_valid_ulid(123) is False

    def test_validate_ulid_field(self):
        valid_ulid = "01arz3ndektsv4rrffq69g5fav"
        expected = valid_ulid.upper()
        
        assert validate_ulid_field(valid_ulid) == expected
        assert validate_ulid_field(None) is None
        
        with pytest.raises(ValueError):
            validate_ulid_field("invalid-ulid")

    def test_ulid_to_timestamp(self):
        # 01HDC2W829N... -> 2023-10-25...
        ulid = "01HDC2W829N400000000000000"
        ts = ulid_to_timestamp(ulid)
        
        assert isinstance(ts, datetime)
        assert ts.year == 2023
        
        with pytest.raises(ValueError):
            ulid_to_timestamp("invalid")

    def test_ulid_to_unix_ms(self):
        ulid = "01HDC2W829N400000000000000"
        ms = ulid_to_unix_ms(ulid)
        
        assert isinstance(ms, int)
        assert ms > 0
        
        with pytest.raises(ValueError):
            ulid_to_unix_ms("invalid")
