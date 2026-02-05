import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta

from src.modules.billing.services.feature_usage_service import FeatureUsageService, QuotaExceededError, FeatureAccessResult
from src.modules.billing.services.features_catalog_service import FeaturesCatalogService
from src.modules.billing.models.feature import Feature, FeatureType
from src.modules.billing.models.feature_usage import FeatureUsage
from src.modules.billing.models.plan_feature import PlanFeature

@pytest.fixture
def mock_usage_repo():
    return Mock()

@pytest.fixture
def mock_catalog_service():
    service = Mock(spec=FeaturesCatalogService)
    # Mock internal repo access if needed, or just mock methods
    return service

@pytest.fixture
def mock_cache():
    mock = Mock()
    mock.get.return_value = None  # Default cache miss
    return mock

@pytest.fixture
def feature_usage_service(mock_usage_repo, mock_catalog_service, mock_cache):
    return FeatureUsageService(
        usage_repository=mock_usage_repo,
        catalog_service=mock_catalog_service,
        cache_service=mock_cache
    )

def test_initialize_features_for_tenant(feature_usage_service, mock_usage_repo):
    # Arrange
    owner_id = "owner_123"
    plan_features = [
        PlanFeature(
            plan_feature_id=1,
            plan_id="plan_1",
            feature_id="feat_1",
            is_enabled=True,
            quota_limit=100,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        PlanFeature(
            plan_feature_id=2,
            plan_id="plan_1",
            feature_id="feat_2",
            is_enabled=False, # Should be skipped
            quota_limit=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    ]
    
    mock_usage_repo.upsert.return_value = FeatureUsage(
        usage_id="usage_1",
        owner_id=owner_id,
        feature_id="feat_1",
        current_usage=0,
        quota_limit=100,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    # Act
    result = feature_usage_service.initialize_features_for_tenant(owner_id, plan_features)

    # Assert
    assert len(result) == 1
    assert result[0].feature_id == "feat_1"
    mock_usage_repo.upsert.assert_called_once()
    call_args = mock_usage_repo.upsert.call_args[0][0]
    assert call_args["owner_id"] == owner_id
    assert call_args["feature_id"] == "feat_1"
    assert call_args["quota_limit"] == 100

def test_check_feature_access_allowed(feature_usage_service, mock_usage_repo, mock_catalog_service):
    # Arrange
    owner_id = "owner_123"
    feature_key = "test_feature"
    feature = Feature(
        feature_id="feat_1",
        feature_key=feature_key,
        name="Test Feature",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    usage = FeatureUsage(
        usage_id="usage_1",
        owner_id=owner_id,
        feature_id="feat_1",
        current_usage=50,
        quota_limit=100,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    mock_catalog_service.get_feature_by_key.return_value = feature
    mock_usage_repo.find_by_owner_and_feature.return_value = usage

    # Act
    result = feature_usage_service.check_feature_access(owner_id, feature_key)

    # Assert
    assert result.allowed is True
    assert result.percentage_used == 50.0
    assert result.reason == "OK"

def test_check_feature_access_quota_exceeded(feature_usage_service, mock_usage_repo, mock_catalog_service):
    # Arrange
    owner_id = "owner_123"
    feature_key = "test_feature"
    feature = Feature(
        feature_id="feat_1",
        feature_key=feature_key,
        name="Test Feature",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    usage = FeatureUsage(
        usage_id="usage_1",
        owner_id=owner_id,
        feature_id="feat_1",
        current_usage=100,
        quota_limit=100,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    mock_catalog_service.get_feature_by_key.return_value = feature
    mock_usage_repo.find_by_owner_and_feature.return_value = usage

    # Act
    result = feature_usage_service.check_feature_access(owner_id, feature_key)

    # Assert
    assert result.allowed is False
    assert result.reason == "Quota exceeded"
    assert result.percentage_used == 100.0

def test_increment_usage_success(feature_usage_service, mock_usage_repo, mock_catalog_service):
    # Arrange
    owner_id = "owner_123"
    feature_key = "test_feature"
    feature = Feature(
        feature_id="feat_1",
        feature_key=feature_key,
        name="Test Feature",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    usage = FeatureUsage(
        usage_id="usage_1",
        owner_id=owner_id,
        feature_id="feat_1",
        current_usage=10,
        quota_limit=100,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    mock_catalog_service.get_feature_by_key.return_value = feature
    mock_usage_repo.find_by_owner_and_feature.return_value = usage # For check_access
    mock_usage_repo.increment.return_value = usage # Simplified return

    # Act
    feature_usage_service.increment_usage(owner_id, feature_key, amount=1)

    # Assert
    mock_usage_repo.increment.assert_called_once_with(
        owner_id=owner_id,
        feature_id="feat_1",
        amount=1
    )
