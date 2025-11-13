"""
A simple agent that can research charities using Google Search.
"""

from google.adk.agents import Agent
from google.adk.tools import google_search


simple_agent = Agent(
    name="SimpleAgent",
    model="gemini-2.5-flash",
    instruction="""You are a helpful research assistant. When a user asks you to find information about charities,
use the google_search tool to find the most relevant and up-to-date results from the web.
Synthesize the search results into a helpful summary.""",
    tools=[google_search]
)
