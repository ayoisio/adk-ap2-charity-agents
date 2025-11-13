"""
End-to-end test of the three-agent pipeline.
Uses mock CredentialsProvider to bypass confirmation for automated testing.
"""

import asyncio
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai.types import Content, Part
from charity_advisor.shopping_agent.agent import shopping_agent
from charity_advisor.merchant_agent.agent import merchant_agent
from charity_advisor.credentials_provider.agent_mock import credentials_provider_mock  # ← Use mock


async def test_full_pipeline():
    """Test the complete three-agent pipeline with AP2 credentials."""

    session_service = InMemorySessionService()
    app_name = "charity_advisor"
    user_id = "test_user"
    session_id = "pipeline_session"

    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state={}
    )

    print("=" * 70)
    print("THREE-AGENT PIPELINE TEST (AP2 CREDENTIAL CHAIN)")
    print("=" * 70)

    # ========================================================================
    # Step 1: Shopping Agent
    # ========================================================================
    print("\n[1/3] SHOPPING AGENT - Finding charity and creating IntentMandate...")
    print("-" * 70)

    shopping_runner = Runner(
        agent=shopping_agent,
        app_name=app_name,
        session_service=session_service
    )

    user_query_1 = Content(parts=[Part(text="Show me education charities")])
    async for event in shopping_runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=user_query_1
    ):
        if event.is_final_response():
            pass

    user_query_2 = Content(parts=[Part(text="I'll donate $75 to Room to Read")])
    async for event in shopping_runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=user_query_2
    ):
        if event.is_final_response():
            pass

    session_after_shopping = await session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )

    if "intent_mandate" in session_after_shopping.state:
        intent = session_after_shopping.state["intent_mandate"]
        print(f"✓ IntentMandate created")
        print(f"  - Intent ID: {intent.get('intent_id')}")
        print(f"  - Description: {intent.get('natural_language_description')}")
        print(f"  - Merchant: {intent.get('merchants', ['N/A'])[0]}")
        print(f"  - Amount: ${intent.get('amount')}")
        print(f"  - Expires: {intent.get('intent_expiry')}")
    else:
        print("❌ Error: IntentMandate not found in state")
        return

    # ========================================================================
    # Step 2: Merchant Agent
    # ========================================================================
    print("\n[2/3] MERCHANT AGENT - Reading IntentMandate and creating CartMandate...")
    print("-" * 70)

    merchant_runner = Runner(
        agent=merchant_agent,
        app_name=app_name,
        session_service=session_service
    )

    merchant_query = Content(parts=[Part(text="Create the CartMandate")])
    async for event in merchant_runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=merchant_query
    ):
        if event.is_final_response():
            pass

    session_after_merchant = await session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )

    if "cart_mandate" in session_after_merchant.state:
        cart = session_after_merchant.state["cart_mandate"]
        print(f"✓ CartMandate created")

        if "contents" in cart:
            contents = cart["contents"]
            print(f"  - ID: {contents.get('id')}")
            print(f"  - Expires: {contents.get('cart_expiry')}")
        else:
            print(f"  - ID: {cart.get('id')}")

        print(f"  - Signature: {cart.get('merchant_authorization')}")
    else:
        print("❌ Error: CartMandate not found in state")
        return

    # ========================================================================
    # Step 3: Credentials Provider (MOCK - NO CONFIRMATION)
    # ========================================================================
    print("\n[3/3] CREDENTIALS PROVIDER - Creating PaymentMandate and processing...")
    print("-" * 70)
    print("NOTE: Using mock agent - consent is automatically granted")

    credentials_runner = Runner(
        agent=credentials_provider_mock,  # ← Use mock
        app_name=app_name,
        session_service=session_service
    )

    credentials_query = Content(parts=[Part(text="Process the payment")])
    async for event in credentials_runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=credentials_query
    ):
        if event.is_final_response():
            pass

    final_session = await session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )

    if "payment_result" in final_session.state:
        payment_result = final_session.state["payment_result"]
        print(f"✓ Payment processed (SIMULATED)")
        print(f"  - Transaction ID: {payment_result.get('transaction_id')}")
        print(f"  - Amount: ${payment_result.get('amount')}")
        print(f"  - Status: {payment_result.get('status')}")
    else:
        print("❌ Error: Payment result not found in state")
        return

    # ========================================================================
    # Verify complete mandate chain
    # ========================================================================
    print("\n" + "=" * 70)
    print("COMPLETE AP2 CREDENTIAL CHAIN")
    print("=" * 70)

    print("\n✓ Credential 1: IntentMandate (User's Intent)")
    intent = final_session.state.get("intent_mandate", {})
    print(f"  - Intent ID: {intent.get('intent_id')}")
    print(f"  - Description: {intent.get('natural_language_description')}")
    print(f"  - Expiry: {intent.get('intent_expiry')}")

    print("\n✓ Credential 2: CartMandate (Merchant's Offer)")
    cart = final_session.state.get("cart_mandate", {})
    if "contents" in cart:
        print(f"  - Cart ID: {cart['contents'].get('id')}")
        print(f"  - Cart Expiry: {cart['contents'].get('cart_expiry')}")
    else:
        print(f"  - Cart ID: {cart.get('id')}")
    print(f"  - Merchant Signature: {cart.get('merchant_authorization')}")

    print("\n✓ Credential 3: PaymentMandate (Payment Execution)")
    payment_mandate = final_session.state.get("payment_mandate", {})
    if "payment_mandate_contents" in payment_mandate:
        contents = payment_mandate["payment_mandate_contents"]
        print(f"  - Payment Mandate ID: {contents.get('payment_mandate_id')}")
        print(f"  - Linked to Cart: {contents.get('payment_details_id')}")
    print(f"  - Agent Present: {payment_mandate.get('agent_present')}")

    print("\n✓ Transaction Result:")
    print(f"  - Transaction ID: {payment_result.get('transaction_id')}")
    print(f"  - Simulation: {payment_result.get('simulation')}")

    print("\n" + "=" * 70)
    print("✅ COMPLETE PIPELINE TEST PASSED")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
