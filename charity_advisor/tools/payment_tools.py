"""
Tools for the CredentialsProvider.

This file contains tools for creating PaymentMandates and simulating
payment processing.
"""

from typing import Dict, Any
import logging
import hashlib
from datetime import datetime, timezone
from ap2.types.mandate import CartMandate, PaymentMandate, PaymentMandateContents
from ap2.types.payment_request import PaymentResponse

logger = logging.getLogger(__name__)


def _validate_cart_expiry(cart: CartMandate) -> tuple[bool, str]:
    """
    Validates that the CartMandate hasn't expired.
    
    This is a critical security check - expired carts should not be processed.
    
    Args:
        cart: The Pydantic CartMandate model to validate.
        
    Returns:
        (is_valid, error_message): Tuple indicating if cart is still valid.
    """
    try:
        expiry_str = cart.contents.cart_expiry
        expiry_time = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        
        if expiry_time < now:
            return False, f"CartMandate expired at {expiry_str}"
        
        time_remaining = expiry_time - now
        logger.info(f"CartMandate valid. Expires in {time_remaining.total_seconds():.0f} seconds")
        
        return True, ""
        
    except (ValueError, TypeError, AttributeError) as e:
        return False, f"Invalid cart_expiry format or structure: {e}"


def _create_payment_mandate(cart: CartMandate, consent_granted: bool) -> dict:
    """
    Creates a PaymentMandate using the official AP2 Pydantic models.
    
    It links to the CartMandate and includes user consent status.
    
    Args:
        cart: The validated Pydantic CartMandate model being processed.
        consent_granted: Whether the user has consented to the payment.
        
    Returns:
        A dictionary representation of the final, validated PaymentMandate.
    """
    timestamp = datetime.now(timezone.utc)
    
    # Safely extract details from the validated CartMandate model
    cart_id = cart.contents.id
    merchant_name = cart.contents.merchant_name
    total_item = cart.contents.payment_request.details.total
    
    # Create the nested PaymentResponse model for the mandate
    payment_response_model = PaymentResponse(
        request_id=cart_id,
        method_name="CARD",  # As per the simulated flow
        details={"token": "simulated_payment_token_12345"}
    )
    
    # Create the PaymentMandateContents model
    payment_mandate_contents_model = PaymentMandateContents(
        payment_mandate_id=f"payment_{hashlib.sha256(f'{cart_id}{timestamp.isoformat()}'.encode()).hexdigest()[:12]}",
        payment_details_id=cart_id,
        payment_details_total=total_item,
        payment_response=payment_response_model,
        merchant_agent=merchant_name,
        timestamp=timestamp.isoformat()
    )
    
    # Create the top-level PaymentMandate model
    # In a real system, a user signature would be added to this model
    payment_mandate_model = PaymentMandate(
        payment_mandate_contents=payment_mandate_contents_model
    )
    
    # Convert the final Pydantic model to a dictionary for state storage
    final_dict = payment_mandate_model.model_dump(mode='json')
    
    # Add any custom/non-standard fields required by the codelab's logic to the dictionary
    # The spec does not have these fields, but your original code did. We add them
    # back to ensure compatibility with later steps.
    final_dict['payment_mandate_contents']['user_consent'] = consent_granted
    final_dict['payment_mandate_contents']['consent_timestamp'] = timestamp.isoformat() if consent_granted else None
    final_dict['agent_present'] = True
    
    return final_dict


async def create_payment_mandate(tool_context: Any) -> Dict[str, Any]:
    """
    Creates a PaymentMandate and simulates payment processing using Pydantic models.
    
    This tool now reads the CartMandate from state, parses it into a validated model,
    and creates a spec-compliant PaymentMandate.
    """
    logger.info("Tool called: Creating PaymentMandate and processing payment")

    # 1. Read CartMandate dictionary from state
    cart_mandate_dict = tool_context.state.get("cart_mandate")
    if not cart_mandate_dict:
        logger.error("No CartMandate found in state")
        return { "status": "error", "message": "No CartMandate found. Merchant Agent must create cart first." }
    
    # 2. Parse dictionary into a validated Pydantic model
    try:
        cart_model = CartMandate.model_validate(cart_mandate_dict)
    except Exception as e:
        logger.error(f"Could not validate CartMandate structure: {e}")
        return {"status": "error", "message": f"Invalid CartMandate structure: {e}"}
    
    # 3. Validate that the cart hasn't expired using the Pydantic model
    is_valid, error_message = _validate_cart_expiry(cart_model)
    if not is_valid:
        logger.error(f"CartMandate validation failed: {error_message}")
        return {"status": "error", "message": error_message}

    # 4. Safely extract data from the validated model
    cart_id = cart_model.contents.id
    merchant_name = cart_model.contents.merchant_name
    amount_value = cart_model.contents.payment_request.details.total.amount.value
    currency = cart_model.contents.payment_request.details.total.amount.currency
    consent_granted = True  # Assume consent for this codelab flow

    # 5. Create the spec-compliant PaymentMandate using the validated CartMandate model
    payment_mandate_dict = _create_payment_mandate(cart_model, consent_granted)
    
    # 6. Simulate payment processing
    transaction_id = f"txn_{hashlib.sha256(f'{cart_id}{datetime.now(timezone.utc).isoformat()}'.encode()).hexdigest()[:16]}"
    payment_result = {
        "transaction_id": transaction_id,
        "status": "completed",
        "amount": amount_value,
        "currency": currency,
        "merchant": merchant_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "simulation": True
    }
    
    # 7. Write the compliant PaymentMandate dictionary and result to state
    tool_context.state["payment_mandate"] = payment_mandate_dict
    tool_context.state["payment_result"] = payment_result
    
    logger.info(f"Payment processed successfully: {transaction_id}")
    
    return {
        "status": "success",
        "message": f"Payment of {currency} {amount_value:.2f} to {merchant_name} processed successfully",
        "transaction_id": transaction_id,
        "payment_mandate_id": payment_mandate_dict["payment_mandate_contents"]["payment_mandate_id"]
    }
