# Mock Google ADK — Detailed Documentation

This document explains the mock `google.adk` package that simulates the real Google Agent Development Kit for local development.

---

## 1. Why a Mock ADK?

The real `google.adk` package (Google's Agent Development Kit for Gemini) is used in production to call the Gemini API. During development/testing, we use a mock that:
- Returns **deterministic, data-driven responses** (no API calls needed)
- Derives realistic fraud scores from the actual enriched claim data in the prompt
- Generates structured investigation reports from pattern results
- Is instrumented with the same Arize telemetry as the real agent would be

### Location
```
google/
└── adk/
    └── __init__.py    # Mock Agent class (354 lines)
```

Python sees this as `google.adk` because the `google/` directory is on the Python path.

---

## 2. Agent Class

```python
class Agent:
    def __init__(self, name, model, instruction, tools=None):
        self.name = name        # e.g., "fraud_pattern_analyzer"
        self.model = model      # e.g., "gemini-2.5-pro"
        self.instruction = instruction
        self.tools = tools or []

    @trace_llm_call          # Creates an LLM span in Arize
    async def run(self, prompt: str) -> str:
        # Route to the appropriate mock analyzer based on prompt content
        ...
```

### Routing Logic
The `run()` method examines the prompt content to determine which mock analyzer to call. It checks the `PATTERN:` header from the YAML templates:

| Prompt Contains | Routes To | Returns |
|----------------|-----------|---------|
| `"duplicate"` in prompt | `_analyze_duplicate()` | JSON with score 0-100 |
| `"PATTERN: Suspicious Timing"` | `_analyze_timing()` | JSON with score 0-100 |
| `"PATTERN: Inflated Amounts"` | `_analyze_inflated()` | JSON with score 0-100 |
| `"PATTERN: Provider Network"` | `_analyze_provider_network()` | JSON with score 0-100 |
| `"report"` in agent name | `_generate_report()` | Markdown report string |
| None match | Generic JSON response | `{"status": "ok"}` |

---

## 3. Pattern Analyzer Mocks

Each pattern analyzer mock:
1. Extracts the `ENRICHED DATA:` JSON block from the prompt
2. Reads specific fields from the flat data structure
3. Applies deterministic scoring rules based on those fields
4. Returns a JSON response matching the `PatternResult` schema

### `_analyze_duplicate()` — Duplicate/Similar Claims
**Scoring rules**:
- `prior_fraud_flags >= 2` → +40 points
- `prior_fraud_flags == 1` → +20 points
- `total_prior_claims >= 4` → +30 points
- `total_prior_claims >= 2` → +15 points
- `claim_frequency >= 2.0/year` → +20 points
- `claim_frequency >= 1.5/year` → +10 points

### `_analyze_timing()` — Suspicious Timing
**Scoring rules**:
- `days_since_inception <= 15` → +35 points
- `days_since_inception <= 30` → +25 points
- `days_since_inception <= 60` → +15 points
- `recent_policy_changes` exist → +25 points
- `lapse_history` exists → +15 points

### `_analyze_inflated()` — Inflated Amounts
**Scoring rules**:
- `claimed_amount > market_value` → +35 points
- `claimed_amount > market_value * 0.7` → +20 points
- `claimed_amount > 2x median repair benchmark` → +30 points
- `billing_ratio > 2.0` → +15 points
- `billing_ratio > 1.5` → +10 points

### `_analyze_provider_network()` — Provider Network Anomalies
**Scoring rules**:
- `license_status` = "revoked"/"suspended"/"under_investigation" → +35 points
- `billing_ratio > 2.5` → +25 points
- `billing_ratio > 1.5` → +15 points
- `referral_connections` with `shared_claims > 10` → +20 points
- `claims_outside_service_area > 10` → +15 points

### Evidence Generation
Each analyzer also generates evidence items that explain WHY the score is what it is:
```json
{
  "indicator": "Provider under investigation",
  "value": "under_investigation",
  "benchmark": "active",
  "severity": "critical",
  "source": "provider_network"
}
```

---

## 4. Report Generator Mock (`_generate_report()`)

When the prompt contains `FRAUD ANALYSIS:` and `ENRICHED CLAIM DATA:` blocks, the mock:
1. Extracts both JSON blocks from the prompt
2. Reads claim metadata, pattern results, and evidence
3. Builds a complete 7-section Markdown report with actual data values

---

## 5. Helper Methods

| Method | Purpose |
|--------|---------|
| `_extract_claim_data(prompt)` | Extracts the `ENRICHED DATA:` JSON block from a pattern prompt |
| `_extract_json_block(prompt, marker)` | Generic JSON block extractor for any marker string |
| `_safe_float(value, default)` | Safe float conversion with fallback |

---

## 6. Switching to Real Gemini

To switch from mock to real Gemini API:

1. Install the real `google-adk` package
2. Remove the `google/` directory from the project
3. Set `GEMINI_API_KEY` in `.env`
4. The `LLMProvider` in `src/infrastructure/llm/provider.py` will now import the real `Agent` class
5. **Zero changes needed** in any agent module — they all go through `LLMProvider`

---

## 7. Config & Settings (`src/config/`)

### `settings.py` — Environment Configuration
All config loaded from `.env` with sensible defaults:

| Setting | Default | Purpose |
|---------|---------|---------|
| `FRAUD_DEFAULT_MODEL` | `gemini-2.5-pro` | Default LLM model |
| `FRAUD_ENRICHMENT_MODEL` | `gemini-2.5-flash` | Enrichment agent model (speed) |
| `FRAUD_ANALYZER_MODEL` | `gemini-2.5-pro` | Analyzer model (reasoning) |
| `FRAUD_REPORT_MODEL` | `gemini-2.5-flash` | Report model (formatting) |
| `ARIZE_SPACE_ID` / `ARIZE_API_KEY` | empty | Arize AX telemetry credentials |
| `REPORT_SCORE_THRESHOLD` | `40.0` | Minimum score to generate investigation report |
| `HIGH_TIER_THRESHOLD` | `60.0` | Score threshold for "High" tier |
| `CRITICAL_TIER_THRESHOLD` | `80.0` | Score threshold for "Critical" tier |

### `container.py` — Dependency Injection Container
Single wiring point for all dependencies:

```python
class Container:
    def __init__(self):
        # Infrastructure
        self.storage = LocalStorageRepository()
        self.data_provider = MockEnrichmentProvider()

        # A2A transport clients
        self.enrichment_client = A2AEnrichmentClient()
        self.analyzer_client = A2AAnalyzerClient()
        self.report_client = A2AReportGeneratorClient()

        # Top-level agent (everything injected)
        self.orchestrator = OrchestratorAgent(
            enrichment_client=self.enrichment_client,
            analyzer_client=self.analyzer_client,
            report_client=self.report_client,
            storage=self.storage,
        )
```

To swap any component (e.g., real database): change ONE line here. Nothing else.
