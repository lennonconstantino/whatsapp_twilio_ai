"""
[DEPRECATED] This module is deprecated.
Use src.core.database.supabase_repository instead.
This file is kept for backward compatibility.
"""

import warnings

from src.core.database.supabase_repository import SupabaseRepository

# Emit warning when imported
warnings.warn(
    "src.core.database.base_repository is deprecated. Use src.core.database.supabase_repository instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export SupabaseRepository as BaseRepository for compatibility
BaseRepository = SupabaseRepository
