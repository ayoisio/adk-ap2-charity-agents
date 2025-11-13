"""
Simple Agent - A basic charity research agent using Google Search.
"""
try:
    from .agent import simple_agent
    root_agent = simple_agent
    __all__ = ["simple_agent", "root_agent"]
except (ImportError, AttributeError):
    __all__ = []
