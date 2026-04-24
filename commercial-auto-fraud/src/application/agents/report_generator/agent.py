"""
Investigation Report Generator Agent
======================================
Name  : investigation_report_generator
Model : gemini-2.5-flash  (formatting task, not analytical — speed matters for parallel batches)
Mode  : Non-conversational, task-based

Design patterns applied:
  ✅ BaseTool + ToolRegistry  — 3 tools (2 deterministic, 1 LLM)
  ✅ LLMProvider              — Flash agent via singleton (not Pro — no reasoning needed)
  ✅ Pydantic schemas         — ReportInput, PriorityScore, ReportOutput
  ✅ PromptFacade             — investigation_report prompt from versioned YAML
  ✅ Arize tracing            — LLM span for the report generation step
  ✅ Dependency Injection     — llm_agent injected, not hardcoded

Tool execution order (sequential — each feeds the next):
  Tool 3: calculate_priority_score  →  priority dict    (deterministic)
  Tool 2: format_evidence_summary   →  evidence table   (deterministic)
  Tool 1: format_investigation_report → full Markdown   (LLM — Flash)

Why sequential (not parallel):
  Tools 2 & 3 are pre-processors for Tool 1. Their outputs are injected into
  the LLM prompt so the model doesn't have to re-derive or re-format them.
"""

from datetime import datetime

from src.infrastructure.tools.registry import ToolRegistry
from src.infrastructure.llm.provider import llm_provider
from src.infrastructure.telemetry.arize_wrappers import span_chain, span_llm

from src.application.agents.report_generator.schemas import ReportOutput
from src.application.agents.report_generator.tools.calculate_priority import CalculatePriorityTool
from src.application.agents.report_generator.tools.format_evidence    import FormatEvidenceTool
from src.application.agents.report_generator.tools.format_report      import FormatReportTool


class ReportGenerator:
    """
    Investigation Report Generator Agent.

    Orchestrates 3 tools sequentially:
      1. calculate_priority_score  (no LLM)
      2. format_evidence_summary   (no LLM)
      3. format_investigation_report (LLM — Flash)

    Only called for claims with composite_score >= 40.
    """

    agent_name = "investigation_report_generator"
    model      = "gemini-2.5-flash"

    def __init__(self):
        # Flash for speed — report generation is formatting, not reasoning
        self._llm = llm_provider.get_agent(
            name=self.agent_name,
            model=self.model,
            instruction=(
                "You are an Investigation Report Generator for commercial auto insurance fraud. "
                "You produce structured, professional SIU case file reports in Markdown. "
                "Be specific — cite claim IDs, dollar amounts, dates, provider names. "
                "Never use vague language. Every assertion must reference actual data provided."
            ),
        )

        self._registry = ToolRegistry()
        self._registry.register(CalculatePriorityTool())
        self._registry.register(FormatEvidenceTool())
        self._registry.register(FormatReportTool(self._llm))

    def list_tools(self) -> list[dict]:
        return self._registry.list_tools()

    async def run(
        self,
        claim_id:       str,
        fraud_analysis: dict,
        enriched_data:  dict,
    ) -> str:
        """
        Generates a full Markdown investigation report.

        Arize span hierarchy (as child of Orchestrator's Claim Pipeline span):
          CHAIN: Investigation Report Generator [CLM-XXX]   ← server_report.py
            LLM:  investigation_report_generator.run        ← this method
        """
        raw_claim     = enriched_data.get("raw_claim", {})
        fraud_score   = fraud_analysis.get("composite_score", 0)
        claim_amount  = raw_claim.get("claimed_amount", 0)
        pattern_results = fraud_analysis.get("pattern_results", {})

        # ── Tool 3: Priority score (deterministic, runs first) ────────────
        priority = await self._registry.get("calculate_priority_score").run(
            fraud_score=fraud_score,
            claim_amount=float(claim_amount),
        )

        # ── Tool 2: Evidence table (deterministic, runs second) ───────────
        evidence_table = await self._registry.get("format_evidence_summary").run(
            pattern_results=pattern_results,
        )

        # ── Tool 1: LLM report (Flash, runs last — receives pre-computed context)
        with span_llm(
            f"investigation_report_generator.run [{claim_id}]",
            model=self.model,
            input_value=f"claim_id={claim_id} score={fraud_score} tier={fraud_analysis.get('priority_tier')}",
            **{"agent.name": self.agent_name, "claim.id": claim_id,
               "fraud_score": str(fraud_score), "priority_rank": priority.get("priority_rank", "")}
        ) as span:
            report_md = await self._registry.get("format_investigation_report").run(
                fraud_analysis=fraud_analysis,
                enriched_data=enriched_data,
                evidence_table=evidence_table,
                priority=priority,
            )
            span.set_attribute("output.value",   report_md[:2000])
            span.set_attribute("word_count",      str(len(report_md.split())))
            span.set_attribute("priority_rank",   priority.get("priority_rank", ""))
            span.set_attribute("estimated_exposure", str(priority.get("estimated_exposure", 0)))

        return report_md


