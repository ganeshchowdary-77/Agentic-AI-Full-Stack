"""
Fraud Pattern Analyzer Agent
==============================
Name  : fraud_pattern_analyzer
Model : gemini-2.5-pro  (CoT reasoning demands Pro, not Flash)
Mode  : Non-conversational, task-based

Design patterns applied:
  ✅ BaseTool + ToolRegistry  — 4 CoT pattern tools via BasePatternTool
  ✅ LLMProvider              — single Pro agent instance, injected into all tools
  ✅ Pydantic schemas         — PatternResult + FraudAnalysisOutput validated
  ✅ PromptFacade             — each tool loads its CoT prompt from versioned YAML
  ✅ Arize tracing            — LLM span per pattern + CHAIN span for composite
  ✅ Dependency Injection     — llm_agent injected into tools, not hardcoded

Level-2 parallelism:
  All 4 pattern tools run via asyncio.gather (independent LLM calls).

Composite scoring weights (spec-defined):
  Duplicate/Similar  30%
  Suspicious Timing  20%
  Inflated Amounts   25%
  Provider Network   25%

Confidence rules:
  high   — 3+ patterns flagged (score > 40)
  medium — exactly 2 patterns flagged
  low    — 0–1 patterns flagged

Stretch patterns (future — add without changing this file):
  - staged_accident_cot/v1.yaml + StagedAccidentTool + register in registry
"""

import asyncio
import json

from src.infrastructure.tools.registry import ToolRegistry
from src.infrastructure.llm.provider import llm_provider
from src.prompt_manager.engine.facade import PromptFacade
from src.infrastructure.telemetry.arize_wrappers import span_chain, span_llm

from src.application.agents.analyzer.schemas import FraudAnalysisOutput, PatternResult
from src.application.agents.analyzer.tools.duplicate_similar  import DuplicateSimilarTool
from src.application.agents.analyzer.tools.suspicious_timing  import SuspiciousTimingTool
from src.application.agents.analyzer.tools.inflated_amounts   import InflatedAmountsTool
from src.application.agents.analyzer.tools.provider_network   import ProviderNetworkTool

# Composite score weights — spec-defined, change here only
WEIGHTS = {
    "duplicate_similar": 0.30,
    "suspicious_timing":  0.20,
    "inflated_amounts":   0.25,
    "provider_network":   0.25,
}

# Priority tier thresholds — driven by settings but hardcoded as fallback
_CRITICAL = 80
_HIGH     = 60
_MEDIUM   = 40


class FraudPatternAnalyzer:
    """
    Fraud Pattern Analyzer Agent.

    Runs 4 independent CoT pattern analyses in parallel per claim (Level-2 parallelism),
    then combines sub-scores into a weighted composite fraud score.
    """

    agent_name = "fraud_pattern_analyzer"
    model      = "gemini-2.5-pro"

    def __init__(self):
        # Single LLM agent instance — injected into all 4 tools (not 4 separate instances)
        self._llm = llm_provider.get_agent(
            name=self.agent_name,
            model=self.model,
            instruction=(
                "You are a fraud pattern analyzer for commercial auto insurance claims. "
                "You receive enriched claim data and evaluate specific fraud patterns "
                "using Chain-of-Thought reasoning. Always return valid JSON only."
            ),
        )

        # Each tool gets the same LLM agent — it's stateless, safe to share
        self._registry = ToolRegistry()
        self._registry.register(DuplicateSimilarTool(self._llm))
        self._registry.register(SuspiciousTimingTool(self._llm))
        self._registry.register(InflatedAmountsTool(self._llm))
        self._registry.register(ProviderNetworkTool(self._llm))

    def list_tools(self) -> list[dict]:
        return self._registry.list_tools()

    async def run(self, enriched_claim: dict) -> dict:
        """
        Execute all 4 pattern analyses in parallel and compute composite score.

        Arize span hierarchy (as child of Orchestrator's Claim Pipeline span):
          CHAIN: Fraud Pattern Analyzer [CLM-XXX]   ← created by server_analyzer.py
            LLM:  duplicate_similar_analyzer.run    ← via BasePatternTool + BaseTool.run()
            LLM:  suspicious_timing_analyzer.run
            LLM:  inflated_amounts_analyzer.run
            LLM:  provider_network_analyzer.run
        """
        claim_id = enriched_claim.get("claim_id", "UNKNOWN")

        # ── Level-2 Parallelism: all 4 CoT analyses simultaneously ──────────
        (
            duplicate_result,
            timing_result,
            inflated_result,
            provider_result,
        ) = await asyncio.gather(
            self._run_pattern_with_llm_span(
                "duplicate_similar_analyzer", enriched_claim
            ),
            self._run_pattern_with_llm_span(
                "suspicious_timing_analyzer", enriched_claim
            ),
            self._run_pattern_with_llm_span(
                "inflated_amounts_analyzer", enriched_claim
            ),
            self._run_pattern_with_llm_span(
                "provider_network_analyzer", enriched_claim
            ),
        )

        pattern_results = {
            "duplicate_similar": duplicate_result,
            "suspicious_timing":  timing_result,
            "inflated_amounts":   inflated_result,
            "provider_network":   provider_result,
        }

        # -- Composite Scoring (deterministic Python) --
        composite_score = round(
            sum(
                pattern_results[key].get("score", 0) * weight
                for key, weight in WEIGHTS.items()
            ),
            1,
        )

        # -- Confidence: how many patterns are flagged (score > 40) --
        flagged_count = sum(
            1 for r in pattern_results.values() if r.get("score", 0) > 40
        )
        confidence = (
            "high"   if flagged_count >= 3 else
            "medium" if flagged_count == 2 else
            "low"
        )

        # -- Priority Tier --
        if composite_score >= _CRITICAL:
            tier = "critical"
        elif composite_score >= _HIGH:
            tier = "high"
        elif composite_score >= _MEDIUM:
            tier = "medium"
        else:
            tier = "low"

        # -- Step 5: Narrative Coherence via composite_score_cot (LLM) --
        # Clean claims get a deterministic narrative (no LLM cost).
        # Flagged claims use the PromptFacade CoT to reason whether patterns
        # tell a coherent story (provider ring + inflated, etc.)
        narrative = "No significant fraud indicators found across the 4 patterns."
        if composite_score >= _MEDIUM:
            import json as _json
            pattern_evidence_summary = _json.dumps({
                k: {
                    "score":     v.get("score", 0),
                    "severity":  v.get("severity", ""),
                    "reasoning": v.get("reasoning", "")[:200],
                }
                for k, v in pattern_results.items()
            }, indent=2)
            raw_claim = enriched_claim.get("raw_claim", enriched_claim)
            narrative_prompt = PromptFacade.get_prompt(
                "composite_score_cot",
                context={
                    "claim_id":         claim_id,
                    "claimant_name":    raw_claim.get("claimant", {}).get("name", "Unknown"),
                    "claimed_amount":   raw_claim.get("claimed_amount", 0),
                    "duplicate_score":  pattern_results["duplicate_similar"].get("score", 0),
                    "timing_score":     pattern_results["suspicious_timing"].get("score", 0),
                    "inflated_score":   pattern_results["inflated_amounts"].get("score", 0),
                    "network_score":    pattern_results["provider_network"].get("score", 0),
                    "pattern_evidence": pattern_evidence_summary,
                }
            )
            try:
                import re as _re
                raw_narrative = await self._llm.run(narrative_prompt)
                match = _re.search(r"\"narrative\"\s*:\s*\"([^\"]+)\"", str(raw_narrative))
                narrative = match.group(1) if match else str(raw_narrative)[:300]
            except Exception:
                narrative = (
                    "Score " + str(composite_score) + " (" + tier + ") -- "
                    + str(flagged_count) + "/4 patterns flagged."
                )

        return {
            "claim_id":         claim_id,
            "pattern_results":  pattern_results,
            "composite_score":  composite_score,
            "confidence":       confidence,
            "priority_tier":    tier,
            "patterns_flagged": flagged_count,
            "narrative":        narrative,
            "weights":          WEIGHTS,
        }

    async def _run_pattern_with_llm_span(
        self, tool_name: str, enriched_claim: dict
    ) -> dict:
        """
        Runs a single pattern tool wrapped in a named LLM span for Arize.
        The LLM span is a child of the outer CHAIN span in server_analyzer.py.
        """
        claim_id = enriched_claim.get("claim_id", "UNKNOWN")
        with span_llm(
            f"{tool_name}.run [{claim_id}]",
            model=self.model,
            input_value=json.dumps(enriched_claim)[:500],
            **{"agent.name": tool_name, "claim.id": claim_id}
        ) as span:
            result = await self._registry.get(tool_name).run(enriched_claim=enriched_claim)
            span.set_attribute("pattern.score",    str(result.get("score", 0)))
            span.set_attribute("pattern.severity", result.get("severity", ""))
            span.set_attribute("output.value",     json.dumps(result)[:1000])
            return result



