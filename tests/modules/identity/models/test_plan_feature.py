"""Tests for PlanFeature model."""
import pytest
from datetime import datetime, timezone
from src.modules.identity.models.plan_feature import PlanFeature, PlanWithFeatures
from src.modules.identity.models.plan import Plan

class TestPlanFeature:
    """Test suite for PlanFeature model."""

    @pytest.fixture
    def plan_feature(self):
        """Return sample plan feature."""
        return PlanFeature(
            plan_feature_id=1,
            plan_id="plan_123",
            feature_name="whatsapp_integration",
            feature_value={"limit": 100},
            created_at=datetime.now(timezone.utc)
        )

    def test_repr(self, plan_feature):
        """Test string representation."""
        assert "PlanFeature" in repr(plan_feature)
        assert "whatsapp_integration" in repr(plan_feature)

    def test_eq(self, plan_feature):
        """Test equality."""
        other = PlanFeature(
            plan_feature_id=1,
            plan_id="plan_123",
            feature_name="whatsapp_integration",
            feature_value={"limit": 100},
            created_at=datetime.now(timezone.utc)
        )
        assert plan_feature == other
        assert plan_feature != "string"

    def test_hash(self, plan_feature):
        """Test hash."""
        assert hash(plan_feature) == hash(1)

class TestPlanWithFeatures:
    """Test suite for PlanWithFeatures model."""

    @pytest.fixture
    def plan_feature(self):
        """Return sample plan feature."""
        return PlanFeature(
            plan_feature_id=1,
            plan_id="plan_123",
            feature_name="whatsapp_integration",
            feature_value={"limit": 100},
            created_at=datetime.now(timezone.utc)
        )

    @pytest.fixture
    def plan_with_features(self, plan_feature):
        """Return sample plan with features."""
        return PlanWithFeatures(
            plan_id="plan_123",
            name="Basic Plan",
            display_name="Basic Plan",
            code="basic",
            price=10.0,
            features=[plan_feature],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

    def test_repr(self, plan_with_features):
        """Test string representation."""
        assert "PlanWithFeatures" in repr(plan_with_features)
        assert "Basic Plan" in repr(plan_with_features)

    def test_eq(self, plan_with_features):
        """Test equality."""
        other = PlanWithFeatures(
            plan_id="plan_123",
            name="Basic Plan",
            display_name="Basic Plan",
            code="basic",
            price=10.0,
            features=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        assert plan_with_features == other
        assert plan_with_features != "string"

    def test_hash(self, plan_with_features):
        """Test hash."""
        assert hash(plan_with_features) == hash("plan_123")

    def test_contains(self, plan_with_features):
        """Test contains."""
        assert "whatsapp_integration" in plan_with_features
        assert "non_existent" not in plan_with_features

    def test_get_feature_value_success(self, plan_with_features):
        """Test get_feature_value success."""
        value = plan_with_features.get_feature_value("whatsapp_integration")
        assert value == {"limit": 100}

    def test_get_feature_value_not_found(self, plan_with_features):
        """Test get_feature_value not found."""
        with pytest.raises(ValueError):
            plan_with_features.get_feature_value("non_existent")
