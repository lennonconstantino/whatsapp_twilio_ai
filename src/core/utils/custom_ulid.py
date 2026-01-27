"""
ULID utilities for Python.

Provides functions for ULID generation, validation, and manipulation.
Based on: https://github.com/ulid/spec
"""

import re
from datetime import datetime, timezone
from typing import Optional

from ulid import ULID

# Crockford's Base32 alphabet (excludes I, L, O, U to avoid confusion)
ENCODING = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
ENCODING_LEN = len(ENCODING)

# ULID format constants
ULID_LENGTH = 26
TIMESTAMP_LENGTH = 10
RANDOMNESS_LENGTH = 16

# Regex for validation
ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$", re.IGNORECASE)


def is_valid_ulid(ulid: str) -> bool:
    """
    Validate ULID format.

    Args:
        ulid: ULID string to validate

    Returns:
        True if valid ULID format, False otherwise

    Examples:
        >>> is_valid_ulid('01ARZ3NDEKTSV4RRFFQ69G5FAV')
        True
        >>> is_valid_ulid('invalid')
        False
        >>> is_valid_ulid('01ARZ3NDEKTSV4RRFFQ69G5FAI')  # contains 'I'
        False
    """
    if not isinstance(ulid, str):
        return False

    if len(ulid) != ULID_LENGTH:
        return False

    # Check if all characters are in Crockford's Base32 alphabet
    return ULID_PATTERN.match(ulid) is not None


def validate_ulid_field(v: Optional[str]) -> Optional[str]:
    """
    Validate a ULID field for Pydantic models.

    Args:
        v: Value to validate

    Returns:
        Uppercased ULID string or None

    Raises:
        ValueError: If value is present but not a valid ULID
    """
    if v is None:
        return None

    if not is_valid_ulid(v):
        raise ValueError(f"Invalid ULID format: {v}")

    return v.upper()


def generate_ulid() -> str:
    """
    Generate a new ULID using python-ulid library.

    Returns:
        26-character ULID string
    """
    return str(ULID())


def ulid_to_timestamp(ulid: str) -> datetime:
    """
    Extract timestamp from ULID using python-ulid library.

    Args:
        ulid: ULID string

    Returns:
        Datetime object in UTC timezone

    Raises:
        ValueError: If ULID format is invalid
    """
    if not is_valid_ulid(ulid):
        raise ValueError(f"Invalid ULID format: {ulid}")

    try:
        ulid_obj = ULID.from_str(ulid)
        return ulid_obj.timestamp().datetime
    except ValueError as e:
        raise ValueError(f"Invalid ULID format: {ulid}") from e


def ulid_to_unix_ms(ulid: str) -> int:
    """
    Extract Unix timestamp in milliseconds from ULID.

    Args:
        ulid: ULID string

    Returns:
        Unix timestamp in milliseconds
    """
    if not is_valid_ulid(ulid):
        raise ValueError(f"Invalid ULID format: {ulid}")

    try:
        ulid_obj = ULID.from_str(ulid)
        return int(ulid_obj.timestamp().timestamp * 1000)
    except ValueError as e:
        raise ValueError(f"Invalid ULID format: {ulid}") from e
