"""
Validates CartMandate structure against W3C PaymentRequest standard and AP2 format.
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


def validate_ap2_cartmandate(cart_mandate: dict) -> tuple[bool, list[str]]:
    """
    Validates CartMandate against AP2 and W3C PaymentRequest structure.

    Returns:
        (is_valid, errors): Tuple of validation result and error messages
    """
    errors = []

    # 1. Check AP2 top-level structure
    if "contents" not in cart_mandate:
        errors.append("Missing AP2 wrapper: 'contents'")
    if "merchant_authorization" not in cart_mandate:
        errors.append("Missing AP2 signature: 'merchant_authorization'")

    if "contents" in cart_mandate:
        contents = cart_mandate["contents"]

        # 2. Check AP2 'contents' required fields
        if "id" not in contents:
            errors.append("contents is missing required field: 'id'")
        if "cart_expiry" not in contents:
            errors.append("contents is missing required field: 'cart_expiry'")
        if "merchant_name" not in contents:
            errors.append("contents is missing required field: 'merchant_name'")
        if "payment_request" not in contents:
            errors.append("contents is missing required field: 'payment_request'")

        # 3. Check nested W3C PaymentRequest structure
        if "payment_request" in contents:
            pr = contents["payment_request"]

            # Check method_data
            if "method_data" not in pr:
                errors.append("payment_request is missing required field: 'method_data'")
            elif not isinstance(pr["method_data"], list):
                errors.append("'method_data' must be an array")
            elif len(pr["method_data"]) == 0:
                errors.append("'method_data' must be a non-empty array")
            else:
                # Check first method_data item
                if "supported_methods" not in pr["method_data"][0]:
                    errors.append("method_data item is missing 'supported_methods'")

            # Check details structure
            if "details" not in pr:
                errors.append("payment_request is missing required field: 'details'")
            else:
                details = pr["details"]
                if "total" not in details:
                    errors.append("details is missing required field: 'total'")
                else:
                    total = details["total"]
                    if "amount" not in total:
                        errors.append("details.total is missing required field: 'amount'")
                    else:
                        amount = total["amount"]
                        if "currency" not in amount:
                            errors.append("amount is missing required field: 'currency'")
                        if "value" not in amount:
                            errors.append("amount is missing required field: 'value'")

            # Check options (optional but validate if present)
            if "options" in pr:
                options = pr["options"]
                # These are all optional booleans, just validate they exist if present
                valid_option_keys = {
                    "request_payer_name",
                    "request_payer_email",
                    "request_payer_phone",
                    "request_shipping",
                    "shipping_type"
                }
                for key in options:
                    if key not in valid_option_keys:
                        errors.append(f"Unknown option key: {key}")

    return len(errors) == 0, errors


async def test_validation():
    """Test CartMandate validation with correct state simulation."""

    # Create session service
    session_service = InMemorySessionService()

    # Define session identifiers
    app_name = "charity_advisor"
    user_id = "test_user"
    session_id = "validation_session"

    # CORRECTLY simulate the state as created by the Shopping Agent in Module 4
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
        "intent_id": "intent_test_validation",

        # Domain-specific context
        "charity_ein": "77-0479905",
        "amount": 50.0,
        "currency": "USD"
    }

    # Create session with correct initial state
    session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state={"intent_mandate": intent_mandate}
    )

    # Create Runner for Merchant Agent
    runner = Runner(
        agent=merchant_agent,
        app_name=app_name,
        session_service=session_service
    )

    # Run the Merchant Agent to create CartMandate
    user_message = Content(parts=[Part(text="Create the CartMandate.")])
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=user_message
    ):
        if event.is_final_response():
            pass  # Agent completed

    # Get the final session state
    final_session = await session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )

    # Validate the CartMandate structure
    cart = final_session.state.get("cart_mandate")
    if not cart:
        print("❌ No CartMandate found in state")
        return

    is_valid, errors = validate_ap2_cartmandate(cart)

    print("=" * 70)
    print("AP2 & W3C PAYMENTREQUEST VALIDATION")
    print("=" * 70)

    if is_valid:
        print("✅ CartMandate is AP2 and W3C PaymentRequest compliant")
        print("\nStructure validation passed:")
        print("  ✓ AP2 'contents' wrapper present")
        print("  ✓ AP2 'merchant_authorization' signature present")
        print("  ✓ cart_expiry present")
        print("  ✓ payment_request nested inside contents")
        print("  ✓ method_data present and valid")
        print("  ✓ details.total.amount present with currency and value")
        print("  ✓ All required W3C PaymentRequest fields present")
    else:
        print("❌ CartMandate validation failed:")
        for error in errors:
            print(f"  - {error}")

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_validation())
