"""
Shopping Agent - Finds charities from a trusted database and saves the user's choice.
This agent acts as our specialized "Research Analyst."
"""

# MODULE_4_STEP_5_IMPORT_COMPONENTS


shopping_agent = Agent(
    name="ShoppingAgent",
    model="gemini-2.5-flash",
    description="Finds and recommends vetted charities from a trusted database, then saves the user's final choice for processing.",

    # MODULE_4_STEP_6_WRITE_INSTRUCTION
    instruction="""""",

    # MODULE_4_STEP_7_ADD_TOOLS
    tools=[]
)
