DUPLICATE_SIMILAR_COT_PROMPT = """PATTERN: Duplicate / Similar Claims
CLAIM: {claim_id} — {claimant_name} — {loss_date} — ${claimed_amount}

ENRICHED DATA PROVIDED:
{enriched_data}

EVALUATE this claim for Duplicate/Similar Claims fraud indicators using step-by-step reasoning:

Step 1: Identify all relevant data points for this pattern
  - Check for matching VINs across claims, similar loss descriptions, overlapping loss dates within 30 days, same claimant filing across policies.

Step 2: Assess each indicator
  - Identify if each is a red flag (suspicious), neutral, or exculpatory.

Step 3: Weigh the evidence
  - Consider whether multiple minor flags combine into a significant concern.

Step 4: Score the pattern (0-100)
  - 0-20: Clean, 21-40: Minor, 41-60: Notable, 61-80: Significant, 81-100: Critical

Step 5: Compile evidence list
  - List evidence items with values and sources.

OUTPUT FORMAT:
Return ONLY a valid JSON object matching this structure (no markdown blocks or backticks):
{{
  "pattern": "duplicate_similar",
  "score": 0,
  "severity": "clean",
  "evidence": [
    {{"indicator": "...", "value": "...", "benchmark": "...", "severity": "...", "source": "..."}}
  ],
  "reasoning": "...",
  "exculpatory_factors": ["..."]
}}"""

SUSPICIOUS_TIMING_COT_PROMPT = """PATTERN: Suspicious Timing
CLAIM: {claim_id} — {claimant_name} — {loss_date} — ${claimed_amount}

ENRICHED DATA PROVIDED:
{enriched_data}

EVALUATE this claim for Suspicious Timing fraud indicators using step-by-step reasoning:

Step 1: Identify all relevant data points for this pattern
  - Claim within 30 days of inception, 60 days of expiration, Friday night/Monday morning, within 72 hours of coverage upgrade.

Step 2: Assess each indicator
Step 3: Weigh the evidence
Step 4: Score the pattern (0-100)
Step 5: Compile evidence list

OUTPUT FORMAT:
Return ONLY a valid JSON object matching this structure (no markdown blocks or backticks):
{{
  "pattern": "suspicious_timing",
  "score": 0,
  "severity": "clean",
  "evidence": [],
  "reasoning": "...",
  "exculpatory_factors": []
}}"""

INFLATED_AMOUNTS_COT_PROMPT = """PATTERN: Inflated Amounts
CLAIM: {claim_id} — {claimant_name} — {loss_date} — ${claimed_amount}

ENRICHED DATA PROVIDED:
{enriched_data}

EVALUATE this claim for Inflated Amounts fraud indicators using step-by-step reasoning:

Step 1: Identify all relevant data points for this pattern
  - Repair estimate exceeds market value, repair cost >2x regional benchmark, medical billing disproportionate to injury.

Step 2: Assess each indicator
Step 3: Weigh the evidence
Step 4: Score the pattern (0-100)
Step 5: Compile evidence list

OUTPUT FORMAT:
Return ONLY a valid JSON object matching this structure (no markdown blocks or backticks):
{{
  "pattern": "inflated_amounts",
  "score": 0,
  "severity": "clean",
  "evidence": [],
  "reasoning": "...",
  "exculpatory_factors": []
}}"""

PROVIDER_NETWORK_COT_PROMPT = """PATTERN: Provider Network Anomalies
CLAIM: {claim_id} — {claimant_name} — {loss_date} — ${claimed_amount}

ENRICHED DATA PROVIDED:
{enriched_data}

EVALUATE this claim for Provider Network Anomalies fraud indicators using step-by-step reasoning:

Step 1: Identify all relevant data points for this pattern
  - Provider appears on >15% of claims, billing average >2x regional mean, circular referrals, license issues.

Step 2: Assess each indicator
Step 3: Weigh the evidence
Step 4: Score the pattern (0-100)
Step 5: Compile evidence list

OUTPUT FORMAT:
Return ONLY a valid JSON object matching this structure (no markdown blocks or backticks):
{{
  "pattern": "provider_network",
  "score": 0,
  "severity": "clean",
  "evidence": [],
  "reasoning": "...",
  "exculpatory_factors": []
}}"""

