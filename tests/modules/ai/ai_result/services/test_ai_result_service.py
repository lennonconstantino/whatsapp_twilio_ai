import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.modules.ai.ai_result.services.ai_result_service import AIResultService
from src.modules.ai.ai_result.repositories.ai_result_repository import AIResultRepository
from src.modules.ai.ai_result.models.ai_result import AIResult
from src.modules.ai.ai_result.enums.ai_result_type import AIResultType

@pytest.fixture
def mock_repo():
    return Mock(spec=AIResultRepository)

@pytest.fixture
def service(mock_repo):
    return AIResultService(mock_repo)

@pytest.fixture
def sample_result():
    return AIResult(
        ai_result_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        msg_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        feature_id="01ARZ3NDEKTSV4RRFFQ69G5FAV", # Changed from 1 to ULID
        result_json={"status": "success", "processing_time": 0.5},
        result_type=AIResultType.AGENT_LOG,
        processed_at=datetime.now()
    )

class TestAIResultService:

    def test_create_result_success(self, service, mock_repo, sample_result):
        """Test successful creation of AI result."""
        mock_repo.create_result.return_value = sample_result
        
        result = service.create_result(
            msg_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            feature_id="01ARZ3NDEKTSV4RRFFQ69G5FAV", # Changed from 1 to ULID
            result_json={"data": "test"},
            result_type=AIResultType.TOOL
        )
        
        assert result == sample_result
        mock_repo.create_result.assert_called_once_with(
            msg_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            feature_id="01ARZ3NDEKTSV4RRFFQ69G5FAV", # Changed from 1 to ULID
            result_json={"data": "test"},
            result_type=AIResultType.TOOL,
            correlation_id=None
        )

    def test_create_result_error(self, service, mock_repo):
        """Test error handling during result creation."""
        mock_repo.create_result.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            service.create_result(
                msg_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                feature_id="01ARZ3NDEKTSV4RRFFQ69G5FAV", # Changed from 1 to ULID
                result_json={}
            )

    def test_get_results_by_message(self, service, mock_repo, sample_result):
        """Test retrieving results by message ID."""
        mock_repo.find_by_message.return_value = [sample_result]
        
        results = service.get_results_by_message("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert results == [sample_result]
        mock_repo.find_by_message.assert_called_once_with("01ARZ3NDEKTSV4RRFFQ69G5FAV", 100)

    def test_analyze_feature_performance_no_results(self, service, mock_repo):
        """Test analysis when no results are found."""
        mock_repo.find_recent_by_feature.return_value = []
        
        metrics = service.analyze_feature_performance(feature_id="01ARZ3NDEKTSV4RRFFQ69G5FAV") # Changed from 1 to ULID
        
        assert metrics["total_results"] == 0
        assert metrics["message"] == "No results found"

    def test_analyze_feature_performance_metrics(self, service, mock_repo):
        """Test calculation of performance metrics."""
        now = datetime.now()
        results = [
            AIResult(
                ai_result_id="01ARZ3NDEKTSV4RRFFQ69G5FA1", msg_id="01ARZ3NDEKTSV4RRFFQ69G5FA1", feature_id="01ARZ3NDEKTSV4RRFFQ69G5FAV", result_type=AIResultType.AGENT_LOG, processed_at=now,
                result_json={"status": "success", "processing_time": 0.1}
            ),
            AIResult(
                ai_result_id="01ARZ3NDEKTSV4RRFFQ69G5FA2", msg_id="01ARZ3NDEKTSV4RRFFQ69G5FA2", feature_id="01ARZ3NDEKTSV4RRFFQ69G5FAV", result_type=AIResultType.AGENT_LOG, processed_at=now - timedelta(seconds=1),
                result_json={"status": "success", "processing_time": 0.3}
            ),
            AIResult(
                ai_result_id="01ARZ3NDEKTSV4RRFFQ69G5FA3", msg_id="01ARZ3NDEKTSV4RRFFQ69G5FA3", feature_id="01ARZ3NDEKTSV4RRFFQ69G5FAV", result_type=AIResultType.AGENT_LOG, processed_at=now - timedelta(seconds=2),
                result_json={"status": "error", "processing_time": 0.5}
            )
        ]
        mock_repo.find_recent_by_feature.return_value = results
        
        metrics = service.analyze_feature_performance(feature_id="01ARZ3NDEKTSV4RRFFQ69G5FAV") # Changed from 1 to ULID
        
        assert metrics["total_results"] == 3
        assert metrics["avg_processing_time"] == pytest.approx(0.3)
        assert metrics["min_processing_time"] == 0.1
        assert metrics["max_processing_time"] == 0.5
        assert metrics["success_rate"] == pytest.approx(2/3)
        assert metrics["error_rate"] == pytest.approx(1/3)

    def test_delete_old_results(self, service):
        """Test delete_old_results (currently a placeholder)."""
        count = service.delete_old_results(days=30)
        assert count == 0
