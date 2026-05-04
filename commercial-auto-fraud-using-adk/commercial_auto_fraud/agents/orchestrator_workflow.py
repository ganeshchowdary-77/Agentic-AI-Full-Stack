"""
Orchestrator Workflow
Coordinates the fraud detection pipeline using direct agent invocation.
Processes batches of claims through enrichment, analysis, and reporting stages.
"""

import asyncio
import json
import time
from typing import Dict, Any, List
from datetime import datetime
from ..agents.enrichment_agent import enrichment_agent
from ..agents.analyzer_agent import analyzer_agent
from ..agents.report_agent import report_agent
from ..domain.schemas import (
    ClaimInput, EnrichedClaim, CompositeScore, InvestigationReport,
    BatchResult, ClaimResult, PriorityTier, ConfidenceLevel,
    compute_composite_score, classify_tier, classify_confidence
)
from ..infrastructure.mock_providers import provider


class FraudDetectionOrchestrator:
    """Orchestrates the complete fraud detection pipeline for a batch of claims."""
    
    def __init__(self):
        self.enrichment_agent = enrichment_agent
        self.analyzer_agent = analyzer_agent
        self.report_agent = report_agent
    
    async def enrich_claim(self, claim_input: ClaimInput) -> EnrichedClaim:
        """Enriches a single claim with data from 4 external sources."""
        try:
            # Prepare the input for the enrichment agent
            claim_dict = claim_input.model_dump()
            claim_json = json.dumps(claim_dict)
            
            # Invoke the enrichment agent
            result = await self.enrichment_agent.invoke(claim_json)
            
            # Parse the enrichment results
            # The agent should return structured data with all 4 enrichment sources
            enriched_data = json.loads(str(result.output)) if hasattr(result, 'output') else {}
            
            # Build the EnrichedClaim object
            enriched_claim = EnrichedClaim(
                claim_id=claim_input.claim_id,
                raw_claim=claim_input,
                claimant_history=enriched_data.get("claimant_history", {}),
                provider_data=enriched_data.get("provider_data", {}),
                vehicle_valuation=enriched_data.get("vehicle_valuation", {}),
                policy_details=enriched_data.get("policy_details", {}),
                enrichment_status="complete",
                enrichment_timestamp=datetime.utcnow().isoformat()
            )
            
            return enriched_claim
            
        except Exception as e:
            print(f"Enrichment error for claim {claim_input.claim_id}: {e}")
            # Return minimal enriched claim on error
            return EnrichedClaim(
                claim_id=claim_input.claim_id,
                raw_claim=claim_input,
                claimant_history={},
                provider_data={},
                vehicle_valuation={},
                policy_details={},
                enrichment_status="failed",
                enrichment_timestamp=datetime.utcnow().isoformat()
            )
    
    async def analyze_claim(self, enriched_claim: EnrichedClaim) -> CompositeScore:
        """Analyzes an enriched claim for fraud patterns."""
        try:
            # Prepare the input for the analyzer agent
            enriched_json = json.dumps(enriched_claim.model_dump())
            
            # Invoke the analyzer agent
            result = await self.analyzer_agent.invoke(enriched_json)
            
            # Parse the analysis results
            analysis_data = json.loads(str(result.output)) if hasattr(result, 'output') else {}
            
            # Extract pattern results
            pattern_results = analysis_data.get("pattern_results", {})
            
            # Calculate composite score
            duplicate_score = pattern_results.get("duplicate_similar", {}).get("score", 0.0)
            timing_score = pattern_results.get("suspicious_timing", {}).get("score", 0.0)
            inflation_score = pattern_results.get("inflated_amounts", {}).get("score", 0.0)
            provider_score = pattern_results.get("provider_network", {}).get("score", 0.0)
            
            composite = compute_composite_score(
                duplicate_score, timing_score, inflation_score, provider_score
            )
            
            # Count patterns flagged (score > 40)
            patterns_flagged = sum(1 for p in pattern_results.values() if p.get("score", 0) > 40)
            
            composite_score = CompositeScore(
                claim_id=enriched_claim.claim_id,
                pattern_results=pattern_results,
                composite_score=composite,
                confidence=classify_confidence(patterns_flagged),
                priority_tier=classify_tier(composite),
                patterns_flagged=patterns_flagged
            )
            
            return composite_score
            
        except Exception as e:
            print(f"Analysis error for claim {enriched_claim.claim_id}: {e}")
            # Return minimal score on error
            return CompositeScore(
                claim_id=enriched_claim.claim_id,
                composite_score=0.0,
                confidence=ConfidenceLevel.LOW,
                priority_tier=PriorityTier.LOW,
                patterns_flagged=0
            )
    
    async def generate_report(self, enriched_claim: EnrichedClaim, composite_score: CompositeScore) -> InvestigationReport:
        """Generates an investigation report for flagged claims."""
        try:
            # Prepare the input for the report agent
            report_input = {
                "claim_id": enriched_claim.claim_id,
                "enriched_claim": enriched_claim.model_dump(),
                "composite_score": composite_score.model_dump()
            }
            report_json = json.dumps(report_input)
            
            # Invoke the report agent
            result = await self.report_agent.invoke(report_json)
            
            # Parse the report results
            report_data = json.loads(str(result.output)) if hasattr(result, 'output') else {}
            
            investigation_report = InvestigationReport(
                claim_id=enriched_claim.claim_id,
                executive_summary=report_data.get("executive_summary", ""),
                pattern_breakdown=report_data.get("pattern_breakdown", []),
                evidence_table=report_data.get("evidence_table", ""),
                recommended_actions=report_data.get("recommended_actions", []),
                risk_factors=report_data.get("risk_factors", []),
                priority_score=composite_score.composite_score,
                priority_rank=f"P{1 if composite_score.composite_score >= 80 else 2 if composite_score.composite_score >= 60 else 3}-{composite_score.priority_tier.value.title()}",
                estimated_exposure=enriched_claim.raw_claim.claimed_amount,
                report_markdown=report_data.get("report_markdown", "")
            )
            
            return investigation_report
            
        except Exception as e:
            print(f"Report generation error for claim {enriched_claim.claim_id}: {e}")
            return InvestigationReport(
                claim_id=enriched_claim.claim_id,
                executive_summary=f"Error generating report: {str(e)}",
                priority_score=composite_score.composite_score,
                estimated_exposure=enriched_claim.raw_claim.claimed_amount
            )
    
    async def process_single_claim(self, claim_input: ClaimInput) -> ClaimResult:
        """Processes a single claim through the complete pipeline."""
        start_time = time.time()
        
        try:
            # Step 1: Enrich
            enriched_claim = await self.enrich_claim(claim_input)
            
            # Step 2: Analyze
            composite_score = await self.analyze_claim(enriched_claim)
            
            # Step 3: Generate report (only if score >= 40)
            has_report = False
            if composite_score.composite_score >= 40.0:
                await self.generate_report(enriched_claim, composite_score)
                has_report = True
            
            # Get top pattern
            top_pattern = ""
            top_pattern_score = 0.0
            if composite_score.pattern_results:
                for pattern_name, pattern_data in composite_score.pattern_results.items():
                    score = pattern_data.get("score", 0.0)
                    if score > top_pattern_score:
                        top_pattern_score = score
                        top_pattern = pattern_name
            
            processing_time = (time.time() - start_time) * 1000
            
            return ClaimResult(
                claim_id=claim_input.claim_id,
                claimant_name=claim_input.claimant.name,
                claimed_amount=claim_input.claimed_amount,
                composite_score=composite_score.composite_score,
                priority_tier=composite_score.priority_tier,
                confidence=composite_score.confidence,
                patterns_flagged=composite_score.patterns_flagged,
                top_pattern=top_pattern,
                top_pattern_score=top_pattern_score,
                has_report=has_report,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            print(f"Error processing claim {claim_input.claim_id}: {e}")
            processing_time = (time.time() - start_time) * 1000
            return ClaimResult(
                claim_id=claim_input.claim_id,
                claimant_name=claim_input.claimant.name,
                claimed_amount=claim_input.claimed_amount,
                processing_time_ms=processing_time
            )
    
    async def process_batch(self, batch_data: Dict[str, Any]) -> BatchResult:
        """Processes a complete batch of claims concurrently."""
        start_time = time.time()
        
        batch_id = batch_data.get("batch_id", "unknown")
        batch_name = batch_data.get("batch_name", "")
        claims_data = batch_data.get("claims", [])
        
        # Convert to ClaimInput objects
        claim_inputs = [ClaimInput(**claim) for claim in claims_data]
        
        # Process all claims concurrently
        tasks = [self.process_single_claim(claim) for claim in claim_inputs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and count failures
        claim_results = []
        failed_count = 0
        for result in results:
            if isinstance(result, Exception):
                failed_count += 1
            else:
                claim_results.append(result)
        
        # Calculate tier distribution
        tier_distribution = {
            "critical": sum(1 for r in claim_results if r.priority_tier == PriorityTier.CRITICAL),
            "high": sum(1 for r in claim_results if r.priority_tier == PriorityTier.HIGH),
            "medium": sum(1 for r in claim_results if r.priority_tier == PriorityTier.MEDIUM),
            "low": sum(1 for r in claim_results if r.priority_tier == PriorityTier.LOW)
        }
        
        # Calculate top triggered patterns
        pattern_counts = {}
        for result in claim_results:
            if result.top_pattern:
                pattern_counts[result.top_pattern] = pattern_counts.get(result.top_pattern, 0) + 1
        
        top_patterns = [
            {"pattern": pattern, "count": count}
            for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        processing_time = (time.time() - start_time) * 1000
        
        batch_result = BatchResult(
            batch_id=batch_id,
            batch_name=batch_name,
            total_claims=len(claims_data),
            processed_claims=len(claim_results),
            failed_claims=failed_count,
            results=claim_results,
            tier_distribution=tier_distribution,
            top_triggered_patterns=top_patterns[:5],
            processing_time_ms=processing_time,
            timestamp=datetime.utcnow().isoformat()
        )
        
        return batch_result


# Global orchestrator instance
orchestrator = FraudDetectionOrchestrator()