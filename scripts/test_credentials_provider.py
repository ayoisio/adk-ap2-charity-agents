"""
Test script for the Credentials Provider Agent.
Uses mock agent to bypass confirmation for automated testing.
"""

import asyncio
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

from datetime import datetime, timedelta, timezone
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai.types import Content, Part
from charity_advisor.credentials_provider.agent_mock import credentials_provider_mock  # ← Use mock


async def test_credentials_provider():
    """Test the Credentials Provider with simulated Merchant Agent data."""

    session_service = InMemorySessionService()
    app_name = "charity_advisor"
    user_id = "test_user"
    session_id = "test_session"

    timestamp = datetime.now(timezone.utc)
    cart_expiry = timestamp + timedelta(minutes=15)

    cart_mandate = {
        "contents": {
            "id": "cart_test123",
            "cart_expiry": cart_expiry.isoformat(),
            "merchant_name": "Room to Read",
            "user_cart_confirmation_required": False,
            "payment_request": {
                "method_data": [{
                    "supported_methods": ["card", "bank_transfer"],
                    "data": {
                        "supported_networks": ["visa", "mastercard", "amex"],
                        "supported_types": ["debit", "credit"]
                    }
                }],
                "details": {
                    "display_items": [{
                        "label": "Donation to Room to Read",
                        "amount": {
                            "currency": "USD",
                            "value": "50.00"
                        }
                    }],
                    "total": {
                        "label": "Total Donation",
                        "amount": {
                            "currency": "USD",
                            "value": "50.00"
                        }
                    }
                },
                "options": {
                    "request_payer_name": False,
                    "request_payer_email": False,
                    "request_payer_phone": False,
                    "request_shipping": False
                }
            }
        },
        "merchant_authorization": "SIG_test_signature",
        "timestamp": timestamp.isoformat()
    }

    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state={"cart_mandate": cart_mandate}
    )

    print("=" * 70)
    print("CREDENTIALS PROVIDER TEST (MOCK - NO CONFIRMATION)")
    print("=" * 70)
    print("\nSimulated CartMandate from Merchant Agent:")
    print(f"  - Cart ID: {cart_mandate['contents']['id']}")
    print(f"  - Merchant: {cart_mandate['contents']['merchant_name']}")
    print(f"  - Amount: ${cart_mandate['contents']['payment_request']['details']['total']['amount']['value']}")
    print(f"  - Expires: {cart_mandate['contents']['cart_expiry']}")
    print(f"  - Signature: {cart_mandate['merchant_authorization']}")
    print("\nCalling Credentials Provider to process payment...")
    print("=" * 70)

    runner = Runner(
        agent=credentials_provider_mock,  # ← Use mock
        app_name=app_name,
        session_service=session_service
    )

    user_message = Content(parts=[Part(text="Please process this payment.")])

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=user_message
    ):
        if event.is_final_response():
            print("\n" + "=" * 70)
            print("CREDENTIALS PROVIDER RESPONSE:")
            print("=" * 70)
            if event.content and event.content.parts:
                print(event.content.parts[0].text)

    final_session = await session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )

    if "payment_mandate" in final_session.state:
        payment_mandate = final_session.state["payment_mandate"]
        print("\n" + "=" * 70)
        print("PAYMENTMANDATE CREATED:")
        print("=" * 70)

        if "payment_mandate_contents" in payment_mandate:
            contents = payment_mandate["payment_mandate_contents"]
            print(f"  Payment Mandate ID: {contents.get('payment_mandate_id')}")
            print(f"  Linked to Cart: {contents.get('payment_details_id')}")
            print(f"  User Consent: {contents.get('user_consent')}")
            print(f"  Amount: {contents.get('amount', {}).get('currency')} {contents.get('amount', {}).get('value')}")
            print(f"  Merchant: {contents.get('merchant_name')}")

        print(f"  Agent Present: {payment_mandate.get('agent_present')}")
        print("=" * 70)
    else:
        print("\n❌ Error: PaymentMandate not found in state")

    if "payment_result" in final_session.state:
        result = final_session.state["payment_result"]
        print("\n" + "=" * 70)
        print("PAYMENT RESULT:")
        print("=" * 70)
        print(f"  Transaction ID: {result.get('transaction_id')}")
        print(f"  Status: {result.get('status')}")
        print(f"  Amount: {result.get('currency')} {result.get('amount')}")
        print(f"  Merchant: {result.get('merchant')}")
        print(f"  Simulation: {result.get('simulation')}")
        print("=" * 70)
    else:
        print("\n❌ Error: Payment result not found in state")


if __name__ == "__main__":
    asyncio.run(test_credentials_provider())
