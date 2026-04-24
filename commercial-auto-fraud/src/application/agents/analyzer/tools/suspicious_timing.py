"""Tool 2: Suspicious Timing Pattern Analyzer"""
from src.application.agents.analyzer.tools.base_pattern_tool import BasePatternTool


class SuspiciousTimingTool(BasePatternTool):
    name        = "suspicious_timing_analyzer"
    pattern_key = "suspicious_timing"
    description = (
        "Chain-of-Thought analysis for Suspicious Timing pattern. "
        "Evaluates: loss within 30 days of policy inception, within 60 days of expiration, "
        "Friday-night/Monday-morning loss, coverage upgrade within 72h before loss, "
        "lapse-then-reinstate pattern. Weight in composite score: 20%."
    )

