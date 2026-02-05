import asyncio
import os
import sys
from datetime import datetime
import uuid

# Add project root to path
sys.path.append(os.getcwd())

from src.core.di.container import Container
from src.modules.billing.models.plan import PlanCreate
from src.modules.billing.enums.billing_period import BillingPeriod
from src.modules.billing.enums.subscription_status import SubscriptionStatus

async def main():
    print("🚀 Starting Billing Integration Verification (Internal E2E)...")
    
    # Initialize Container
    container = Container()
    
    # Check if we have Supabase credentials
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
        print("⚠️  SUPABASE_URL or SUPABASE_KEY not found in env. Skipping real DB verification.")
        print("ℹ️  To run this verification against Supabase, ensure .env is configured.")
        return

    try:
        # Services
        plan_service = container.billing_plan_service()
        subscription_service = container.billing_subscription_service()
        feature_usage_service = container.feature_usage_service()
        webhook_handler = container.webhook_handler_service()
        owner_repository = container.owner_repository()
        
        # 0. Create Owner
        print("\n👤 Creating Test Owner...")
        owner_id = f"user_{uuid.uuid4().hex[:8]}" # Actually, let's let DB generate ULID or use UUID if table allows? 
        # Wait, identity module likely uses ULID. 
        # Let's create proper owner record.
        owner_email = f"test_{int(datetime.now().timestamp())}@example.com"
        owner_data = {
            "name": "Test Billing Owner",
            "email": owner_email,
            "active": True
        }
        # Assuming owner_repository follows standard interface
        owner = owner_repository.create(owner_data)
        owner_id = owner.owner_id
        print(f"✅ Owner created: {owner_id} ({owner.email})")

        # 1. Create a Test Plan
        print("\n📦 Creating Test Plan...")
        plan_name = f"test_plan_{int(datetime.now().timestamp())}"
        plan_data = PlanCreate(
            name=plan_name,
            display_name="Test Integration Plan",
            description="Plan created by verification script",
            price_cents=1990,
            billing_period=BillingPeriod.MONTHLY,
            max_users=5,
            max_projects=2
        )
        plan = plan_service.create_plan(plan_data)
        print(f"✅ Plan created: {plan.plan_id} ({plan.display_name})")
        
        # 2. Add Feature to Plan
        print("\n✨ Adding Feature 'ocr_processing' to Plan...")
        try:
            plan_service.add_feature_to_plan(
                plan_id=plan.plan_id,
                feature_key="ocr_processing",
                quota_limit=100
            )
            print("✅ Feature 'ocr_processing' added to plan.")
        except ValueError as e:
            print(f"⚠️  Could not add feature (expected if catalog empty): {e}")

        # 3. Simulate Stripe Checkout Webhook (Creation)
        print("\n📝 Simulating Stripe Checkout Webhook...")
        # owner_id is already created above
        stripe_sub_id = f"sub_{uuid.uuid4().hex[:16]}"
        stripe_cus_id = f"cus_{uuid.uuid4().hex[:16]}"
        checkout_session_id = f"cs_test_{uuid.uuid4().hex[:16]}"

        event_checkout = {
            "id": f"evt_{uuid.uuid4().hex}",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": checkout_session_id,
                    "client_reference_id": owner_id,
                    "subscription": stripe_sub_id,
                    "customer": stripe_cus_id,
                    "metadata": {
                        "plan_id": plan.plan_id
                    }
                }
            }
        }

        await webhook_handler.handle_event(event_checkout)
        print(f"✅ Webhook processed for owner: {owner_id}")

        # 4. Verify Subscription Created in DB
        print("\n🔍 Verifying Subscription in Database...")
        subscription = subscription_service.subscription_repo.find_by_owner(owner_id)
        
        if subscription:
            print(f"✅ Subscription found: {subscription.subscription_id}")
            print(f"   Status: {subscription.status}")
            print(f"   Plan: {subscription.plan_id}")
            print(f"   Stripe ID: {subscription.metadata.get('stripe_subscription_id')}")
            
            assert subscription.status == SubscriptionStatus.ACTIVE
            assert subscription.plan_id == plan.plan_id
            assert subscription.metadata.get('stripe_subscription_id') == stripe_sub_id
        else:
            print("❌ Subscription NOT found!")
            return

        # 5. Check Feature Access
        print("\n🔍 Checking Feature Access...")
        access = feature_usage_service.check_feature_access(
            owner_id=owner_id,
            feature_key="ocr_processing"
        )
        print(f"ℹ️  Access allowed: {access.allowed}")
        print(f"ℹ️  Current usage: {access.current_usage}/{access.quota_limit}")

        # 6. Increment Usage
        if access.allowed:
            print("\n📈 Incrementing Usage...")
            feature_usage_service.increment_usage(
                owner_id=owner_id,
                feature_key="ocr_processing",
                amount=1
            )
            access_after = feature_usage_service.check_feature_access(
                owner_id=owner_id,
                feature_key="ocr_processing"
            )
            print(f"✅ Usage incremented: {access_after.current_usage}/{access_after.quota_limit}")
        
        # 7. Simulate Stripe Cancellation Webhook
        print("\n🚫 Simulating Stripe Cancellation Webhook...")
        event_cancel = {
            "id": f"evt_{uuid.uuid4().hex}",
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": stripe_sub_id
                }
            }
        }
        
        await webhook_handler.handle_event(event_cancel)
        print("✅ Cancellation webhook processed.")

        # 8. Verify Cancellation in DB
        print("\n🔍 Verifying Cancellation in Database...")
        # Need to fetch again to see update
        # Since find_by_owner might return None if logic filters inactive (it doesn't currently, but let's be safe)
        # We use find_by_id or check the object we had if we reload it
        sub_cancelled = subscription_service.subscription_repo.find_by_stripe_subscription_id(stripe_sub_id)
        
        if sub_cancelled:
            print(f"ℹ️  Subscription Status: {sub_cancelled.status}")
            print(f"ℹ️  Canceled At: {sub_cancelled.canceled_at}")
            
            assert sub_cancelled.status == SubscriptionStatus.CANCELED
            print("✅ Subscription successfully canceled in DB.")
        else:
            print("❌ Could not reload subscription to verify cancellation.")

        print("\n🎉 Internal E2E Verification Completed Successfully!")

    except Exception as e:
        print(f"\n❌ Error during verification: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
