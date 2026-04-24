# Prompt Manager — Detailed Documentation

This document covers the versioned prompt management system used by all agents.

---

## 1. Why a Prompt Manager?

In an LLM-based system, prompts are as important as code. They need:
- **Versioning** — Track changes, roll back to previous versions
- **A/B Testing** — Run v1 vs v2 of a prompt to compare quality
- **Centralization** — One place to find and edit all prompts
- **Auditability** — Log which prompt version was used for each LLM call

The `PromptFacade` provides all of this.

---

## 2. Architecture

```
src/prompt_manager/
├── engine/
│   └── facade.py          # PromptFacade — the single access point
├── storage/
│   └── prompts/           # 11 versioned YAML prompt directories
│       ├── duplicate_similar_cot/
│       │   └── v1.yaml    # Chain-of-Thought prompt for duplicate detection
│       ├── suspicious_timing_cot/
│       │   └── v1.yaml
│       ├── inflated_amounts_cot/
│       │   └── v1.yaml
│       ├── provider_network_cot/
│       │   └── v1.yaml
│       ├── composite_score_cot/
│       │   └── v1.yaml    # Weighted scoring narrative
│       ├── enrichment_react/
│       │   └── v1.yaml    # ReAct pattern for data gathering
│       ├── investigation_report/
│       │   └── v1.yaml    # 7-section report template
│       ├── orchestrator_system/
│       │   └── v1.yaml    # Orchestrator system instruction
│       ├── kevin_query/
│       │   └── v1.yaml    # Junior analyst query persona
│       ├── diana_query/
│       │   └── v1.yaml    # Senior SIU lead query persona
│       └── fraud_classification_fewshot/
│           └── v1.yaml    # Few-shot FLAGGED/CLEAN classifier
└── templates/             # Python fallback constants
    ├── chain_of_thought.py  # CoT prompt strings
    ├── react.py             # ReAct prompt strings
    └── report.py            # Report prompt strings
```

---

## 3. PromptFacade — How It Works

### Loading Priority
```
1. YAML file: storage/prompts/{name}/v{N}.yaml  (preferred)
2. Python constant fallback (backward compat)
3. ValueError if neither found
```

### Usage
```python
# Basic usage — loads latest version
prompt = PromptFacade.get_prompt("duplicate_similar_cot", {
    "claim_id": "CLM-2026-001",
    "claimant_name": "Marcus Rivera",
    "loss_date": "2026-04-11",
    "claimed_amount": "42000",
    "enriched_data": json.dumps(data_slice),
})

# Pin a specific version (for A/B testing)
prompt = PromptFacade.get_prompt("duplicate_similar_cot", context, version="1")
```

### Key Functions

| Function | What It Does |
|----------|-------------|
| `get_prompt(name, context, version)` | Load + format prompt template with variables |
| `get_last_usage()` | Returns `{template, version, timestamp}` for Arize span attributes |
| `get_usage_log()` | Full audit trail of all prompt usages |
| `list_prompts()` | All registered prompt keys |
| `get_version_info(name)` | YAML metadata (version, description, agent, model) |

### YAML Versioning
To create a new version of a prompt:
1. Copy `v1.yaml` to `v2.yaml` in the same directory
2. Edit `v2.yaml`
3. `PromptFacade` automatically loads the highest version number
4. To pin the old version: `get_prompt("...", context, version="1")`

---

## 4. YAML Template Format

```yaml
version: "1.0"
description: "Suspicious Timing — Chain-of-Thought fraud pattern prompt v1.0"
agent: "suspicious_timing_analyzer"
model: "gemini-2.5-pro"
variables: ["claim_id", "claimant_name", "loss_date", "claimed_amount", "enriched_data"]
content: |
  PATTERN: Suspicious Timing
  CLAIM: {claim_id} — {claimant_name} — {loss_date} — ${claimed_amount}

  ENRICHED DATA:
  {enriched_data}

  ANALYZE the claim for suspicious timing patterns...
  Return JSON with: pattern, score, severity, evidence, reasoning, exculpatory_factors
```

The `{variable}` placeholders are filled by Python's `str.format_map(context)` at runtime.

---

## 5. Prompt Engineering Techniques Used

### Chain-of-Thought (CoT) — Pattern Analyzers
Each of the 4 pattern prompts uses CoT reasoning:
- Present the enriched data
- Ask the LLM to reason step-by-step
- Require structured JSON output with score, evidence, and reasoning

### Few-Shot Learning — Duplicate/Similar Claims
The `duplicate_similar_cot` prompt includes example analyses so the LLM learns the expected format and reasoning depth.

### ReAct Pattern — Enrichment Agent
The `enrichment_react` prompt uses the THOUGHT → ACTION → OBSERVATION loop:
- THOUGHT: "I need to check the claimant's history"
- ACTION: Call `lookup_claimant_history`
- OBSERVATION: "Claimant has 4 prior claims with 2 fraud flags"

### Persona-Based Prompting — Kevin/Diana
The `kevin_query` and `diana_query` prompts define response style:
- Kevin: "Explain step-by-step, define terms, show all evidence"
- Diana: "Concise tables, statistical anomalies only, skip low-confidence flags"

---

## 6. Registered Prompt Keys

| Key | Agent | Technique | Purpose |
|-----|-------|-----------|---------|
| `orchestrator_system` | Orchestrator | System instruction | Defines orchestrator behavior |
| `duplicate_similar_cot` | Analyzer | Few-Shot + CoT | Detect duplicate/similar claims |
| `suspicious_timing_cot` | Analyzer | CoT | Detect suspicious timing patterns |
| `inflated_amounts_cot` | Analyzer | CoT | Detect inflated claim amounts |
| `provider_network_cot` | Analyzer | CoT | Detect provider network anomalies |
| `composite_score_cot` | Analyzer | CoT | Weighted composite score narrative |
| `fraud_classification_fewshot` | Analyzer | Few-Shot | FLAGGED/CLEAN classification |
| `enrichment_react` | Enrichment | ReAct | Data gathering reasoning loop |
| `investigation_report` | Report Generator | Structured output | 7-section Markdown report |
| `kevin_query` | Query Chat | Persona | Junior analyst response style |
| `diana_query` | Query Chat | Persona | Senior SIU lead response style |
