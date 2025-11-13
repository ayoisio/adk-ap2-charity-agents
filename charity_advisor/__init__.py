"""
Charity Advisor - Root orchestrator for the donation system.
"""
try:
    from .agent import root_agent
    __all__ = ["root_agent"]
except (ImportError, AttributeError):
    __all__ = []
