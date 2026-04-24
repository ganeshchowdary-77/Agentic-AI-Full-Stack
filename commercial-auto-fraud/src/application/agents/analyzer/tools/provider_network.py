"""Tool 4: Provider Network Anomaly Pattern Analyzer"""
from src.application.agents.analyzer.tools.base_pattern_tool import BasePatternTool


class ProviderNetworkTool(BasePatternTool):
    name        = "provider_network_analyzer"
    pattern_key = "provider_network"
    description = (
        "Chain-of-Thought analysis for Provider Network Anomalies pattern. "
        "Evaluates: license_status != 'active', billing_ratio > 2.0, circular referral rings, "
        "claims outside geographic service area, flagged_claims_count as % of total. "
        "Weight in composite score: 25%."
    )

