"""
Tools for the MerchantAgent.

This file contains tools for creating W3C-compliant CartMandates
and simulating merchant signatures.
"""

from typing import Dict, Any
import logging
import hashlib
import json
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


def _validate_intent_expiry(intent_mandate: dict) -> tuple[bool, str]:
    """
    Validates that the IntentMandate hasn't expired.

    This is a critical security check - expired intents should not be processed.

    Args:
        intent_mandate: The IntentMandate to validate

    Returns:
        (is_valid, error_message): Tuple indicating if intent is still valid
    """
    # Check if intent_expiry field exists
    if "intent_expiry" not in intent_mandate:
        return False, "IntentMandate missing intent_expiry field"

    try:
        # Parse the expiry timestamp
        expiry_str = intent_mandate["intent_expiry"]
        expiry_time = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))

        # Get current time
        now = datetime.now(timezone.utc)

        # Check if expired
        if expiry_time < now:
            return False, f"IntentMandate expired at {expiry_str}"

        # Check how much time is left
        time_remaining = expiry_time - now
        logger.info(f"IntentMandate valid. Expires in {time_remaining.total_seconds():.0f} seconds")

        return True, ""

    except (ValueError, TypeError) as e:
        return False, f"Invalid intent_expiry format: {e}"


def _generate_merchant_signature(cart_contents: dict) -> str:
    """
    Generates a simulated merchant signature for the CartMandate contents.

    In production, this would use PKI or JWT with the merchant's private key.
    For education, we use SHA-256 to demonstrate the concept.

    Args:
        cart_contents: The cart contents to sign (the 'contents' object)

    Returns:
        Simulated signature string (format: "SIG_" + first 16 chars of hash)
    """
    # Convert cart contents to stable JSON string
    cart_json = json.dumps(cart_contents, sort_keys=True)

    # Generate SHA-256 hash
    cart_hash = hashlib.sha256(cart_json.encode('utf-8')).hexdigest()

    # Create signature in recognizable format
    signature = f"SIG_{cart_hash[:16]}"

    logger.info(f"Generated merchant signature: {signature}")
    return signature


async def create_cart_mandate(tool_context: Any) -> Dict[str, Any]:
    """
    Creates a W3C PaymentRequest-compliant CartMandate from the IntentMandate.

    This tool reads the IntentMandate from shared state (written by Shopping Agent),
    validates it hasn't expired, and creates a formal, signed offer that the
    Credentials Provider can process.

    Returns:
        Dictionary containing status and the created CartMandate
    """
    logger.info("Tool called: Creating CartMandate from IntentMandate")

    # Read IntentMandate from state (written by Shopping Agent)
    intent_mandate = tool_context.state.get("intent_mandate")
    if not intent_mandate:
        logger.error("No IntentMandate found in state")
        return {
            "status": "error",
            "message": "No IntentMandate found. Shopping Agent must create intent first."
        }

    # Validate that intent hasn't expired (CRITICAL security check)
    is_valid, error_message = _validate_intent_expiry(intent_mandate)
    if not is_valid:
        logger.error(f"IntentMandate validation failed: {error_message}")
        return {"status": "error", "message": error_message}

    # Extract data from IntentMandate
    charity_name = intent_mandate["merchants"][0] if intent_mandate.get("merchants") else None
    charity_ein = intent_mandate.get("charity_ein")
    amount = intent_mandate.get("amount")

    if not charity_name or not amount:
        return {
            "status": "error",
            "message": "IntentMandate missing required fields (merchants or amount)"
        }

    # Generate unique CartMandate ID
    timestamp = datetime.now(timezone.utc)
    cart_id = f"cart_{hashlib.sha256(f'{charity_name}{timestamp.isoformat()}'.encode()).hexdigest()[:12]}"

    # Cart expires in 15 minutes (shorter than intent - creates urgency)
    cart_expiry = timestamp + timedelta(minutes=15)

    # Create the cart contents (AP2 structure)
    cart_contents = {
        "id": cart_id,
        "cart_expiry": cart_expiry.isoformat(),
        "merchant_name": charity_name,
        "user_cart_confirmation_required": False,  # Human present flow

        # W3C PaymentRequest nested inside
        "payment_request": {
            # Section 1: Payment methods accepted
            "method_data": [{
                "supported_methods": ["card", "bank_transfer"],
                "data": {
                    "supported_networks": ["visa", "mastercard", "amex"],
                    "supported_types": ["debit", "credit"]
                }
            }],

            # Section 2: Transaction details
            "details": {
                "display_items": [{
                    "label": f"Donation to {charity_name}",
                    "amount": {
                        "currency": "USD",
                        "value": f"{amount:.2f}"
                    }
                }],
                "total": {
                    "label": "Total Donation",
                    "amount": {
                        "currency": "USD",
                        "value": f"{amount:.2f}"
                    }
                }
            },

            # Section 3: Options
            "options": {
                "request_payer_name": False,
                "request_payer_email": False,
                "request_payer_phone": False,
                "request_shipping": False
            }
        }
    }

    # Generate merchant signature (signs the contents)
    signature = _generate_merchant_signature(cart_contents)

    # Create AP2 CartMandate structure
    cart_mandate = {
        "contents": cart_contents,
        "merchant_authorization": signature,
        "timestamp": timestamp.isoformat()
    }

    # Write CartMandate to state for Credentials Provider
    tool_context.state["cart_mandate"] = cart_mandate
    tool_context.state["cart_mandate_id"] = cart_id

    logger.info(f"CartMandate created successfully: {cart_id}")

    return {
        "status": "success",
        "message": f"Created signed CartMandate {cart_id} for ${amount:.2f} donation to {charity_name}",
        "cart_id": cart_id,
        "cart_expiry": cart_expiry.isoformat(),
        "signature": signature
    }
