"""
Merchant Agent - Creates W3C-compliant CartMandates with merchant signatures.
This agent acts as our "Contract Creator."
"""

# MODULE_5_STEP_4_IMPORT_COMPONENTS


merchant_agent = Agent(
    name="MerchantAgent",
    model="gemini-2.5-flash",
    description="Creates formal, signed CartMandates for charity donations following W3C PaymentRequest standards.",

    # MODULE_5_STEP_5_WRITE_INSTRUCTION
    instruction="""""",

    # MODULE_5_STEP_6_ADD_TOOLS
    tools=[]
)
