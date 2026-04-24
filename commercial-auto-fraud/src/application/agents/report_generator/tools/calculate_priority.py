"""
Tool 3: calculate_priority_score
----------------------------------
Combines composite fraud score with financial magnitude.
A $200K claim at score 75 is higher priority than a $5K claim at score 75.

Priority matrix:
  P1-Immediate : score ≥ 80  OR  (score ≥ 60 AND amount ≥ 100K)
  P2-Urgent    : score ≥ 60  OR  (score ≥ 40 AND amount ≥ 50K)
  P3-Standard  : score ≥ 40
  P4-Monitor   : score < 40

This is pure computation — no LLM needed.
"""

from src.infrastructure.tools.base_tool import BaseTool
from src.application.agents.report_generator.schemas import PriorityScore


class CalculatePriorityTool(BaseTool):
    name = "calculate_priority_score"
    description = (
        "Calculates investigation priority by combining composite fraud score with "
        "financial magnitude. Returns priority_rank (P1-Immediate to P4-Monitor), "
        "priority_score (0-100), estimated_exposure (claim_amount × fraud_score/100), "
        "and reasoning. No LLM call — pure deterministic computation."
    )

    async def execute(self, fraud_score: float, claim_amount: float) -> dict:
        # Estimated financial exposure if fraud
        exposure = round(claim_amount * (fraud_score / 100), 2)

        # Priority score: weighted combination (70% fraud score, 30% financial magnitude)
        # Normalize amount: $100K = 100 on the scale
        amount_score = min(100.0, (claim_amount / 1000))
        priority_score = round((fraud_score * 0.70) + (amount_score * 0.30), 1)

        # Priority rank
        if fraud_score >= 80 or (fraud_score >= 60 and claim_amount >= 100_000):
            rank = "P1-Immediate"
            reasoning = (
                f"Composite fraud score {fraud_score} exceeds 80 threshold"
                if fraud_score >= 80
                else f"High-value claim (${claim_amount:,.0f}) with significant fraud score ({fraud_score})"
            )
        elif fraud_score >= 60 or (fraud_score >= 40 and claim_amount >= 50_000):
            rank = "P2-Urgent"
            reasoning = (
                f"Fraud score {fraud_score} indicates significant fraud indicators "
                f"requiring prompt investigation. Exposure: ${exposure:,.0f}."
            )
        elif fraud_score >= 40:
            rank = "P3-Standard"
            reasoning = (
                f"Fraud score {fraud_score} warrants monitoring. "
                f"Estimated exposure: ${exposure:,.0f}."
            )
        else:
            rank = "P4-Monitor"
            reasoning = (
                f"Fraud score {fraud_score} below investigation threshold. "
                "Flag for periodic review only."
            )

        return PriorityScore(
            priority_score=priority_score,
            priority_rank=rank,
            reasoning=reasoning,
            estimated_exposure=exposure,
        ).model_dump()


