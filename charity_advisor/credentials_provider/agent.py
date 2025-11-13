"""
Credentials Provider Agent - Handles payment processing with user consent.
This agent acts as our "Payment Processor."
"""

# MODULE_6_STEP_4_IMPORT_COMPONENTS


credentials_provider = Agent(
    name="CredentialsProvider",
    model="gemini-2.5-flash",
    description="Securely processes payments by creating PaymentMandates and executing transactions with user consent.",

    # MODULE_6_STEP_5_WRITE_INSTRUCTION
    instruction="""""",

    # MODULE_6_STEP_6_ADD_TOOLS
    tools=[],
)
