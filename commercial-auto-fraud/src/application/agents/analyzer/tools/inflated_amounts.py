"""Tool 3: Inflated Amounts Pattern Analyzer"""
from src.application.agents.analyzer.tools.base_pattern_tool import BasePatternTool


class InflatedAmountsTool(BasePatternTool):
    name        = "inflated_amounts_analyzer"
    pattern_key = "inflated_amounts"
    description = (
        "Chain-of-Thought analysis for Inflated Amounts pattern. "
        "Evaluates: claimed amount vs vehicle market value, repair estimate vs regional benchmark, "
        "provider billing_ratio > 2.0, rental duration vs expected repair time. "
        "Weight in composite score: 25%."
    )

