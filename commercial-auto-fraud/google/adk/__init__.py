"""
Mock Google ADK Agent implementation.
Used because the real google.adk package is not publicly available.

The mock Agent.run() simulates realistic per-agent responses based on the
agent's name, deriving outputs from the enriched claim data passed in the prompt.
All spans are instrumented via the trace_llm_call decorator.
"""

import json
import re
from src.infrastructure.telemetry.arize_wrappers import trace_llm_call


class Agent:
    def __init__(self, name: str, model: str, instruction: str, tools: list = None):
        self.name  = name
        self.model = model
        self.instruction = instruction
        self.tools = tools or []

    @trace_llm_call
    async def run(self, prompt: str) -> str:
        print(f"[{self.name}] [{self.model}] Running... (prompt length: {len(prompt)} chars)")

        # Route by agent name (dedicated agents) OR by PATTERN: header in prompt
        # (shared fraud_pattern_analyzer uses YAML templates with distinct headers)
        prompt_upper = prompt[:600]

        # ── Duplicate / Similar Claims Pattern Analyzer ──────────────────────
        if "duplicate_similar" in self.name or "duplicate" in prompt_upper.lower():
            return self._analyze_duplicate(prompt)

        # ── Suspicious Timing Pattern Analyzer ───────────────────────────────
        elif "suspicious_timing" in self.name or "PATTERN: Suspicious Timing" in prompt_upper:
            return self._analyze_timing(prompt)

        # ── Inflated Amounts Pattern Analyzer ────────────────────────────────
        elif "inflated_amounts" in self.name or "PATTERN: Inflated Amounts" in prompt_upper:
            return self._analyze_inflated(prompt)

        # ── Provider Network Pattern Analyzer ─────────────────────────────────
        elif "provider_network" in self.name or "PATTERN: Provider Network" in prompt_upper:
            return self._analyze_provider_network(prompt)

        # ── Investigation Report Generator ───────────────────────────────────
        elif "report" in self.name or "FRAUD ANALYSIS:" in prompt_upper:
            return self._generate_report(prompt)

        # ── Composite Score CoT (narrative synthesis) ────────────────────────
        elif "composite" in self.name or "composite_score" in prompt_upper.lower():
            return json.dumps({"narrative": "Multiple fraud patterns flagged requiring coordinated SIU investigation."})

        return '{"status": "ok", "message": "Simulated ADK agent response"}'

    # ─────────────────────────────────────────────────────────────────────────
    # Pattern analyzers — derive realistic scores from enriched data in prompt
    # ─────────────────────────────────────────────────────────────────────────

    def _extract_json_block(self, prompt: str, key: str) -> dict:
        """Extracts the first JSON object following a labelled block in the prompt."""
        try:
            # Find the section after the key
            idx = prompt.find(key)
            if idx == -1:
                return {}
            snippet = prompt[idx + len(key):].strip()
            # Grab the first {...} block
            depth, start = 0, None
            for i, ch in enumerate(snippet):
                if ch == '{':
                    if start is None:
                        start = i
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0 and start is not None:
                        return json.loads(snippet[start:i+1])
        except Exception:
            pass
        return {}

    def _extract_claim_data(self, prompt: str) -> dict:
        """Pull ENRICHED DATA json block from prompt."""
        return self._extract_json_block(prompt, "ENRICHED DATA:")

    def _analyze_duplicate(self, prompt: str) -> str:
        data = self._extract_claim_data(prompt)
        # BasePatternTool._extract_pattern_data sends flat keys (not nested under claimant_history)
        prior_flags  = data.get("prior_fraud_flags", 0)
        prior_claims = data.get("total_prior_claims", 0)
        prior_vin    = data.get("prior_claims_on_vin", [])
        prior_list   = data.get("prior_claims", [])
        freq         = data.get("claim_frequency_per_year", 0)

        score = 0
        evidence = []
        if prior_flags > 0:
            score += 40
            evidence.append({"indicator": "Prior fraud flags on claimant", "value": str(prior_flags), "benchmark": "0", "severity": "major", "source": "claimant_history"})
        if prior_claims >= 3:
            score += 25
            evidence.append({"indicator": "High prior claim frequency", "value": str(prior_claims), "benchmark": "< 2", "severity": "moderate", "source": "claimant_history"})
        if prior_vin:
            score += 30
            evidence.append({"indicator": "Prior claims on same VIN", "value": str(len(prior_vin)), "benchmark": "0", "severity": "major", "source": "vehicle_valuation"})
        elif prior_list:
            score += 15
            evidence.append({"indicator": "Prior claims on record", "value": str(len(prior_list)), "benchmark": "0", "severity": "moderate", "source": "claimant_history"})
        if freq >= 2.0:
            score += 10
            evidence.append({"indicator": "High claim frequency", "value": f"{freq:.1f}/year", "benchmark": "< 1.0/year", "severity": "moderate", "source": "claimant_history"})
        if score == 0:
            evidence.append({"indicator": "No duplicate indicators found", "value": "0", "benchmark": "0", "severity": "clean", "source": "claimant_history"})

        severity = "critical" if score >= 80 else "significant" if score >= 60 else "notable" if score >= 40 else "minor" if score > 0 else "clean"
        return json.dumps({
            "pattern": "duplicate_similar",
            "score": min(score, 100),
            "severity": severity,
            "evidence": evidence,
            "reasoning": f"Claimant has {prior_flags} prior fraud flag(s), {prior_claims} total prior claims, frequency {freq:.1f}/yr, and {len(prior_vin)} prior claim(s) on this specific VIN.",
            "exculpatory_factors": [] if score > 0 else ["No matching VIN, claimant, or description indicators"]
        })

    def _analyze_timing(self, prompt: str) -> str:
        data = self._extract_claim_data(prompt)
        # BasePatternTool._extract_pattern_data sends flat keys (not nested under policy_details)
        days_since = data.get("days_since_inception", 999)
        changes    = data.get("recent_policy_changes", [])
        lapse      = data.get("lapse_history", [])

        score = 0
        evidence = []
        if days_since <= 30:
            score += 50
            evidence.append({"indicator": "Policy inception proximity", "value": f"{days_since} days since inception", "benchmark": "> 90 days", "severity": "major", "source": "policy_details"})
        if changes:
            score += 25
            change_detail = changes[0].get("details", "upgrade recorded") if isinstance(changes[0], dict) else str(changes[0])
            evidence.append({"indicator": "Coverage upgrade shortly before loss", "value": change_detail, "benchmark": "No recent changes", "severity": "major", "source": "policy_details"})
        if lapse:
            lapse_date = lapse[0].get("lapse_date", "N/A") if isinstance(lapse[0], dict) else str(lapse[0])
            score += 15
            evidence.append({"indicator": "Prior policy lapse and reinstatement", "value": f"Lapsed {lapse_date}", "benchmark": "No lapse history", "severity": "moderate", "source": "policy_details"})
        if score == 0:
            evidence.append({"indicator": "Policy well-established", "value": f"{days_since} days since inception", "benchmark": "> 90 days", "severity": "clean", "source": "policy_details"})

        severity = "critical" if score >= 80 else "significant" if score >= 60 else "notable" if score >= 40 else "minor" if score > 0 else "clean"
        return json.dumps({
            "pattern": "suspicious_timing",
            "score": min(score, 100),
            "severity": severity,
            "evidence": evidence,
            "reasoning": f"Policy was {days_since} days old at time of loss. {'Coverage upgrade recorded shortly before loss. ' if changes else ''}{'Prior lapse history detected.' if lapse else ''}",
            "exculpatory_factors": ["Long-standing policy with no changes"] if score == 0 else []
        })

    def _analyze_inflated(self, prompt: str) -> str:
        data = self._extract_claim_data(prompt)
        # BasePatternTool._extract_pattern_data sends flat keys (not nested under raw_claim/vehicle_valuation)
        claimed      = data.get("claimed_amount", 0)
        loss_type    = data.get("loss_type", "major_collision")
        market_value = data.get("market_value", 35000)
        benchmarks   = data.get("regional_repair_benchmarks", {})
        type_bench   = benchmarks.get(loss_type, {}) if isinstance(benchmarks, dict) else {}
        median_repair = type_bench.get("median", 15000) if isinstance(type_bench, dict) else 15000
        billing_ratio = data.get("billing_ratio", 1.0)

        score = 0
        evidence = []
        if claimed > market_value and market_value > 0:
            score += 50
            evidence.append({"indicator": "Claimed amount exceeds vehicle market value", "value": f"${claimed:,.0f}", "benchmark": f"Market value: ${market_value:,.0f}", "severity": "major", "source": "vehicle_valuation"})
        elif claimed > median_repair * 2:
            score += 35
            evidence.append({"indicator": "Claimed amount far exceeds repair benchmark", "value": f"${claimed:,.0f}", "benchmark": f"Median: ${median_repair:,.0f}", "severity": "major", "source": "vehicle_valuation"})
        elif claimed > median_repair * 1.5:
            score += 20
            evidence.append({"indicator": "Claimed amount above benchmark", "value": f"${claimed:,.0f}", "benchmark": f"Median: ${median_repair:,.0f}", "severity": "moderate", "source": "vehicle_valuation"})
        if billing_ratio and billing_ratio > 2.0:
            score += 15
            evidence.append({"indicator": "Provider billing ratio elevated", "value": f"{billing_ratio:.2f}x", "benchmark": "< 1.5x", "severity": "moderate", "source": "provider_network"})
        if score == 0:
            evidence.append({"indicator": "Claimed amount within regional benchmark", "value": f"${claimed:,.0f}", "benchmark": f"Median: ${median_repair:,.0f}", "severity": "clean", "source": "vehicle_valuation"})

        severity = "critical" if score >= 80 else "significant" if score >= 60 else "notable" if score >= 40 else "minor" if score > 0 else "clean"
        return json.dumps({
            "pattern": "inflated_amounts",
            "score": min(score, 100),
            "severity": severity,
            "evidence": evidence,
            "reasoning": f"Claimed amount ${claimed:,.0f} vs. vehicle market value ${market_value:,.0f} and regional median repair cost ${median_repair:,.0f} for {loss_type}.",
            "exculpatory_factors": ["Claimed amount within normal range"] if score == 0 else []
        })

    def _analyze_provider_network(self, prompt: str) -> str:
        data = self._extract_claim_data(prompt)
        # BasePatternTool._extract_pattern_data sends flat keys (not nested under provider_network)
        billing_ratio  = data.get("billing_ratio", 1.0) or 1.0
        license_status = data.get("license_status", "active") or "active"
        flagged_count  = data.get("flagged_claims_count", 0)
        referrals      = data.get("referral_connections", [])
        outside_area   = data.get("claims_outside_service_area", 0)

        score = 0
        evidence = []
        if license_status in ("expired", "suspended", "under_investigation"):
            score += 40
            evidence.append({"indicator": "Provider license status", "value": license_status, "benchmark": "active", "severity": "major", "source": "provider_network"})
        if billing_ratio > 2.0:
            score += 30
            evidence.append({"indicator": "Provider billing ratio", "value": f"{billing_ratio:.2f}x regional average", "benchmark": "< 1.5x", "severity": "major", "source": "provider_network"})
        if referrals:
            shared = referrals[0].get('shared_claims', 0) if isinstance(referrals[0], dict) else 0
            score += 15
            evidence.append({"indicator": "Cross-provider referral connections", "value": f"{len(referrals)} connection(s), {shared} shared claims", "benchmark": "0", "severity": "moderate", "source": "provider_network"})
        if outside_area > 5:
            score += 10
            evidence.append({"indicator": "Claims filed outside service area", "value": str(outside_area), "benchmark": "< 5", "severity": "minor", "source": "provider_network"})
        if score == 0:
            evidence.append({"indicator": "Provider within normal parameters", "value": f"billing_ratio={billing_ratio:.2f}", "benchmark": "< 1.5x", "severity": "clean", "source": "provider_network"})

        severity = "critical" if score >= 80 else "significant" if score >= 60 else "notable" if score >= 40 else "minor" if score > 0 else "clean"
        return json.dumps({
            "pattern": "provider_network",
            "score": min(score, 100),
            "severity": severity,
            "evidence": evidence,
            "reasoning": f"Provider license: {license_status}. Billing ratio: {billing_ratio:.2f}x. Referral connections: {len(referrals)}. Claims outside area: {outside_area}.",
            "exculpatory_factors": ["Licensed and billing within normal range"] if score == 0 else []
        })

    # ─────────────────────────────────────────────────────────────────────────
    # Investigation Report Generator
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_report(self, prompt: str) -> str:
        """Extract fraud_analysis JSON embedded in the prompt and build the Markdown report."""
        fraud = self._extract_json_block(prompt, "FRAUD ANALYSIS:")
        enriched = self._extract_json_block(prompt, "ENRICHED CLAIM DATA:")

        claim_id     = fraud.get("claim_id", "Unknown")
        score        = fraud.get("composite_score", 0)
        tier         = fraud.get("priority_tier", "low").upper()
        confidence   = fraud.get("confidence", "low")
        flagged      = fraud.get("patterns_flagged", 0)
        patterns     = fraud.get("pattern_results", {})
        raw          = enriched.get("raw_claim", enriched)
        claimant     = raw.get("claimant", {}).get("name", "Unknown")
        loss_date    = raw.get("loss_date", "Unknown")
        claimed      = raw.get("claimed_amount", 0)
        policy_num   = raw.get("policy_number", "Unknown")
        provider_info = enriched.get("provider_network", {})
        claimant_hist = enriched.get("claimant_history", {})

        # Build evidence table
        evidence_rows = ""
        row_num = 1
        for pat_name, pat_data in patterns.items():
            for ev in pat_data.get("evidence", []):
                if ev.get("severity", "clean") != "clean":
                    evidence_rows += (
                        f"| {row_num} | {ev.get('indicator','N/A')} | "
                        f"{ev.get('value','N/A')} | {ev.get('benchmark','N/A')} | "
                        f"{pat_name} | {ev.get('severity','N/A')} | {ev.get('source','N/A')} |\n"
                    )
                    row_num += 1
        if not evidence_rows:
            evidence_rows = "| — | No significant evidence flagged | — | — | — | — | — |\n"

        # Build pattern detail sections
        pattern_details = ""
        for pat_name, pat_data in patterns.items():
            pat_score = pat_data.get("score", 0)
            pat_sev   = pat_data.get("severity", "clean")
            if pat_score > 20:
                pattern_details += f"\n### Pattern: {pat_name.replace('_', ' ').title()} — Score: {pat_score}/100 — Severity: {pat_sev.upper()}\n"
                for ev in pat_data.get("evidence", []):
                    if ev.get("severity", "clean") != "clean":
                        pattern_details += f"- **{ev.get('indicator','N/A')}**: {ev.get('value','N/A')} (Benchmark: {ev.get('benchmark','N/A')})\n"
                pattern_details += f"\n*Reasoning*: {pat_data.get('reasoning', 'N/A')}\n"

        # Recommended actions based on evidence
        actions = []
        if claimant_hist.get("prior_fraud_flags", 0) > 0:
            actions.append(f"**Recorded Statement**: Schedule a recorded statement with {claimant} regarding prior fraud flags and claim history.")
        if provider_info.get("license_status") in ("expired", "suspended", "under_investigation"):
            actions.append(f"**Provider Audit**: Subpoena itemized invoices from **{provider_info.get('provider_name', 'provider')}** — license status: {provider_info.get('license_status')}.")
        if provider_info.get("billing_ratio", 1.0) > 2.0:
            actions.append(f"**Billing Review**: Compare provider billing against regional benchmarks — billing ratio is {provider_info.get('billing_ratio', 0):.2f}x regional average.")
        if not actions:
            actions.append("**Standard Review**: Verify claim documentation with standard SIU procedures.")

        actions_md = "\n".join(f"- {a}" for a in actions)

        report_md = f"""# Investigation Report: {claim_id}

## 1. Case Header
| Field | Value |
|-------|-------|
| Claim ID | {claim_id} |
| Claimant | {claimant} |
| Loss Date | {loss_date} |
| Claimed Amount | ${claimed:,.2f} |
| Policy Number | {policy_num} |
| Composite Fraud Score | **{score}** |
| Priority Tier | **{tier}** |
| Confidence Level | {confidence} |
| Patterns Flagged | {flagged} of 4 |

## 2. Executive Summary
Claim **{claim_id}** filed by **{claimant}** on **{loss_date}** for **${claimed:,.2f}** has been flagged by the Commercial Auto Fraud Detection Pipeline with a composite fraud score of **{score}** ({tier} priority). {flagged} of 4 fraud patterns triggered significant indicators requiring SIU review.

## 3. Pattern Analysis Detail
{pattern_details if pattern_details else "_No patterns exceeded the 20-point threshold._"}

## 4. Evidence Summary Table
| # | Evidence Item | Value | Benchmark | Pattern | Severity | Source |
|---|---------------|-------|-----------|---------|----------|--------|
{evidence_rows}

## 5. Recommended Actions
{actions_md}

## 6. Risk Factors
{self._build_risk_factors(patterns, claimant_hist, provider_info)}

## 7. Claimant & Provider Profile
- **Claimant Prior Claims**: {claimant_hist.get("total_prior_claims", 0)} (Fraud flags: {claimant_hist.get("prior_fraud_flags", 0)})
- **Provider License**: {provider_info.get("license_status", "N/A")} — Billing Ratio: {provider_info.get("billing_ratio", 0):.2f}x
- **Provider Flagged Claims**: {provider_info.get("flagged_claims_count", 0)} of {provider_info.get("total_claims_served", 0)} total
"""
        return report_md

    def _build_risk_factors(self, patterns: dict, claimant_hist: dict, provider_info: dict) -> str:
        factors = []
        for pat_name, pat_data in patterns.items():
            if pat_data.get("score", 0) >= 60:
                factors.append(f"- 🔴 **{pat_name.replace('_',' ').title()}** — Score {pat_data['score']}/100 ({pat_data.get('severity','').upper()})")
            elif pat_data.get("score", 0) >= 40:
                factors.append(f"- 🟡 **{pat_name.replace('_',' ').title()}** — Score {pat_data['score']}/100 ({pat_data.get('severity','').upper()})")
        if claimant_hist.get("prior_fraud_flags", 0) > 0:
            factors.insert(0, f"- 🔴 **Claimant has {claimant_hist['prior_fraud_flags']} prior fraud flag(s)** in claims history")
        return "\n".join(factors) if factors else "- ✅ No high-severity risk factors identified"


class UI:
    def run(self, agent: Agent):
        print(f"ADK Web UI started for {agent.name}")


ui = UI()
