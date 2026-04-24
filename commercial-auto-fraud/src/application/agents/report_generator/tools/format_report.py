"""
Tool 1: format_investigation_report
--------------------------------------
Calls the LLM (Gemini 2.5 Flash) with the PromptFacade investigation_report
prompt to produce the full 7-section Markdown report.

Pre-processing (no LLM):
  - Tools 2 and 3 run first (evidence table + priority score)
  - Results injected into the LLM prompt context

The LLM's job: narrative synthesis and section formatting only.
All scores and evidence come from upstream (Analyzer Agent).
"""

import json
from src.infrastructure.tools.base_tool import BaseTool
from src.prompt_manager.engine.facade import PromptFacade


class FormatReportTool(BaseTool):
    name = "format_investigation_report"
    description = (
        "Generates a 7-section Markdown investigation report using Gemini 2.5 Flash. "
        "Sections: Case Header, Executive Summary, Pattern Analysis Detail, "
        "Evidence Summary Table, Recommended Actions, Risk Factors, "
        "Claimant & Provider Profile. "
        "Receives pre-computed evidence table and priority score from Tools 2 & 3."
    )

    def __init__(self, llm_agent):
        self._agent = llm_agent

    async def execute(
        self,
        fraud_analysis: dict,
        enriched_data:  dict,
        evidence_table: str,
        priority:       dict,
    ) -> str:
        # Load versioned prompt from YAML
        prompt = PromptFacade.get_prompt(
            "investigation_report",
            context={
                "fraud_analysis": json.dumps(fraud_analysis, indent=2),
                "enriched_data":  json.dumps(enriched_data, indent=2),
            }
        )

        # Append pre-computed sections so the LLM doesn't have to re-derive them
        prompt += f"""

## PRE-COMPUTED EVIDENCE TABLE (use this verbatim in Section 4):
{evidence_table}

## PRE-COMPUTED PRIORITY (use in Section 1 Case Header):
Priority Rank: {priority.get('priority_rank', 'P3-Standard')}
Priority Score: {priority.get('priority_score', 0)}
Estimated Exposure: ${priority.get('estimated_exposure', 0):,.0f}
Priority Reasoning: {priority.get('reasoning', '')}
"""
        report = await self._agent.run(prompt)
        return str(report).strip()


