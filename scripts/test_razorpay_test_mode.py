import asyncio
import json
from app.core.config import settings
from app.services.razorpay_service import RazorpayService

async def main():
    print("Starting Razorpay Test Mode integration check...")
    
    # 1. Load Razorpay Credentials
    key_id = settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_KEY_SECRET
    
    if not key_id or not key_secret:
        print("Error: RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be configured in your .env file.")
        print("Please check your .env file setup.")
        return

    # Mask key for secure display
    masked_key = key_id[:8] + "..." + key_id[-4:] if len(key_id) > 12 else "..."
    print(f"Loaded Key ID: {masked_key}")

    # 2. Refuse Live credentials via initialization validation
    try:
        service = RazorpayService(key_id=key_id, key_secret=key_secret)
        print("Credential prefix validation: PASSED (Test Mode prefix confirmed).")
    except ValueError as e:
        print(f"Credential prefix validation: FAILED.")
        print(f"Security Exception details: {e}")
        return

    # 3. Perform a harmless operation (order creation)
    print("Sending harmless Order Creation request to Razorpay Test API...")
    try:
        # Create a ₹1.00 order (100 paise)
        order = await service.create_order(
            amount=100,
            currency="INR",
            receipt="harmless_integration_test_receipt"
        )
        print("\n--- HARMLESS OPERATION RESULT ---")
        print(json.dumps(order, indent=2))
        print("---------------------------------")
        print("\nSuccess! Razorpay Test Mode API integration verified successfully.")
    except Exception as e:
        print(f"\nRazorpay API Call: FAILED.")
        print(f"Error details: {e}")

if __name__ == "__main__":
    asyncio.run(main())
