"""
Claim Data Enrichment Agent
Runs as an independent task (one per claim).
Uses Gemini Flash to orchestrate 4 enrichment tool calls.
"""

from google.adk.agents import LlmAgent
from google.adk.agents.llm_agent_config import LlmAgentConfig
from google.adk.agents.parallel_agent_config import ParallelAgentConfig
from google.adk.models import ModelConfig
from ..tools.enrichment_tools import (
    lookup_claimant_history,
    lookup_provider_network,
    lookup_vehicle_valuation,
    lookup_policy_details,
)
from ..prompts.manager import prompt_manager

enrichment_agent = LlmAgent(
    name="claim_data_enrichment",
    instruction=prompt_manager.get("enrichment_system"),
    model=ModelConfig(
        provider="google",
        model="gemini-2.5-flash",
        temperature=0.0,
    ),
    tools=[
        lookup_claimant_history,
        lookup_provider_network,
        lookup_vehicle_valuation,
        lookup_policy_details,
    ],
)
