"""
User Profile Service
---------------------
Loads investigator profiles (Kevin = junior, Diana = senior) and
provides profile-aware response formatting for the SIU Query Chat.

Profile-driven behavior:
  Kevin (junior):  Verbose narrative, definitions, step-by-step evidence, next steps.
  Diana (senior):  Concise tables, statistical anomalies, high-confidence flags only.
"""

import json
import os
import re
from datetime import datetime, timezone


PROFILES_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "fraud_data_store", "user_profiles"
)
REPORTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "fraud_data_store", "investigation_reports"
)

_cache: dict = {}


def load_profile(name: str) -> dict:
    """Load a user profile by first name (case-insensitive). Returns Kevin by default."""
    name = name.lower()
    if name in _cache:
        return _cache[name]
    path = os.path.join(PROFILES_DIR, f"{name}.json")
    if os.path.exists(path):
        with open(path) as f:
            profile = json.load(f)
    else:
        # Default to Kevin (junior) if unknown
        with open(os.path.join(PROFILES_DIR, "kevin.json")) as f:
            profile = json.load(f)
    _cache[name] = profile
    return profile


def format_batch_summary(batch_results: dict, profile: dict) -> str:
    """
    Format a batch summary differently for Kevin vs Diana.
    """
    results = batch_results.get("results", [])
    batch_id = batch_results.get("batch_id", "unknown")
    experience = profile.get("experience", "junior")
    threshold = profile.get("response_style", {}).get("threshold_filter", 0)

    # Filter for Diana
    if threshold:
        results = [r for r in results if r.get("fraud_analysis", {}).get("composite_score", 0) >= threshold]

    if experience == "senior":
        return _format_diana_summary(batch_id, results, batch_results)
    else:
        return _format_kevin_summary(batch_id, results, batch_results)


def _format_diana_summary(batch_id: str, results: list, full_batch: dict) -> str:
    all_results = full_batch.get("results", [])
    flagged = [r for r in all_results if r.get("fraud_analysis", {}).get("composite_score", 0) >= 60]

    lines = [
        f"**BATCH: {batch_id}** ({len(all_results)} claims analyzed)",
        f"**FLAGGED (≥60):** {len(flagged)} claims requiring immediate attention",
        "",
        "| Claim ID | Score | Tier | Patterns Triggered |",
        "|----------|-------|------|--------------------|",
    ]
    for r in results:
        fa = r.get("fraud_analysis", {})
        patterns = [
            k.replace("_", "/") for k, v in fa.get("pattern_results", {}).items()
            if v.get("score", 0) >= 40
        ]
        lines.append(
            f"| {r['claim_id']} | **{fa.get('composite_score',0)}** "
            f"| {fa.get('priority_tier','low').upper()} "
            f"| {', '.join(patterns) if patterns else 'None'} |"
        )

    # Cross-claim alert
    provider_counts: dict = {}
    for r in all_results:
        prov = r.get("enriched", {}).get("provider_network", {}).get("provider_id", "")
        if prov:
            provider_counts[prov] = provider_counts.get(prov, 0) + 1
    repeated = {k: v for k, v in provider_counts.items() if v > 1}
    if repeated:
        lines.append("")
        lines.append("**⚠ ALERT — Shared Providers Across Claims:**")
        for prov_id, count in repeated.items():
            lines.append(f"- Provider `{prov_id}` appears in **{count} claims** → Recommend law enforcement referral review")

    return "\n".join(lines)


def _format_kevin_summary(batch_id: str, results: list, full_batch: dict) -> str:
    all_results = full_batch.get("results", [])
    lines = [
        f"# Batch Analysis Complete: {batch_id}",
        f"**{len(all_results)} claims** were analyzed this week. Here's what you need to know:",
        "",
    ]
    for r in all_results:
        fa = r.get("fraud_analysis", {})
        score = fa.get("composite_score", 0)
        tier = fa.get("priority_tier", "low")
        icon = "🔴" if tier == "critical" else "🟠" if tier == "high" else "🟡" if tier == "medium" else "✅"
        lines.append(f"### {icon} Claim {r['claim_id']} — Fraud Score: {score} ({tier.upper()})")

        if score >= 40:
            lines.append("")
            lines.append("**Why this claim is suspicious:**")
            for pat_name, pat_data in fa.get("pattern_results", {}).items():
                if pat_data.get("score", 0) >= 40:
                    lines.append(f"- **{pat_name.replace('_', ' ').title()}** (sub-score: {pat_data['score']}/100): {pat_data.get('reasoning', '')[:200]}")
            lines.append("")
            lines.append("**What to investigate next:**")
            lines.append("- Review all prior claims linked to this claimant in the claims database")
            lines.append("- Request itemized invoices from the service provider")
            lines.append("- Schedule a recorded statement with the claimant")
        else:
            lines.append(f"  ✅ Score below threshold — no immediate action required.")
        lines.append("")

    return "\n".join(lines)


def _format_top_pattern(results: list, experience: str) -> str:
    """Which single fraud pattern triggered most often across all claims?"""
    counts: dict = {}
    for r in results:
        for pat_key, pat_data in r.get("fraud_analysis", {}).get("pattern_results", {}).items():
            if pat_data.get("score", 0) >= 40:
                counts[pat_key] = counts.get(pat_key, 0) + 1
    if not counts:
        return "No patterns triggered above threshold (40) in this batch."
    top_key = max(counts, key=counts.__getitem__)
    top_label = top_key.replace("_", " ").title()
    if experience == "senior":
        lines = [f"Top pattern: **{top_label}** — triggered in {counts[top_key]} claim(s)"]
        for k, v in sorted(counts.items(), key=lambda x: -x[1]):
            lines.append(f"- {k.replace('_',' ').title()}: {v} claim(s)")
        return "\n".join(lines)
    return (
        f"The most common fraud pattern this week is **{top_label}**, "
        f"which triggered in **{counts[top_key]}** claims.\n\n"
        "Pattern frequency breakdown:\n" +
        "\n".join(f"- {k.replace('_',' ').title()}: {v} claim(s)" for k, v in sorted(counts.items(), key=lambda x: -x[1]))
    )


def answer_siu_query(query: str, batch_results: dict, profile: dict) -> str:
    """
    Rule-based SIU query handler covering all 6 spec query types.
    Type 1 (pipeline status) is handled upstream in QueryResultsTool.
    """
    q = query.lower()
    results = batch_results.get("results", [])
    experience = profile.get("experience", "junior")
    name = profile.get("name", "Investigator")

    # 2. Batch Summary
    if any(kw in q for kw in ["summary", "show me", "show results", "results",
                                "batch", "this week", "overview", "how many fraud"]):
        return format_batch_summary(batch_results, profile)

    # 7. Terminology Glossary — must run BEFORE pattern/provider filters
    #    so "what does provider network anomaly mean" hits here, not the provider filter.
    _GLOSSARY = {
        "provider network anomaly": (
            "A **provider network anomaly** flags suspicious behavior by the service provider "
            "(repair shop, medical clinic, tow company) rather than the claimant.\n\n"
            "The system checks 4 things:\n"
            "1. **Billing deviation** \u2014 Is the provider billing 2x+ the regional average? "
            "Most legitimate shops bill within \u00b130% of the regional median.\n"
            "2. **Batch concentration** \u2014 Does this provider appear on multiple claims in one batch? "
            "A single shop on 4 of 12 claims (33%) is a major ring indicator.\n"
            "3. **Referral ring** \u2014 Does the provider have circular referral connections with tow companies, "
            "attorneys, or other shops? Fraud rings steer customers to inflate estimates.\n"
            "4. **License status** \u2014 Is the provider licensed and compliant, or under investigation?\n\n"
            "**Key takeaway:** When you see a provider flag, always check if the same provider appears "
            "on other recent claims \u2014 that's where rings are found."
        ),
        "composite score": (
            "The **composite fraud score** (0\u2013100) is a weighted combination of 4 pattern sub-scores:\n"
            "- Duplicate/Similar Claims: **30%** weight\n"
            "- Suspicious Timing: **20%** weight\n"
            "- Inflated Amounts: **25%** weight\n"
            "- Provider Network: **25%** weight\n\n"
            "Tiers: **Low** (<40) \u2022 **Medium** (40\u201359) \u2022 **High** (60\u201379) \u2022 **Critical** (80+)"
        ),
        "duplicate": (
            "A **duplicate/similar claim** flag means the system found another claim with the same "
            "or overlapping vehicle VIN, claimant, loss type, or repair shop as a prior claim.\n\n"
            "Red flags include: same VIN on 2+ claims within 24 months, same claimant at the same "
            "repair shop, or suspiciously similar damage descriptions and amounts."
        ),
        "timing": (
            "A **suspicious timing** flag means the loss occurred unusually close to a policy event.\n\n"
            "Common signals: claim filed within 30 days of policy inception (new-policy fraud), "
            "coverage upgraded within 72 hours before the loss (pre-planned fraud), "
            "policy lapsed and reinstated within weeks before the claim, or "
            "Friday-evening incidents reported Monday morning (staged window)."
        ),
        "inflated": (
            "An **inflated amounts** flag means the claimed costs significantly exceed benchmarks.\n\n"
            "The system compares claimed amounts against: vehicle market value "
            "(claims exceeding 75% of market value trigger total-loss thresholds), "
            "regional repair medians by damage type, and historical billing from the same provider.\n\n"
            "Example: A $42,000 repair on a $29,500 vehicle = 1.42x market value = major red flag."
        ),
        "euo": (
            "**EUO (Examination Under Oath)** is a formal recorded statement given by a claimant "
            "or witness under oath, similar to a deposition. SIU investigators use EUOs to get "
            "detailed testimony about the incident, prior claims, and provider relationships. "
            "Inconsistencies between the EUO and claim documents are strong fraud indicators."
        ),
        "nicb": (
            "**NICB (National Insurance Crime Bureau)** is a non-profit that works with insurers and "
            "law enforcement to detect fraud. Submitting a claim to NICB runs it against a "
            "cross-carrier database to find the same claimant, VIN, or provider appearing across "
            "multiple insurance companies \u2014 a key tool for spotting organized rings."
        ),
        "cfe": (
            "**CFE (Certified Fraud Examiner)** is a professional credential from the ACFE. "
            "CFEs are trained in fraud detection, evidence collection, and legal/compliance frameworks. "
            "Senior SIU leads like Diana often hold this certification."
        ),
    }
    _is_definition_query = any(kw in q for kw in [
        "what does", "what is", "what are", "explain", "mean", "definition"
    ])
    if _is_definition_query:
        for term, definition in _GLOSSARY.items():
            if term.split()[0] in q:
                return definition.split("\n")[0] if experience == "senior" else definition

    # 8. Claim status update (Diana workflow) \u2014 must run BEFORE claim drill-down
    #    so "Flag CLM-X for law enforcement" routes here, not to _format_claim_drilldown.
    _is_update = any(kw in q for kw in [
        "add notes", "add note", "law enforcement", "referral",
        "link to", "cross-link", "mark as", "escalate",
    ]) or ("flag" in q and any(kw in q for kw in ["enforcement", "referral", "link", "notes", "escalate"]))
    if _is_update and results:
        return _handle_status_update(query, q, results, profile, batch_results)

    # 9. "Critical only" / "show all" filter shortcut
    if any(kw in q for kw in ["critical only", "only critical", "show critical", "criticals"]):
        criticals = [r for r in results if r.get("fraud_analysis", {}).get("priority_tier") == "critical"]
        if not criticals:
            return "No CRITICAL-tier claims in this batch."
        if experience == "senior":
            lines = [f"**CRITICAL ONLY \u2014 {len(criticals)} claim(s):**", ""]
            lines += ["| Claim ID | Score | Primary Pattern | Action |",
                      "|----------|-------|-----------------|--------|"]  
            for r in criticals:
                fa = r["fraud_analysis"]
                top_pat = max(fa.get("pattern_results", {}).items(),
                              key=lambda kv: kv[1].get("score", 0), default=("", {}))
                lines.append(f"| {r['claim_id']} | **{fa['composite_score']}** "
                             f"| {top_pat[0].replace('_',' ').title()} "
                             f"| Deep investigation |")
            remaining = len(results) - len(criticals)
            if remaining:
                lines.append(f"\n{remaining} additional claims scored below CRITICAL. Say \"show all\" to see full results.")
            return "\n".join(lines)
        return format_batch_summary(batch_results, profile)

    if "show all" in q:
        return format_batch_summary(batch_results, profile)

    # 3. Claim Drill-Down - highest-scoring shortcut
    if any(kw in q for kw in ["highest", "worst", "top claim", "most suspicious"]):
        if results:
            top = max(results, key=lambda r: r.get("fraud_analysis", {}).get("composite_score", 0))
            return _format_claim_drilldown(top, experience)

    # 3. Claim Drill-Down - exact CLM-ID or partial "claim N"
    claim_match = None
    for r in results:
        if r["claim_id"].lower() in q:
            claim_match = r
            break
    if not claim_match:
        for r in results:
            suffix = r["claim_id"].split("-")[-1].lstrip("0")
            if suffix and ("claim " + suffix in q or "clm " + suffix in q):
                claim_match = r
                break
    if claim_match:
        return _format_claim_drilldown(claim_match, experience)

    # 4. Pattern Filter
    if "most common" in q or "top pattern" in q:
        return _format_top_pattern(results, experience)
    if "duplicate" in q or "similar claim" in q:
        return _format_pattern_query(results, "duplicate_similar", experience)
    if any(kw in q for kw in ["timing", "inception", "lapse", "reinstate", "coverage change"]):
        return _format_pattern_query(results, "suspicious_timing", experience)
    if any(kw in q for kw in ["inflat", "amount", "overcharg", "market value", "benchmark"]):
        return _format_pattern_query(results, "inflated_amounts", experience)
    if any(kw in q for kw in ["network", "ring", "referral", "provider network", "circular"]):
        return _format_pattern_query(results, "provider_network", experience)

    # 5. Provider Analysis
    if any(kw in q for kw in ["provider", "shop", "repair", "medical", "towing",
                                "multiple times", "frequency", "billing"]):
        return _format_provider_query(results, experience)

    # 6. Explanation
    if any(kw in q for kw in ["explain", "what is", "what does", "how is", "how does",
                                "calculated", "score mean", "confidence", "tier", "composite"]):
        if experience == "senior":
            return (
                "Composite = Dup x0.30 + Timing x0.20 + Inflated x0.25 + Network x0.25. "
                "Thresholds: 40 (SIU flag), 60 (open file), 80 (immediate escalation). "
                "Confidence: High = 3+ patterns flagged, Medium = 2, Low <= 1."
            )
        return (
            "Hi " + name + "! The Composite Fraud Score combines 4 pattern analyses:\n\n"
            "| Pattern | Weight | What It Detects |\n"
            "|---------|--------|-----------------|\n"
            "| Duplicate/Similar Claims | 30% | Same claimant, policies, or VIN across claims |\n"
            "| Suspicious Timing | 20% | Claims near policy inception, upgrades, or lapse |\n"
            "| Inflated Amounts | 25% | Costs above benchmarks or vehicle market value |\n"
            "| Provider Network | 25% | Billing rings, circular referrals, expired licenses |\n\n"
            "Tiers: Low (<40) / Medium (40-59) / High (60-79) / Critical (80+)\n"
            "Confidence: High = 3+ patterns flagged, Medium = 2, Low = 0-1."
        )

    return (
        "I can help with: batch summary, claim details (e.g. tell me about CLM-2026-001 "
        "or why was claim 3 flagged), pattern filters (which claims had timing issues), "
        "provider analysis, most common pattern, score explanations, or terminology "
        "(e.g. 'what does provider network anomaly mean?').\n\n"
        "For Senior mode: 'flag CLM-X for law enforcement. Add notes: ... Link to CLM-Y.'"
    )

def _format_claim_drilldown(r: dict, experience: str) -> str:
    fa = r.get("fraud_analysis", {})
    patterns = fa.get("pattern_results", {})
    score = fa.get("composite_score", 0)
    tier = fa.get("priority_tier", "low").upper()
    claimant = r.get("enriched", {}).get("raw_claim", {}).get("claimant", {}).get("name", "")
    amount = r.get("enriched", {}).get("raw_claim", {}).get("claimed_amount", 0)

    if experience == "senior":
        # Spec §18.2 format: concise pattern×evidence table + cross-claim links
        lines = [
            f"**{r['claim_id']}** — {claimant} | Score: {score} | {tier} | Patterns flagged: {fa.get('patterns_flagged', 0)}/4",
            "",
            "| Pattern | Score | Evidence |",
            "|---------|-------|----------|",
        ]
        for pat, data in patterns.items():
            pat_score = data.get("score", 0)
            # Use flags[] if present (spec §15.3), else first evidence item
            flags = data.get("flags", [])
            evidence_str = flags[0] if flags else (data.get("evidence", [{}])[0].get("value", "N/A") if data.get("evidence") else "N/A")
            lines.append(
                f"| {pat.replace('_', ' ').title()} | **{pat_score}** | {evidence_str[:100]} |"
            )
        # Cross-claim link detection
        prov_id = r.get("enriched", {}).get("provider_network", {}).get("provider_id", "")
        if prov_id:
            lines.append(f"\nCross-claim links: Provider `{prov_id}` — check if shared with other batch claims.")
        if fa.get("narrative"):
            lines.append(f"\n*Narrative: {fa['narrative'][:200]}*")
        return "\n".join(lines)
    else:
        # Kevin format: full pattern breakdown with definitions
        lines = [
            f"# Claim {r['claim_id']} — Detailed Investigation Summary",
            f"**Claimant:** {claimant} | **Claimed:** ${amount:,.2f} | "
            f"**Score:** {score}/100 | **Priority:** {tier}",
            "",
            "## Pattern-by-Pattern Analysis:",
        ]
        for pat, data in patterns.items():
            pat_score = data.get("score", 0)
            icon = "🔴" if pat_score >= 60 else "🟡" if pat_score >= 40 else "✅"
            lines.append(f"\n{icon} **{pat.replace('_', ' ').title()}** — {pat_score}/100")
            reasoning = data.get("reasoning", "") or "Analysis complete."
            lines.append(f"  *{reasoning[:300]}*")
            for ev in data.get("evidence", [])[:3]:
                if ev.get("severity", "clean") != "clean":
                    lines.append(
                        f"  - {ev.get('indicator', 'N/A')}: **{ev.get('value', 'N/A')}** "
                        f"(Benchmark: {ev.get('benchmark', 'N/A')})"
                    )
        lines.append("\n**Recommended Investigative Actions:**")
        lines.append("- Request a recorded statement from the claimant")
        lines.append("- Subpoena repair invoices and medical records from the provider")
        lines.append("- Cross-reference the provider against all other batch claims")
        if fa.get("narrative"):
            lines.append(f"\n**AI Summary:** {fa['narrative'][:250]}")
        return "\n".join(lines)


def _handle_status_update(query: str, q: str, results: list,
                           profile: dict, batch_results: dict) -> str:
    """
    Handles Diana-style update commands from §18.2:
      'Flag CLM-X for law enforcement referral. Add notes: ... Link to CLM-Y.'
    Persists status + notes to fraud_data_store/investigation_reports/{CLM-ID}.json.
    """
    investigator = profile.get("name", "Investigator")
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Find the target claim ID in the query
    claim_ids = re.findall(r'clm[-\s]?\d{4}[-\s]?\d{3,}', q, re.IGNORECASE)
    if not claim_ids:
        # Try matching any result claim ID substring
        for r in results:
            if r["claim_id"].lower() in q:
                claim_ids.append(r["claim_id"])
                break
    if not claim_ids:
        return "Could not identify which claim to update. Please include the Claim ID (e.g. CLM-2026-001)."

    primary_id = claim_ids[0].upper().replace(" ", "-")
    linked_ids = [cid.upper().replace(" ", "-") for cid in claim_ids[1:]]

    # Determine new status
    status = "Law Enforcement Referral" if "law enforcement" in q else \
             "SIU Escalated" if "escalat" in q else \
             "Under Investigation" if "investigat" in q else "Flagged"

    # Extract notes from query (text after 'notes:' or 'note:')
    notes_match = re.search(r'(?:notes?|note):?\s*(.+?)(?:\.|link to|$)', query, re.IGNORECASE | re.DOTALL)
    notes_text = notes_match.group(1).strip() if notes_match else ""
    full_note = f"{notes_text} —{investigator}, {now_str}" if notes_text else f"Status updated. —{investigator}, {now_str}"

    # Persist to JSON file
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_path = os.path.join(REPORTS_DIR, f"{primary_id}.json")
    try:
        if os.path.exists(report_path):
            with open(report_path, encoding="utf-8") as f:
                report_data = json.load(f)
        else:
            report_data = {"claim_id": primary_id, "history": []}

        report_data["status"] = status
        report_data["last_updated"] = datetime.now(timezone.utc).isoformat()
        report_data["updated_by"] = investigator
        report_data.setdefault("notes", []).append(full_note)
        if linked_ids:
            report_data.setdefault("cross_linked_claims", []).extend(linked_ids)
            report_data["cross_linked_claims"] = list(set(report_data["cross_linked_claims"]))

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        persisted = True
    except Exception:
        persisted = False

    # Build confirmation message
    confirm_lines = [f"Updated **{primary_id}**:\n"]
    confirm_lines.append(f"\u2705 Status \u2192 {status}")
    if notes_text:
        confirm_lines.append(f"\u2705 Notes added: \"{full_note}\"")
    if linked_ids:
        confirm_lines.append(f"\u2705 Cross-linked with: {', '.join(linked_ids)}")
    if not persisted:
        confirm_lines.append("\u26a0 Note: Could not write to report file — update is in-memory only.")
    confirm_lines.append("\nAnything else on this batch?")
    return "\n".join(confirm_lines)


def _format_provider_query(results: list, experience: str) -> str:
    provider_counts: dict = {}
    for r in results:
        prov = r.get("enriched", {}).get("provider_network", {})
        pid = prov.get("provider_id", "")
        pname = prov.get("provider_name", pid)
        ratio = prov.get("billing_ratio", 1.0)
        if pid:
            provider_counts[pid] = provider_counts.get(pid, {"name": pname, "count": 0, "ratio": ratio})
            provider_counts[pid]["count"] += 1

    if experience == "senior":
        lines = ["| Provider ID | Name | Claims | Billing Ratio |", "|-------------|------|--------|---------------|"]
        for pid, info in sorted(provider_counts.items(), key=lambda x: -x[1]["count"]):
            lines.append(f"| {pid} | {info['name']} | {info['count']} | {info['ratio']:.2f}x |")
        return "\n".join(lines)
    else:
        lines = ["# Provider Analysis\n", "Here are all service providers that appeared in this week's claims:\n"]
        for pid, info in sorted(provider_counts.items(), key=lambda x: -x[1]["count"]):
            flag = "⚠️ **FLAGGED**" if info["ratio"] > 2.0 else "✅ Clean"
            lines.append(f"- **{info['name']}** (`{pid}`): {info['count']} claim(s), billing ratio {info['ratio']:.2f}x {flag}")
        return "\n".join(lines)


def _format_pattern_query(results: list, pattern_key: str, experience: str) -> str:
    flagged = [
        r for r in results
        if r.get("fraud_analysis", {}).get("pattern_results", {}).get(pattern_key, {}).get("score", 0) >= 40
    ]
    pat_label = pattern_key.replace("_", " ").title()

    if experience == "senior":
        if not flagged:
            return f"No claims flagged for {pat_label} (threshold: 40)."
        lines = [f"**{pat_label} — {len(flagged)} claim(s) flagged:**\n"]
        lines += [f"- {r['claim_id']}: {r['fraud_analysis']['pattern_results'][pattern_key].get('score',0)}/100" for r in flagged]
        return "\n".join(lines)
    else:
        if not flagged:
            return f"Good news — no claims were flagged for the **{pat_label}** pattern this week."
        lines = [f"# {pat_label} — {len(flagged)} claim(s) flagged\n"]
        for r in flagged:
            pat_data = r["fraud_analysis"]["pattern_results"][pattern_key]
            lines.append(f"## Claim {r['claim_id']} — Score: {pat_data.get('score',0)}/100")
            lines.append(f"**What this means:** {pat_data.get('reasoning','N/A')[:300]}")
            for ev in pat_data.get("evidence", [])[:3]:
                lines.append(f"- {ev.get('indicator','N/A')}: {ev.get('value','N/A')}")
            lines.append("")
        return "\n".join(lines)


