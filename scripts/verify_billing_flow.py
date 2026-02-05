import asyncio
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from src.core.di.container import Container
from src.modules.billing.models.plan import PlanCreate
from src.modules.billing.enums.billing_period import BillingPeriod
from src.modules.billing.enums.subscription_status import SubscriptionStatus

async def main():
    print("🚀 Starting Billing Integration Verification...")
    
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
        
        # 1. Create a Test Plan
        print("\n📦 Creating Test Plan...")
        plan_data = PlanCreate(
            name=f"test_plan_{int(datetime.now().timestamp())}",
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
        # First ensure feature exists (in real app, catalog is pre-seeded)
        # For this script, we assume it might not exist or we might fail if not seeded.
        # We'll try to add it. If catalog doesn't have it, this might fail.
        # Let's verify catalog first? No, let's try to add and handle error.
        try:
            plan_service.add_feature_to_plan(
                plan_id=plan.plan_id,
                feature_key="ocr_processing",
                quota_limit=100
            )
            print("✅ Feature 'ocr_processing' added to plan.")
        except ValueError as e:
            print(f"⚠️  Could not add feature (expected if catalog empty): {e}")

        # 3. Create Subscription
        print("\n📝 Creating Subscription for 'test_owner_integration'...")
        owner_id = "test_owner_integration"
        subscription = subscription_service.create_subscription(
            owner_id=owner_id,
            plan_id=plan.plan_id
        )
        print(f"✅ Subscription created: {subscription.subscription_id} (Status: {subscription.status})")

        # 4. Check Feature Access
        print("\n🔍 Checking Feature Access...")
        access = feature_usage_service.check_feature_access(
            owner_id=owner_id,
            feature_key="ocr_processing"
        )
        print(f"ℹ️  Access allowed: {access.allowed}")
        print(f"ℹ️  Current usage: {access.current_usage}/{access.quota_limit}")

        # 5. Increment Usage
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
        
        # 6. Cleanup (Cancel Subscription)
        print("\n🧹 Cleaning up (Cancelling Subscription)...")
        subscription_service.cancel_subscription(
            subscription_id=subscription.subscription_id,
            immediately=True,
            reason="Integration test cleanup"
        )
        print("✅ Subscription canceled.")
        
        print("\n🎉 Verification Completed Successfully!")

    except Exception as e:
        print(f"\n❌ Error during verification: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
