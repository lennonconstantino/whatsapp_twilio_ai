from enum import Enum


class FeatureType(str, Enum):
    """Types of features in the catalog."""
    BOOLEAN = "boolean"  # Simple on/off
    QUOTA = "quota"      # Countable with limit
    TIER = "tier"        # Bronze/Silver/Gold
    CONFIG = "config"    # Complex JSON config

    def __repr__(self) -> str:
        return f"FeatureType.{self.name}"
