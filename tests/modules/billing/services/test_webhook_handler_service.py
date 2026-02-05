import pytest
from unittest.mock import AsyncMock, Mock, patch
from src.modules.billing.services.webhook_handler_service import WebhookHandlerService
from src.modules.billing.enums.subscription_status import SubscriptionStatus

@pytest.fixture
def mock_subscription_service():
    service = Mock()
    service.subscription_repo = Mock()
    return service

@pytest.fixture
def mock_plan_service():
    return Mock()

@pytest.fixture
def webhook_handler(mock_subscription_service, mock_plan_service):
    return WebhookHandlerService(mock_subscription_service, mock_plan_service)

@pytest.mark.asyncio
async def test_handle_checkout_session_completed_creates_subscription(webhook_handler, mock_subscription_service):
    # Arrange
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "client_reference_id": "user_123",
                "subscription": "sub_123",
                "customer": "cus_123",
                "metadata": {
                    "plan_id": "plan_basic"
                }
            }
        }
    }
    
    mock_subscription_service.subscription_repo.find_by_owner.return_value = None

    # Act
    await webhook_handler.handle_event(event)

    # Assert
    mock_subscription_service.create_subscription.assert_called_once_with(
        owner_id="user_123",
        plan_id="plan_basic",
        metadata={
            "stripe_subscription_id": "sub_123",
            "stripe_customer_id": "cus_123",
            "checkout_session_id": "cs_test_123"
        }
    )

@pytest.mark.asyncio
async def test_handle_invoice_payment_succeeded_updates_status(webhook_handler, mock_subscription_service):
    # Arrange
    event = {
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {
                "subscription": "sub_123"
            }
        }
    }
    
    mock_sub = Mock()
    mock_sub.subscription_id = "internal_sub_123"
    mock_sub.status = SubscriptionStatus.PAST_DUE
    
    mock_subscription_service.subscription_repo.find_by_stripe_subscription_id.return_value = mock_sub

    # Act
    await webhook_handler.handle_event(event)

    # Assert
    mock_subscription_service.subscription_repo.update.assert_called_once_with(
        "internal_sub_123",
        {"status": SubscriptionStatus.ACTIVE}
    )

@pytest.mark.asyncio
async def test_handle_subscription_deleted_cancels_subscription(webhook_handler, mock_subscription_service):
    # Arrange
    event = {
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_123"
            }
        }
    }
    
    mock_sub = Mock()
    mock_sub.subscription_id = "internal_sub_123"
    
    mock_subscription_service.subscription_repo.find_by_stripe_subscription_id.return_value = mock_sub

    # Act
    await webhook_handler.handle_event(event)

    # Assert
    mock_subscription_service.cancel_subscription.assert_called_once_with(
        subscription_id="internal_sub_123",
        immediately=True,
        reason="Canceled via Stripe",
        triggered_by="stripe"
    )
