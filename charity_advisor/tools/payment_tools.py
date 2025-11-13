"""
Tools for the CredentialsProvider.

This file contains tools for creating PaymentMandates and simulating
payment processing.
"""

from typing import Dict, Any
import logging
import hashlib
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _validate_cart_expiry(cart_mandate: dict) -> tuple[bool, str]:
    """
    Validates that the CartMandate hasn't expired.

    This is a critical security check - expired carts should not be processed.

    Args:
        cart_mandate: The CartMandate to validate

    Returns:
        (is_valid, error_message): Tuple indicating if cart is still valid
    """
    # Check if contents wrapper exists
    if "contents" not in cart_mandate:
        return False, "CartMandate missing AP2 contents wrapper"

    contents = cart_mandate["contents"]

    # Check if cart_expiry field exists
    if "cart_expiry" not in contents:
        return False, "CartMandate missing cart_expiry field"

    try:
        # Parse the expiry timestamp
        expiry_str = contents["cart_expiry"]
        expiry_time = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))

        # Get current time
        now = datetime.now(timezone.utc)

        # Check if expired
        if expiry_time < now:
            return False, f"CartMandate expired at {expiry_str}"

        # Check how much time is left
        time_remaining = expiry_time - now
        logger.info(f"CartMandate valid. Expires in {time_remaining.total_seconds():.0f} seconds")

        return True, ""

    except (ValueError, TypeError) as e:
        return False, f"Invalid cart_expiry format: {e}"


def _create_payment_mandate(cart_mandate: dict, consent_granted: bool) -> dict:
    """
    Creates a PaymentMandate - AP2's third verifiable credential.

    A PaymentMandate is the final credential that authorizes payment execution.
    It links to the CartMandate and includes user consent status.

    Args:
        cart_mandate: The CartMandate being processed
        consent_granted: Whether user has consented to the payment

    Returns:
        Dictionary containing the PaymentMandate structure per AP2 specification
    """
    timestamp = datetime.now(timezone.utc)

    # Extract cart details from nested structure
    contents = cart_mandate["contents"]
    cart_id = contents.get("id", "unknown")
    payment_request = contents.get("payment_request", {})
    details = payment_request.get("details", {})
    total = details.get("total", {})
    amount_obj = total.get("amount", {})

    # Create PaymentMandate with AP2 structure
    payment_mandate = {
        # AP2 wrapper for payment mandate contents
        "payment_mandate_contents": {
            "payment_mandate_id": f"payment_{hashlib.sha256(f'{cart_id}{timestamp.isoformat()}'.encode()).hexdigest()[:12]}",
            "payment_details_id": cart_id,  # Links to CartMandate
            "timestamp": timestamp.isoformat(),

            # User consent
            "user_consent": consent_granted,
            "consent_timestamp": timestamp.isoformat() if consent_granted else None,

            # Payment details extracted from CartMandate
            "amount": {
                "currency": amount_obj.get("currency", "USD"),
                "value": amount_obj.get("value", "0.00")
            },

            # Merchant info
            "merchant_name": contents.get("merchant_name", "Unknown"),
        },

        # AP2 metadata
        "agent_present": True,  # Human-in-the-loop flow
        "timestamp": timestamp.isoformat()
    }

    return payment_mandate


async def create_payment_mandate(tool_context: Any) -> Dict[str, Any]:
    """
    Creates a PaymentMandate from the CartMandate and simulates payment processing.

    This tool reads the CartMandate from shared state (written by Merchant Agent),
    validates it hasn't expired, creates a PaymentMandate, and simulates payment
    execution.

    NOTE: In production, this would integrate with real payment processors.
    This is an educational simulation.

    Returns:
        Dictionary containing status and payment result
    """
    logger.info("Tool called: Creating PaymentMandate and processing payment")

    # Read CartMandate from state (written by Merchant Agent)
    cart_mandate = tool_context.state.get("cart_mandate")
    if not cart_mandate:
        logger.error("No CartMandate found in state")
        return {
            "status": "error",
            "message": "No CartMandate found. Merchant Agent must create cart first."
        }

    # Validate CartMandate structure
    if "contents" not in cart_mandate:
        logger.error("CartMandate missing AP2 contents wrapper")
        return {
            "status": "error",
            "message": "Invalid CartMandate structure: missing contents wrapper"
        }

    # Validate that cart hasn't expired (CRITICAL security check)
    is_valid, error_message = _validate_cart_expiry(cart_mandate)
    if not is_valid:
        logger.error(f"CartMandate validation failed: {error_message}")
        return {"status": "error", "message": error_message}

    # Extract data from nested CartMandate structure
    contents = cart_mandate["contents"]
    cart_id = contents.get("id", "unknown")
    merchant_name = contents.get("merchant_name", "Unknown Merchant")

    # Navigate nested structure to get amount
    payment_request = contents.get("payment_request", {})
    details = payment_request.get("details", {})
    total = details.get("total", {})
    amount_obj = total.get("amount", {})
    amount_value = amount_obj.get("value", "0.00")
    currency = amount_obj.get("currency", "USD")

    # In production, this would show a consent dialog
    # For this workshop, we support conversational consent
    consent_granted = True

    # Create PaymentMandate (third credential in AP2 chain)
    payment_mandate = _create_payment_mandate(cart_mandate, consent_granted)

    # Simulate payment processing
    # In production, this would call a real payment processor API
    transaction_id = f"txn_{hashlib.sha256(f'{cart_id}{datetime.now(timezone.utc).isoformat()}'.encode()).hexdigest()[:16]}"

    payment_result = {
        "transaction_id": transaction_id,
        "status": "completed",
        "amount": amount_value,
        "currency": currency,
        "merchant": merchant_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "simulation": True  # Flag to indicate this is simulated
    }

    # Write PaymentMandate and result to state
    tool_context.state["payment_mandate"] = payment_mandate
    tool_context.state["payment_result"] = payment_result

    logger.info(f"Payment processed successfully: {transaction_id}")

    return {
        "status": "success",
        "message": f"Payment of {currency} {amount_value} to {merchant_name} processed successfully",
        "transaction_id": transaction_id,
        "payment_mandate_id": payment_mandate["payment_mandate_contents"]["payment_mandate_id"]
    }
