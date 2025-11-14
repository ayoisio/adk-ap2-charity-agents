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
from ap2.types.mandate import IntentMandate, CartMandate, CartContents
from ap2.types.payment_request import (
    PaymentRequest,
    PaymentMethodData,
    PaymentDetailsInit,
    PaymentItem,
    PaymentCurrencyAmount,
    PaymentOptions,
)

logger = logging.getLogger(__name__)


def _validate_intent_expiry(intent_expiry_str: str) -> tuple[bool, str]:
    """
    Validates that the IntentMandate hasn't expired.
    
    This is a critical security check - expired intents should not be processed.
    
    Args:
        intent_expiry_str: The ISO 8601 timestamp string from the IntentMandate.
        
    Returns:
        (is_valid, error_message): Tuple indicating if intent is still valid.
    """
    try:
        # The .replace('Z', '+00:00') is for compatibility with older Python versions
        expiry_time = datetime.fromisoformat(intent_expiry_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        
        if expiry_time < now:
            return False, f"IntentMandate expired at {intent_expiry_str}"
        
        time_remaining = expiry_time - now
        logger.info(f"IntentMandate valid. Expires in {time_remaining.total_seconds():.0f} seconds")
        
        return True, ""
        
    except (ValueError, TypeError) as e:
        return False, f"Invalid intent_expiry format: {e}"


def _generate_merchant_signature(cart_contents: CartContents) -> str:
    """
    Generates a simulated merchant signature for the CartMandate contents.
    
    In production, this would use PKI or JWT with the merchant's private key.
    For this codelab, we use a SHA-256 hash of the sorted JSON representation.
    
    Args:
        cart_contents: The Pydantic model of the cart contents to sign.
        
    Returns:
        Simulated signature string (format: "SIG_" + first 16 chars of hash).
    """
    # Step 1: Dump the Pydantic model to a dictionary. The `mode='json'` argument
    # ensures that complex types like datetimes are serialized correctly.
    cart_contents_dict = cart_contents.model_dump(mode='json')
    
    # Step 2: Use the standard json library to create a stable, sorted JSON string.
    # separators=(',', ':') removes whitespace for a compact and canonical representation.
    cart_json = json.dumps(cart_contents_dict, sort_keys=True, separators=(',', ':'))
    
    # Step 3: Generate SHA-256 hash.
    cart_hash = hashlib.sha256(cart_json.encode('utf-8')).hexdigest()
    
    # Step 4: Create signature in a recognizable format.
    signature = f"SIG_{cart_hash[:16]}"
    
    logger.info(f"Generated merchant signature: {signature}")
    return signature


async def create_cart_mandate(tool_context: Any) -> Dict[str, Any]:
    """
    Creates a W3C PaymentRequest-compliant CartMandate from the IntentMandate.
    
    This tool reads the IntentMandate from shared state, validates it, and
    creates a formal, signed offer using the official AP2 Pydantic models.
    
    Returns:
        Dictionary containing status and the created CartMandate.
    """
    logger.info("Tool called: Creating CartMandate from IntentMandate")

    # 1. Read IntentMandate dictionary from state
    intent_mandate_dict = tool_context.state.get("intent_mandate")
    if not intent_mandate_dict:
        logger.error("No IntentMandate found in state")
        return {
            "status": "error",
            "message": "No IntentMandate found. Shopping Agent must create intent first."
        }
    
    # 2. Parse dictionary into a validated Pydantic model
    try:
        intent_mandate_model = IntentMandate.model_validate(intent_mandate_dict)
    except Exception as e:
        logger.error(f"Could not validate IntentMandate structure: {e}")
        return {"status": "error", "message": f"Invalid IntentMandate structure: {e}"}
    
    # 3. Validate that the intent hasn't expired (CRITICAL security check)
    is_valid, error_message = _validate_intent_expiry(intent_mandate_model.intent_expiry)
    if not is_valid:
        logger.error(f"IntentMandate validation failed: {error_message}")
        return {"status": "error", "message": error_message}
    
    # 4. Extract data. Safely access standard fields from the model, and
    # custom fields (like 'amount') from the original dictionary.
    charity_name = intent_mandate_model.merchants[0] if intent_mandate_model.merchants else "Unknown Charity"
    amount = intent_mandate_dict.get("amount", 0.0)

    # 5. Build the nested Pydantic models for the CartMandate
    timestamp = datetime.now(timezone.utc)
    cart_id = f"cart_{hashlib.sha256(f'{charity_name}{timestamp.isoformat()}'.encode()).hexdigest()[:12]}"
    cart_expiry = timestamp + timedelta(minutes=15)
    
    payment_request_model = PaymentRequest(
        method_data=[PaymentMethodData(
            supported_methods="CARD",
            data={"supported_networks": ["visa", "mastercard", "amex"], "supported_types": ["debit", "credit"]}
        )],
        details=PaymentDetailsInit(
            id=f"order_{cart_id}",
            display_items=[PaymentItem(
                label=f"Donation to {charity_name}",
                amount=PaymentCurrencyAmount(currency="USD", value=amount)  # Pydantic v2 handles float -> str conversion
            )],
            total=PaymentItem(
                label="Total Donation",
                amount=PaymentCurrencyAmount(currency="USD", value=amount)
            )
        ),
        options=PaymentOptions(request_shipping=False)
    )
    
    cart_contents_model = CartContents(
        id=cart_id,
        cart_expiry=cart_expiry.isoformat(),
        merchant_name=charity_name,
        user_cart_confirmation_required=False,
        payment_request=payment_request_model
    )

    # 6. Generate signature from the validated Pydantic model
    signature = _generate_merchant_signature(cart_contents_model)
    
    # 7. Create the final CartMandate model, now including the signature
    cart_mandate_model = CartMandate(
        contents=cart_contents_model,
        merchant_authorization=signature
    )
    
    # 8. Convert the final model to a dictionary for state storage and add the custom timestamp
    cart_mandate_dict = cart_mandate_model.model_dump(mode='json')
    cart_mandate_dict["timestamp"] = timestamp.isoformat()
    
    # 9. Write the final dictionary to state
    tool_context.state["cart_mandate"] = cart_mandate_dict
    
    logger.info(f"CartMandate created successfully: {cart_id}")
    
    return {
        "status": "success",
        "message": f"Created signed CartMandate {cart_id} for ${amount:.2f} donation to {charity_name}",
        "cart_id": cart_id,
        "cart_expiry": cart_expiry.isoformat(),
        "signature": signature
    }
