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


# MODULE_5_STEP_1_ADD_EXPIRY_VALIDATION_HELPER


# MODULE_5_STEP_2_ADD_SIGNATURE_HELPER


# MODULE_5_STEP_3A_CREATE_TOOL_SIGNATURE
