"""
Fraud Pipeline Orchestrator Agent
====================================
Name  : fraud_pipeline_orchestrator
Model : gemini-2.5-pro
Mode  : Dual — Batch Pipeline (non-conversational) + SIU Query Chat (conversational)

Design patterns applied:
  ✅ BaseTool + ToolRegistry  — 5 tools, each independently swappable
  ✅ LLMProvider              — Agent created via singleton, not hardcoded
  ✅ Pydantic schemas         — All boundaries validated (schemas.py)
  ✅ PromptFacade             — All prompts loaded from versioned YAML
  ✅ Arize tracing            — span_chain/tool wrapping every pipeline step
  ✅ Dependency Injection     — clients/storage injected, not imported directly

Responsibilities (5 tools):
  Tool 1: ingest_claim_batch         — Validate N claims (Pydantic-backed)
  Tool 2: enrich_claim               — Delegate to Enrichment Agent (A2A :8002)
  Tool 3: analyze_fraud_patterns     — Delegate to Analyzer Agent (A2A :8003)
  Tool 4: generate_investigation_report — Delegate to Report Generator (A2A :8004)
  Tool 5: query_results              — SIU chat (Kevin/Diana profile-adaptive)

Dual-level parallelism:
  Level 1: N claims via asyncio.gather  (batch)
  Level 2: 4 patterns per claim         (inside Analyzer Agent)
"""

import asyncio
import json
from typing import Dict, List, Optional

from src.core.ports.repository import IStorageRepository
from src.infrastructure.tools.registry import ToolRegistry
from src.infrastructure.llm.provider import llm_provider
from src.prompt_manager.engine.facade import PromptFacade
from src.infrastructure.telemetry.arize_wrappers import span_chain, span_tool, tracer

from src.application.agents.orchestrator.schemas import BatchPipelineOutput
from src.application.agents.orchestrator.tools.ingest_batch import IngestBatchTool
from src.application.agents.orchestrator.tools.pipeline_tools import (
    EnrichClaimTool,
    AnalyzeFraudPatternsTool,
    GenerateReportTool,
    QueryResultsTool,
)


class OrchestratorAgent:
    """
    Fraud Pipeline Orchestrator.
    Owns a ToolRegistry of 5 tools and coordinates the full pipeline.
    """

    agent_name = "fraud_pipeline_orchestrator"
    model      = "gemini-2.5-pro"

    def __init__(
        self,
        enrichment_client,
        analyzer_client,
        report_client,
        storage: IStorageRepository,
    ):
        self._storage  = storage

        # LLM via provider (swap model in settings.py, not here)
        self._llm = llm_provider.get_agent(
            name=self.agent_name,
            model=self.model,
            instruction=PromptFacade.get_prompt("orchestrator_system"),
        )

        # Build tool registry (DI — clients injected, not hardcoded)
        self._query_tool = QueryResultsTool()
        self._registry   = ToolRegistry()
        self._registry.register(IngestBatchTool())
        self._registry.register(EnrichClaimTool(enrichment_client))
        self._registry.register(AnalyzeFraudPatternsTool(analyzer_client))
        self._registry.register(GenerateReportTool(report_client, storage))
        self._registry.register(self._query_tool)

    # ─────────────────────────────────────────────────────────────────────────
    # MODE 1: Batch Pipeline (non-conversational)
    # ─────────────────────────────────────────────────────────────────────────

    async def process_claim_batch(self, batch_json_str: str) -> str:
        """
        Entry point for the batch pipeline.

        Arize span hierarchy:
          CHAIN: Orchestrator: Batch Pipeline
            TOOL:  Orchestrator: Ingest & Validate Batch
            CHAIN: Claim Pipeline [CLM-XXX]          ← N claims, parallel
              TOOL:  Claim Data Enrichment Agent [CLM-XXX]
              CHAIN: Fraud Pattern Analyzer [CLM-XXX]
              CHAIN: Investigation Report Generator [CLM-XXX]  ← if score ≥ 40
        """
        with span_chain(
            "Orchestrator: Batch Pipeline",
            input_value=batch_json_str[:500],
            **{"agent.name": self.agent_name, "agent.model": self.model}
        ) as batch_span:

            # ── Tool 1: Ingest & Validate ─────────────────────────────────
            batch = await self._registry.get("ingest_claim_batch").run(
                batch_json=batch_json_str
            )
            batch_span.set_attribute("batch.id",     batch["batch_id"])
            batch_span.set_attribute("batch.total",  str(batch["total_claims"]))
            batch_span.set_attribute("batch.valid",  str(len(batch["valid_claims"])))
            batch_span.set_attribute("batch.invalid",str(len(batch["invalid_claims"])))

            # ── Level-1 Parallelism: all N claims concurrently ────────────
            results: list = await asyncio.gather(*[
                self._process_single_claim(claim)
                for claim in batch["valid_claims"]
            ])

            results = sorted(
                results,
                key=lambda r: r["fraud_analysis"].get("composite_score", 0),
                reverse=True,
            )

            # ── Aggregate stats ───────────────────────────────────────────
            tiers: Dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            pattern_counts: Dict[str, int] = {}
            provider_freq:  Dict[str, int] = {}

            for r in results:
                fa   = r["fraud_analysis"]
                tier = fa.get("priority_tier", "low")
                tiers[tier] = tiers.get(tier, 0) + 1

                for pat, pat_data in fa.get("pattern_results", {}).items():
                    if pat_data.get("score", 0) >= 40:
                        pattern_counts[pat] = pattern_counts.get(pat, 0) + 1

                prov_id = r.get("enriched", {}).get("provider_network", {}).get("provider_id", "")
                if prov_id:
                    provider_freq[prov_id] = provider_freq.get(prov_id, 0) + 1

            repeat_providers = {k: v for k, v in provider_freq.items() if v > 1}
            top_patterns = dict(sorted(pattern_counts.items(), key=lambda x: -x[1]))

            batch_results = {
                "batch_id":               batch["batch_id"],
                "batch_name":             batch["batch_name"],
                "total_claims":           len(results),
                "tier_distribution":      tiers,
                "top_triggered_patterns": top_patterns,
                "repeat_providers":       repeat_providers,
                "validation_summary":     batch["validation_summary"],
                "invalid_claims":         batch["invalid_claims"],
                "results":                results,
            }

            await self._storage.save_batch(batch["batch_id"], batch_results)
            self._query_tool.update_batch_results(batch_results)

            summary_lines = [
                f"Batch {batch['batch_id']} processing complete.",
                f"Total Claims: {len(results)}",
                f"Critical: {tiers['critical']}, High: {tiers['high']}, "
                f"Medium: {tiers['medium']}, Low: {tiers['low']}",
            ]
            if repeat_providers:
                summary_lines.append(f"⚠ Repeat providers: {list(repeat_providers.keys())}")
            if top_patterns:
                top = next(iter(top_patterns))
                summary_lines.append(
                    f"Top pattern: {top.replace('_',' ').title()} "
                    f"({top_patterns[top]} claims)"
                )

            summary = "\n".join(summary_lines)
            batch_span.set_attribute("output.value", summary)

        return json.dumps({"summary": summary, "batch_results": batch_results})

    async def _process_single_claim(self, claim: dict) -> dict:
        """Per-claim pipeline: Enrich -> Analyze (4 parallel) -> Report."""
        claim_id = claim["claim_id"]

        with span_chain(
            "Claim Pipeline [" + claim_id + "]",
            input_value=json.dumps(claim),
            **{"claim.id": claim_id,
               "claimant.name": claim.get("claimant", {}).get("name", ""),
               "claimed_amount": str(claim.get("claimed_amount", 0))}
        ) as claim_span:

            # Tool 2: Enrich
            enriched = await self._registry.get("enrich_claim").run(claim=claim)

            # Tool 3: Analyze (4 patterns in parallel inside Analyzer Agent)
            fraud_analysis = await self._registry.get("analyze_fraud_patterns").run(
                enriched_claim=enriched
            )
            score = fraud_analysis.get("composite_score", 0)
            tier  = fraud_analysis.get("priority_tier", "low")

            # Tool 4: Report (flagged claims only)
            report = None
            if score >= 40:
                report = await self._registry.get("generate_investigation_report").run(
                    claim_id=claim_id,
                    fraud_analysis=fraud_analysis,
                    enriched_data=enriched,
                )

            # -- Fraud-specific Arize span attributes (spec 13.1) --
            # pattern_flags: comma-separated patterns with score > 40
            pattern_flags = ",".join(
                pat for pat, data in fraud_analysis.get("pattern_results", {}).items()
                if data.get("score", 0) > 40
            )
            last_prompt = PromptFacade.get_last_usage()

            claim_span.set_attribute("fraud_score",             str(score))
            claim_span.set_attribute("fraud_tier",              tier)
            claim_span.set_attribute("pattern_flags",           pattern_flags)
            claim_span.set_attribute("enrichment_completeness", enriched.get("enrichment_status", "complete"))
            claim_span.set_attribute("report_generated",        str(report is not None))
            claim_span.set_attribute("prompt_template",         last_prompt.get("template", ""))
            claim_span.set_attribute("prompt_version",          last_prompt.get("version", ""))
            # Legacy attributes kept
            claim_span.set_attribute("composite_score",         str(score))
            claim_span.set_attribute("priority_tier",           tier)

        return {
            "claim_id":       claim_id,
            "enriched":       enriched,
            "fraud_analysis": fraud_analysis,
            "report":         report,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # MODE 2: SIU Query Chat (conversational)
    # ─────────────────────────────────────────────────────────────────────────

    async def handle_siu_query(self, query: str, profile: dict) -> str:
        """
        Tool 5: Profile-adaptive SIU investigator query handler.
        Delegates to QueryResultsTool which holds the last batch results.
        Wrapped in an Arize CHAIN span.
        """
        with span_chain(
            "Orchestrator: SIU Query",
            input_value=query,
            **{
                "agent.name":    self.agent_name,
                "query.text":    query,
                "user.persona":  profile.get("experience", "junior"),
            }
        ) as span:
            result = await self._registry.get("query_results").run(query=query, profile=profile)
            span.set_attribute("output.value", str(result)[:2000])
        return result



