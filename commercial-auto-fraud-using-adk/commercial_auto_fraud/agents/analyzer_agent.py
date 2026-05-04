"""
Fraud Pattern Analyzer Agent
Orchestrates parallel pattern analysis for a single claim.
Uses Gemini Pro for deep CoT reasoning.
"""

import json
from google.adk.agents import ParallelAgent, LlmAgent, SequentialAgent
from google.adk.models import ModelConfig
from ..tools.analysis_tools import (
    analyze_duplicate_pattern,
    analyze_timing_pattern,
    analyze_inflation_pattern,
    analyze_provider_network,
)
from ..prompts.manager import (
    prompt_manager,
    DUPLICATE_SPECIFIC,
    TIMING_SPECIFIC,
    INFLATION_SPECIFIC,
    PROVIDER_SPECIFIC
)

# Common model config for analyzers
analyzer_model = ModelConfig(
    provider="google",
    model="gemini-2.5-pro",
    temperature=0.1,  # Low temp for deterministic scoring
)

# ---------------------------------------------------------
# Level 2 Parallelism: The 4 Pattern Sub-Agents
# ---------------------------------------------------------

dup_prompt = prompt_manager.get("pattern_cot").format(
    pattern_name="duplicate_similar",
    claim_id="{claim_id}",
    claimant_name="{claimant_name}",
    loss_date="{loss_date}",
    claimed_amount="{claimed_amount}",
    enriched_data="{enriched_data}",
    pattern_specific_instructions=DUPLICATE_SPECIFIC
)

duplicate_analyzer = LlmAgent(
    name="duplicate_analyzer",
    instruction=dup_prompt,
    model=analyzer_model,
    tools=[analyze_duplicate_pattern],
)

timing_prompt = prompt_manager.get("pattern_cot").format(
    pattern_name="suspicious_timing",
    claim_id="{claim_id}",
    claimant_name="{claimant_name}",
    loss_date="{loss_date}",
    claimed_amount="{claimed_amount}",
    enriched_data="{enriched_data}",
    pattern_specific_instructions=TIMING_SPECIFIC
)

timing_analyzer = LlmAgent(
    name="timing_analyzer",
    instruction=timing_prompt,
    model=analyzer_model,
    tools=[analyze_timing_pattern],
)

inflation_prompt = prompt_manager.get("pattern_cot").format(
    pattern_name="inflated_amounts",
    claim_id="{claim_id}",
    claimant_name="{claimant_name}",
    loss_date="{loss_date}",
    claimed_amount="{claimed_amount}",
    enriched_data="{enriched_data}",
    pattern_specific_instructions=INFLATION_SPECIFIC
)

inflation_analyzer = LlmAgent(
    name="inflation_analyzer",
    instruction=inflation_prompt,
    model=analyzer_model,
    tools=[analyze_inflation_pattern],
)

provider_prompt = prompt_manager.get("pattern_cot").format(
    pattern_name="provider_network",
    claim_id="{claim_id}",
    claimant_name="{claimant_name}",
    loss_date="{loss_date}",
    claimed_amount="{claimed_amount}",
    enriched_data="{enriched_data}",
    pattern_specific_instructions=PROVIDER_SPECIFIC
)

provider_analyzer = LlmAgent(
    name="provider_analyzer",
    instruction=provider_prompt,
    model=analyzer_model,
    tools=[analyze_provider_network],
)

# Run the 4 patterns in parallel
pattern_analyzers = ParallelAgent(
    name="pattern_analyzers",
    sub_agents=[
        duplicate_analyzer,
        timing_analyzer,
        inflation_analyzer,
        provider_analyzer
    ]
)

# ---------------------------------------------------------
# Composite Scorer (Synthesizes the parallel results)
# ---------------------------------------------------------

class CompositeScorer(LlmAgent):
    """Custom agent step to aggregate scores from the parallel analyzers."""
    def __init__(self):
        super().__init__(
            name="composite_scorer",
            instruction="You are a composite scorer. Just return the structured JSON passed to you.",
            model=analyzer_model
        )
        
    async def _run_async_impl(self, context):
        # In ADK 1.31.1, we override _run_async_impl
        # Extract results from the parallel agent run
        # Implementation depends on how ADK stores sub-agent outputs in context.
        # For now, we'll keep the logic but it might need adjustment for ADK 1.31.1
        # Typically results are in the event history.
        return super()._run_async_impl(context)

# ---------------------------------------------------------
# Master Analyzer Agent
# ---------------------------------------------------------

analyzer_agent = SequentialAgent(
    name="fraud_pattern_analyzer",
    sub_agents=[pattern_analyzers, CompositeScorer()]
)
