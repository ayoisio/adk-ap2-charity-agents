"""
Shopping Agent - Finds charities from trusted database and creates IntentMandate.
"""
try:
    from .agent import shopping_agent
    root_agent = shopping_agent
    __all__ = ["shopping_agent", "root_agent"]
except (ImportError, AttributeError):
    __all__ = []
