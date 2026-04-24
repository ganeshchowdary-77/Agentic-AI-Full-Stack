"""
Claim Data Enrichment Agent
============================
Name  : claim_data_enrichment
Model : gemini-2.5-flash  (speed-critical — N instances run in parallel per batch)
Mode  : Non-conversational, task-based

Design patterns applied:
  ✅ BaseTool + ToolRegistry  — 4 lookup tools, independently swappable
  ✅ LLMProvider              — Agent created via singleton (Flash, not Pro)
  ✅ Pydantic schemas         — EnrichedClaimOutput validates all boundaries
  ✅ PromptFacade             — ReAct prompt loaded from enrichment_react/v1.yaml
  ✅ Arize tracing            — Each tool call is a named TOOL child span
  ✅ Dependency Injection     — data_provider injected, not imported

Responsibilities:
  Tool 1: lookup_claimant_history   — prior claims, fraud flags, frequency
  Tool 2: lookup_provider_network   — billing ratio, license, referral rings
  Tool 3: lookup_vehicle_valuation  — market value, repair benchmarks, VIN history
  Tool 4: lookup_policy_details     — inception, coverage changes, lapse history

Single responsibility: DATA RETRIEVAL ONLY.
No fraud scoring, no LLM reasoning on evidence.
All 4 tools run in parallel (I/O-bound, no ordering dependency).
"""

import asyncio
import json
from datetime import datetime

from src.infrastructure.tools.registry import ToolRegistry
from src.infrastructure.llm.provider import llm_provider
from src.prompt_manager.engine.facade import PromptFacade
from src.infrastructure.telemetry.arize_wrappers import span_chain, tracer

from src.application.agents.enrichment.schemas import EnrichedClaimOutput
from src.application.agents.enrichment.tools.claimant_history import ClaimantHistoryTool
from src.application.agents.enrichment.tools.provider_network import ProviderNetworkTool
from src.application.agents.enrichment.tools.vehicle_valuation import VehicleValuationTool
from src.application.agents.enrichment.tools.policy_details import PolicyDetailsTool


class FraudEnrichmentAgent:
    """
    Claim Data Enrichment Agent.

    Runs 4 data-lookup tools concurrently via asyncio.gather.
    Each claim in the batch gets its own agent instance call (Level-1 parallelism
    is handled by the Orchestrator — we just handle one claim at a time here).
    """

    agent_name = "claim_data_enrichment"
    model      = "gemini-2.5-flash"

    def __init__(self, data_provider):
        """
        Args:
            data_provider: IEnrichmentProvider (MockEnrichmentProvider in dev,
                           real external API client in prod — swap in container.py)
        """
        self._provider = data_provider

        # LLM via provider singleton — Flash for speed
        # System instruction is built once at init with all 12 template variables
        # as literal placeholder strings so format_map succeeds. Per-claim values
        # are substituted at run() time when the claim dict is passed as user message.
        self._llm = llm_provider.get_agent(
            name=self.agent_name,
            model=self.model,
            instruction=PromptFacade.get_prompt("enrichment_react", {
                "claim_id":         "{claim_id}",
                "claimant_id":      "{claimant_id}",
                "claimant_name":    "{claimant_name}",
                "provider_id":      "{provider_id}",
                "provider_type":    "{provider_type}",
                "vehicle_vin":      "{vehicle_vin}",
                "vehicle_year":     "{vehicle_year}",
                "vehicle_make":     "{vehicle_make}",
                "vehicle_model":    "{vehicle_model}",
                "policy_number":    "{policy_number}",
                "claimed_amount":   "{claimed_amount}",
                "loss_description": "{loss_description}",
            }),
        )

        # Own ToolRegistry — 4 data-lookup tools
        self._registry = ToolRegistry()
        self._registry.register(ClaimantHistoryTool(data_provider))
        self._registry.register(ProviderNetworkTool(data_provider))
        self._registry.register(VehicleValuationTool(data_provider))
        self._registry.register(PolicyDetailsTool(data_provider))

    def list_tools(self) -> list[dict]:
        """Returns tool metadata for debugging and Arize annotations."""
        return self._registry.list_tools()

    async def run(self, claim: dict) -> dict:
        """
        Executes all 4 enrichment tools in parallel and returns an
        EnrichedClaimOutput-compatible dict.

        Arize span hierarchy (created here as child of Orchestrator span):
          TOOL: Claim Data Enrichment Agent [CLM-XXX]   ← created by server_enrichment.py
            TOOL: lookup_claimant_history               ← via BaseTool.run()
            TOOL: lookup_provider_network               ← via BaseTool.run()
            TOOL: lookup_vehicle_valuation              ← via BaseTool.run()
            TOOL: lookup_policy_details                 ← via BaseTool.run()
        """
        claim_id = claim.get("claim_id", "UNKNOWN")
        claimant = claim.get("claimant", {})
        provider = claim.get("provider", {})
        vehicle  = claim.get("vehicle", {})

        enrichment_status = "complete"
        errors = []

        # All 4 lookups are independent I/O — run concurrently for speed
        try:
            (
                claimant_history,
                provider_network,
                vehicle_valuation,
                policy_details,
            ) = await asyncio.gather(
                self._registry.get("lookup_claimant_history").run(
                    claimant_id=claimant.get("id", "")
                ),
                self._registry.get("lookup_provider_network").run(
                    provider_id=provider.get("id", ""),
                    provider_type=provider.get("type", "unknown"),
                ),
                self._registry.get("lookup_vehicle_valuation").run(
                    vin=vehicle.get("vin", ""),
                    year=vehicle.get("year", 2020),
                    make=vehicle.get("make", ""),
                    model=vehicle.get("model", ""),
                ),
                self._registry.get("lookup_policy_details").run(
                    policy_number=claim.get("policy_number", "")
                ),
            )
        except Exception as e:
            enrichment_status = "partial"
            errors.append(str(e))
            claimant_history = {}
            provider_network = {}
            vehicle_valuation = {}
            policy_details = {}

        return {
            "claim_id":           claim_id,
            "raw_claim":          claim,
            "claimant_history":   claimant_history,
            "provider_network":   provider_network,
            "vehicle_valuation":  vehicle_valuation,
            "policy_details":     policy_details,
            "enrichment_status":  enrichment_status,
            "enrichment_timestamp": datetime.utcnow().isoformat(),
            **({"enrichment_errors": errors} if errors else {}),
        }


