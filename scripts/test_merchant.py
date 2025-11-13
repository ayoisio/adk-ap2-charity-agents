"""
Test script for the Merchant Agent.
Simulates Shopping Agent output in state (IntentMandate), then runs Merchant Agent.
"""

import asyncio

from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

from datetime import datetime, timedelta, timezone
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai.types import Content, Part
from charity_advisor.merchant_agent.agent import merchant_agent


async def test_merchant_agent():
    """Test the Merchant Agent with simulated Shopping Agent data."""

    # Create session service
    session_service = InMemorySessionService()

    # Define session identifiers
    app_name = "charity_advisor"
    user_id = "test_user"
    session_id = "test_session"

    # Simulate the IntentMandate that Shopping Agent would create
    timestamp = datetime.now(timezone.utc)
    expiry = timestamp + timedelta(hours=1)

    intent_mandate = {
        # Core AP2 fields
        "user_cart_confirmation_required": True,
        "natural_language_description": "Donate $50.00 to Room to Read",
        "merchants": ["Room to Read"],
        "skus": None,
        "requires_refundability": False,
        "intent_expiry": expiry.isoformat(),

        # Metadata
        "timestamp": timestamp.isoformat(),
        "intent_id": "intent_774799058_test",

        # Domain-specific context
        "charity_ein": "77-0479905",
        "amount": 50.0,
        "currency": "USD"
    }

    # Create session with initial state containing the IntentMandate
    session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state={"intent_mandate": intent_mandate}
    )

    print("=" * 70)
    print("MERCHANT AGENT TEST")
    print("=" * 70)
    print("\nSimulated IntentMandate from Shopping Agent:")
    print(f"  - Intent ID: {intent_mandate['intent_id']}")
    print(f"  - Description: {intent_mandate['natural_language_description']}")
    print(f"  - Merchant: {intent_mandate['merchants'][0]}")
    print(f"  - Amount: ${intent_mandate['amount']}")
    print(f"  - Expires: {intent_mandate['intent_expiry']}")
    print("\nCalling Merchant Agent to create CartMandate...")
    print("=" * 70)

    # Create Runner
    runner = Runner(
        agent=merchant_agent,
        app_name=app_name,
        session_service=session_service
    )

    # Run the agent
    user_message = Content(parts=[Part(text="Please create the CartMandate for this donation.")])

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=user_message
    ):
        if event.is_final_response():
            print("\n" + "=" * 70)
            print("MERCHANT AGENT RESPONSE:")
            print("=" * 70)
            if event.content and event.content.parts:
                print(event.content.parts[0].text)

    # Check if CartMandate was created in state
    final_session = await session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )

    if "cart_mandate" in final_session.state:
        cart = final_session.state["cart_mandate"]
        print("\n" + "=" * 70)
        print("CARTMANDATE CREATED:")
        print("=" * 70)

        # Access nested structure (AP2 CartMandate has 'contents' wrapper)
        if "contents" in cart:
            contents = cart["contents"]
            print(f"  ID: {contents.get('id')}")
            payment_request = contents.get('payment_request', {})
            details = payment_request.get('details', {})
            total = details.get('total', {})
            amount = total.get('amount', {})
            print(f"  Amount: {amount.get('value', 'N/A')}")
            print(f"  Merchant: {contents.get('merchant_name', 'N/A')}")
            print(f"  Expires: {contents.get('cart_expiry', 'N/A')}")
        else:
            # Fallback for simpler structure
            print(f"  ID: {cart.get('id')}")
            print(f"  Amount: {cart.get('details', {}).get('total', {}).get('amount', {}).get('value', 'N/A')}")
            print(f"  Merchant: {cart.get('merchant', {}).get('name', 'N/A')}")

        print(f"  Signature: {cart.get('merchant_authorization', 'N/A')}")
        print("=" * 70)
    else:
        print("\n❌ Error: CartMandate not found in state")


if __name__ == "__main__":
    asyncio.run(test_merchant_agent())
