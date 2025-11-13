"""
Tools for the ShoppingAgent.

This file contains tools for discovering trustworthy charities and for saving
the user's final choice to the shared state for handoff to the next agent.
"""

from typing import Dict, Any
import logging
from charity_advisor.data.charities import get_charities_by_cause

logger = logging.getLogger(__name__)


# This tool is pre-written. It simulates a call to a trusted,
# curated database of charitable organizations.
async def find_charities(cause_area: str) -> Dict[str, Any]:
    """
    Finds vetted charities from a trusted internal database for a specific cause area.

    Args:
        cause_area (str): The cause the user is interested in (e.g., 'education').

    Returns:
        A dictionary containing the search results.
    """
    logger.info(f"Tool called: Searching for charities in cause area '{cause_area}'")
    charities = get_charities_by_cause(cause_area)

    if not charities:
        logger.warning(f"No charities found for cause area: {cause_area}")
        return {
            "status": "not_found",
            "message": f"I could not find any vetted charities for the '{cause_area}' cause."
        }

    logger.info(f"Found {len(charities)} charities.")

    # Format charities for display using our helper function
    formatted_charities = [_format_charity_display(c) for c in charities]

    return {
        "status": "success",
        "count": len(charities),
        "charities": formatted_charities,
        "raw_data": charities  # Keep raw data for downstream agents if needed
    }


def _validate_charity_data(charity_name: str, charity_ein: str, amount: float) -> tuple[bool, str]:
    """
    Validates charity selection data before saving to state.

    This helper function performs basic validation to ensure data quality
    before it gets passed to other agents in the pipeline.

    Args:
        charity_name: Name of the selected charity
        charity_ein: Employer Identification Number (should be format: XX-XXXXXXX)
        amount: Donation amount in USD

    Returns:
        (is_valid, error_message): Tuple where is_valid is True if all checks pass,
                                    and error_message contains details if validation fails
    """
    # Validate charity name
    if not charity_name or not charity_name.strip():
        return False, "Charity name cannot be empty"

    # Validate EIN format (should be XX-XXXXXXX)
    if not charity_ein or len(charity_ein) != 10 or charity_ein[2] != '-':
        return False, f"Invalid EIN format: {charity_ein}. Expected format: XX-XXXXXXX"

    # Validate amount
    if amount <= 0:
        return False, f"Donation amount must be positive, got: ${amount}"

    if amount > 1_000_000:
        return False, f"Donation amount exceeds maximum of $1,000,000: ${amount}"

    # All checks passed
    return True, ""


def _create_intent_mandate(charity_name: str, charity_ein: str, amount: float) -> dict:
    """
    Creates an IntentMandate - AP2's verifiable credential for user intent.

    An IntentMandate captures what the user wants to do in a structured,
    machine-readable format. This is the first of three verifiable credentials
    in the AP2 architecture.

    Args:
        charity_name: Name of the selected charity
        charity_ein: Employer Identification Number
        amount: Donation amount in USD

    Returns:
        Dictionary containing the IntentMandate structure per AP2 specification
    """
    from datetime import datetime, timedelta, timezone

    # Current timestamp
    timestamp = datetime.now(timezone.utc)

    # Intent expires in 1 hour (user must complete transaction before then)
    expiry = timestamp + timedelta(hours=1)

    # Create AP2-compliant IntentMandate
    intent_mandate = {
        # Core AP2 fields
        "user_cart_confirmation_required": True,  # User must approve the cart
        "natural_language_description": f"Donate ${amount:.2f} to {charity_name}",
        "merchants": [charity_name],  # Which merchant(s) can fulfill this
        "skus": None,  # Not applicable for donations (used for product SKUs)
        "requires_refundability": False,  # Donations typically non-refundable
        "intent_expiry": expiry.isoformat(),  # When this intent expires

        # Metadata
        "timestamp": timestamp.isoformat(),
        "intent_id": f"intent_{charity_ein.replace('-', '')}_{int(timestamp.timestamp())}",

        # Domain-specific context (charity donations)
        "charity_ein": charity_ein,
        "amount": amount,
        "currency": "USD"
    }

    return intent_mandate


async def save_user_choice(
    charity_name: str,
    charity_ein: str,
    amount: float,
    tool_context: Any
) -> Dict[str, Any]:
    """
    Saves the user's final charity choice and donation amount to the shared state.
    This action prepares the data for a secure handoff to the next agent.

    Args:
        charity_name: Name of the selected charity
        charity_ein: Employer Identification Number (EIN) of the charity
        amount: Donation amount in USD
        tool_context: ADK tool context providing access to shared state

    Returns:
        Dictionary containing status and confirmation details
    """
    logger.info(f"Tool called: Saving user choice of '{charity_name}' for ${amount}")

    # Validate inputs before creating IntentMandate
    is_valid, error_message = _validate_charity_data(charity_name, charity_ein, amount)
    if not is_valid:
        logger.error(f"Validation failed: {error_message}")
        return {"status": "error", "message": error_message}

    # Create AP2 IntentMandate
    intent_mandate = _create_intent_mandate(charity_name, charity_ein, amount)

    # Write the IntentMandate to shared state for the next agent
    # This is the ONLY data we write - downstream agents will read from this credential
    tool_context.state["intent_mandate"] = intent_mandate

    logger.info(f"Successfully created IntentMandate and saved to state")
    logger.info(f"Intent ID: {intent_mandate['intent_id']}")
    logger.info(f"Intent expires: {intent_mandate['intent_expiry']}")

    # Return success confirmation
    return {
        "status": "success",
        "message": f"Created IntentMandate: ${amount:.2f} donation to {charity_name} (EIN: {charity_ein})",
        "intent_id": intent_mandate["intent_id"],
        "expiry": intent_mandate["intent_expiry"]
    }


def _format_charity_display(charity: dict) -> str:
    """
    Formats a charity dictionary into a user-friendly display string.

    This helper function demonstrates how to transform structured data
    into readable text for the user.

    Args:
        charity: Dictionary containing charity data (name, ein, mission, rating, efficiency)

    Returns:
        Formatted string suitable for display to the user
    """
    name = charity.get('name', 'Unknown')
    ein = charity.get('ein', 'N/A')
    mission = charity.get('mission', 'No mission statement available')
    rating = charity.get('rating', 0.0)
    efficiency = charity.get('efficiency', 0.0)

    # Format efficiency as percentage
    efficiency_pct = int(efficiency * 100)

    # Build formatted string
    display = f"""
**{name}** (EIN: {ein})
⭐ Rating: {rating}/5.0
💰 Efficiency: {efficiency_pct}% of funds go to programs
📋 Mission: {mission}
    """.strip()

    return display
