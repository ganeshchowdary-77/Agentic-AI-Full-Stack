"""
Tool 2: format_evidence_summary
---------------------------------
Compiles all evidence items from all triggered patterns into a
consolidated, deduplicated Markdown evidence table.
Pure formatting — no LLM call.
"""

from typing import List
from src.infrastructure.tools.base_tool import BaseTool

SEVERITY_ORDER = {"major": 0, "moderate": 1, "minor": 2, "clean": 3}


class FormatEvidenceTool(BaseTool):
    name = "format_evidence_summary"
    description = (
        "Compiles evidence items from all triggered fraud patterns into a single "
        "deduplicated Markdown table. Columns: #, Evidence Item, Value, Benchmark, "
        "Pattern, Severity, Source. Sorted by severity (major first). "
        "Pure formatting — no LLM call."
    )

    async def execute(self, pattern_results: dict) -> str:
        rows: List[dict] = []
        seen: set = set()

        for pattern_key, result in pattern_results.items():
            if not isinstance(result, dict):
                continue
            pattern_label = pattern_key.replace("_", " ").title()
            for item in result.get("evidence", []):
                if not isinstance(item, dict):
                    continue
                # Deduplicate on indicator + value combination
                dedup_key = f"{item.get('indicator','')}|{item.get('value','')}"
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                rows.append({
                    "indicator": item.get("indicator", ""),
                    "value":     item.get("value", ""),
                    "benchmark": item.get("benchmark", "—"),
                    "pattern":   pattern_label,
                    "severity":  item.get("severity", "minor"),
                    "source":    item.get("source", "enriched data"),
                })

        if not rows:
            return "_No specific evidence items recorded._"

        # Sort by severity (major → moderate → minor)
        rows.sort(key=lambda r: SEVERITY_ORDER.get(r["severity"].lower(), 99))

        header = (
            "| # | Evidence Item | Value | Benchmark | Pattern | Severity | Source |\n"
            "|---|---------------|-------|-----------|---------|----------|--------|\n"
        )
        body = "\n".join(
            f"| {i+1} | {r['indicator']} | {r['value']} | {r['benchmark']} "
            f"| {r['pattern']} | **{r['severity'].upper()}** | {r['source']} |"
            for i, r in enumerate(rows)
        )
        return header + body


