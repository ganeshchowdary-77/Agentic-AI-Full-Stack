"""
SIU Chat Agent
Handles conversational queries about batch results.
"""

from google.adk.agents import LlmAgent
from google.adk.models import ModelConfig
from ..tools.query_tools import read_batch_results, get_claim_detail
from ..prompts.manager import prompt_manager

siu_chat_agent = LlmAgent(
    name="siu_chat_agent",
    instruction=prompt_manager.get("siu_chat_system"),
    model=ModelConfig(
        provider="google",
        model="gemini-2.5-pro",
        temperature=0.3,
    ),
    tools=[
        read_batch_results,
        get_claim_detail,
    ],
)
