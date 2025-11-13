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


# MODULE_4_STEP_1_ADD_VALIDATION_HELPER


# MODULE_4_STEP_2_ADD_INTENTMANDATE_CREATION_HELPER


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

    # MODULE_4_STEP_3_COMPLETE_SAVE_TOOL


# MODULE_4_STEP_4_ADD_FORMATTING_HELPER