"""Tool 1: Duplicate / Similar Claims Pattern Analyzer"""
from src.application.agents.analyzer.tools.base_pattern_tool import BasePatternTool


class DuplicateSimilarTool(BasePatternTool):
    name        = "duplicate_similar_analyzer"
    pattern_key = "duplicate_similar"
    description = (
        "Chain-of-Thought analysis for Duplicate/Similar Claims pattern. "
        "Evaluates: matching VINs, same claimant across policies, overlapping loss dates "
        "within 30 days, similar loss type repeated, prior fraud flags. "
        "Weight in composite score: 30%."
    )

