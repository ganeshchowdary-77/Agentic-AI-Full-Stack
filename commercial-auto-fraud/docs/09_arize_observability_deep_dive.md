# Arize AX & OpenTelemetry — How Observability Works Behind the Scenes

This document teaches you everything about how we instrument AI agents for observability, how OpenTelemetry works internally, and how Arize AX visualizes traces.

---

## 1. The Problem: AI Agents Are Black Boxes

When an LLM returns a wrong answer, you need to know:
- What prompt was sent?
- Which tools were called?
- What data did each tool return?
- How long did each step take?
- Where in the pipeline did things go wrong?

Without observability, debugging an AI pipeline is like debugging a program with no logs and no debugger. **OpenTelemetry + Arize AX = your debugger for AI agents.**

---

## 2. OpenTelemetry — The Foundation

### What is OpenTelemetry?
OpenTelemetry (OTel) is an open standard for collecting **traces**, **metrics**, and **logs** from applications. Think of it as a universal adapter for observability — you instrument your code once, and can send data to any backend (Arize, Datadog, Jaeger, etc.).

### Key Concepts

| Concept | What It Is | Analogy |
|---------|-----------|---------|
| **Trace** | A complete request journey (end-to-end) | A GPS route from start to finish |
| **Span** | One step within a trace | One turn on the route |
| **Trace ID** | Unique identifier for the entire trace | Route ID |
| **Span ID** | Unique identifier for one step | Turn ID |
| **Parent Span** | The span that started this one | The previous turn |
| **Attributes** | Key-value metadata on a span | Notes attached to a turn |
| **Context** | The thread-local trace state | "Where am I on the route right now?" |

### Span Hierarchy = Call Tree
```
Trace ID: abc-123
│
├── Span: "Orchestrator: Batch Pipeline" (root)     ← 36.44s total
│   ├── Span: "ingest_claim_batch"                   ← 0.46s
│   ├── Span: "Claim Pipeline [CLM-2026-001]"        ← 35.87s
│   │   ├── Span: "enrich_claim"                     ← 19.06s
│   │   │   ├── Span: "lookup_claimant_history"      ← 0.01s
│   │   │   ├── Span: "lookup_provider_network"      ← 0.01s
│   │   │   ├── Span: "lookup_vehicle_valuation"     ← 0.01s
│   │   │   └── Span: "lookup_policy_details"        ← 0.01s
│   │   ├── Span: "analyze_fraud_patterns"           ← 16.81s
│   │   │   ├── Span: "duplicate_similar.run"        ← 0.19s
│   │   │   ├── Span: "suspicious_timing.run"        ← 0.01s
│   │   │   ├── Span: "inflated_amounts.run"         ← 0.01s
│   │   │   └── Span: "provider_network.run"         ← 0.01s
│   │   └── Span: "report_generator.run"             ← 0.01s
│   ├── Span: "Claim Pipeline [CLM-2026-002]"        ← parallel with above
│   └── ... (12 claims total)
```

---

## 3. OpenInference — The AI-Specific Extension

Standard OpenTelemetry was designed for web services. **OpenInference** is an extension that adds AI-specific span types:

| Span Kind | When Used | What Gets Recorded |
|-----------|----------|-------------------|
| `CHAIN` | Agent workflow / pipeline step | Input, output, agent name |
| `TOOL` | Tool execution | Tool name, input args, output result |
| `LLM` | LLM inference call | Model name, prompt, completion, tokens |
| `RETRIEVER` | RAG retrieval | Query, retrieved documents |
| `EMBEDDING` | Embedding generation | Input text, model, dimensions |

### How We Set Span Kind
```python
# Every span gets the openinference.span.kind attribute
span.set_attribute("openinference.span.kind", "CHAIN")  # or "TOOL", "LLM"
```

Arize AX reads this attribute to determine how to visualize the span — LLM spans show prompt/completion, TOOL spans show input/output, CHAIN spans show workflow flow.

---

## 4. Our Telemetry Implementation — Line by Line

### 4.1 Setup (`setup_telemetry()`)

```python
def setup_telemetry():
    # 1. Read Arize credentials from environment
    space_id = os.environ.get("ARIZE_SPACE_ID", "")
    api_key  = os.environ.get("ARIZE_API_KEY", "")

    # 2. Create a Resource (identifies this service in the trace backend)
    resource = Resource(attributes={
        "service.name": "commercial-auto-fraud-pipeline",
        "openinference.project.name": "commercial-auto-fraud-pipeline",
    })

    # 3. Create the TracerProvider (the factory for creating spans)
    provider = TracerProvider(resource=resource)

    # 4. If Arize credentials exist, add an OTLP exporter
    if space_id and api_key:
        exporter = OTLPSpanExporter(
            endpoint="https://otlp.arize.com/v1/traces",  # Arize's OTLP endpoint
            headers={
                "space_id": space_id,  # Your Arize workspace
                "api_key": api_key,     # Your Arize API key
            },
        )
        # BatchSpanProcessor batches spans and sends them periodically
        # (not one-by-one, for performance)
        provider.add_span_processor(BatchSpanProcessor(exporter))

    # 5. Set as the global tracer provider
    trace.set_tracer_provider(provider)

    # 6. Return a named tracer
    return trace.get_tracer("commercial-auto-fraud")
```

### What Happens Without Credentials
If `ARIZE_SPACE_ID` and `ARIZE_API_KEY` are empty, no exporter is added. Spans are still created (for context propagation) but not exported anywhere. The system works identically — just without external observability.

### 4.2 Creating Spans — Three Context Managers

```python
@contextmanager
def span_chain(name, input_value="", **extra_attrs):
    """Creates a CHAIN span — for agent workflows and pipeline steps."""
    with tracer.start_as_current_span(name) as span:
        span.set_attribute("openinference.span.kind", "CHAIN")
        if input_value:
            span.set_attribute("input.value", input_value[:4000])
        for k, v in extra_attrs.items():
            span.set_attribute(k, str(v))
        try:
            yield span  # Caller can add more attributes
        except Exception as e:
            span.record_exception(e)   # Exception appears in Arize
            span.set_attribute("error", True)
            raise
```

**Usage**:
```python
with span_chain("Claim Pipeline [CLM-001]", input_value=json.dumps(claim)) as span:
    result = await process_claim(claim)
    span.set_attribute("fraud_score", str(result["score"]))
```

The same pattern is used for `span_tool()` (kind="TOOL") and `span_llm()` (kind="LLM", also sets `llm.model.name`).

### 4.3 The `@trace_llm_call` Decorator

This decorator is applied to `Agent.run()` in the mock ADK:

```python
def trace_llm_call(func):
    @wraps(func)
    async def wrapper(self, prompt, *args, **kwargs):
        with span_llm(
            f"{self.name}.run",           # Span name: "fraud_pattern_analyzer.run"
            model=self.model,              # "gemini-2.5-pro"
            input_value=str(prompt),       # The full prompt (truncated to 4000 chars)
            **{"agent.name": self.name},   # Extra attribute
        ) as span:
            result = await func(self, prompt, *args, **kwargs)
            span.set_attribute("output.value", str(result)[:4000])
            return result
    return wrapper
```

Every time `agent.run(prompt)` is called, this creates an LLM span with:
- `input.value` = the prompt sent to the LLM
- `output.value` = the LLM's response
- `llm.model.name` = which model was used
- Duration = how long the LLM call took

---

## 5. How Spans Flow Through the Pipeline

Let's trace one claim through the entire system:

```
1. User clicks "Run Pipeline" → GET /api/run
   │
2. OrchestratorAgent.process_claim_batch()
   │ Creates: CHAIN span "Orchestrator: Batch Pipeline"
   │
3. IngestBatchTool.run()
   │ Creates: TOOL span "Tool: ingest_claim_batch"
   │ Attributes: input_value = batch JSON
   │
4. For each claim (parallel): _process_single_claim()
   │ Creates: CHAIN span "Claim Pipeline [CLM-2026-001]"
   │ Attributes: claim.id, claimant.name, claimed_amount
   │
5. EnrichClaimTool.run()
   │ Creates: TOOL span "Tool: enrich_claim"
   │   │
   │   └── HTTP POST to :8002/v1/tasks
   │       Headers include: traceparent: 00-TRACEID-SPANID-01
   │       │
   │       └── server_enrichment.py receives request
   │           │ Extracts: ctx = propagate.extract(headers)
   │           │ Creates: TOOL span (CHILD of step 5's span)
   │           │
   │           └── FraudEnrichmentAgent.run()
   │               │ Creates: TOOL span "Tool: lookup_claimant_history"
   │               │ Creates: TOOL span "Tool: lookup_provider_network"
   │               │ Creates: TOOL span "Tool: lookup_vehicle_valuation"
   │               │ Creates: TOOL span "Tool: lookup_policy_details"
   │               │ (all 4 created in parallel via asyncio.gather)
   │
6. AnalyzeFraudPatternsTool.run()
   │ Creates: TOOL span "Tool: analyze_fraud_patterns"
   │   │
   │   └── HTTP POST to :8003/v1/tasks → server_analyzer.py
   │       │ Creates: CHAIN span "Fraud Pattern Analyzer [CLM-2026-001]"
   │       │
   │       └── 4 pattern tools run in parallel:
   │           │ DuplicateSimilarTool.run()
   │           │   Creates: TOOL span "Tool: duplicate_similar_analyzer"
   │           │     └── agent.run(prompt)
   │           │         Creates: LLM span "fraud_pattern_analyzer.run"
   │           │         Attributes: input.value=prompt, output.value=result
   │           │
   │           │ (same for suspicious_timing, inflated_amounts, provider_network)
   │
7. GenerateReportTool.run() (if score >= 40)
   │ Creates: TOOL span "Tool: generate_investigation_report"
   │   └── HTTP POST to :8004/v1/tasks → server_report.py
   │       Creates: CHAIN span "Investigation Report Generator [CLM-2026-001]"
   │         └── LLM span "investigation_report_generator.run"
```

All of these spans share the SAME Trace ID. In Arize, they appear as one connected tree.

---

## 6. Arize AX — What You See in the Dashboard

### The Traces View
Each pipeline run creates ONE trace. In Arize, you see:
- **Trace list**: Each row = one batch run, with total duration
- **Click a trace**: Waterfall view showing all spans as a tree
- **Click a span**: See attributes (fraud_score, claim_id, etc.), input/output values

### Key Attributes We Set

| Attribute | Where Set | Purpose |
|-----------|----------|---------|
| `claim.id` | Claim Pipeline span | Filter traces by claim |
| `fraud_score` | Claim Pipeline span | Sort/filter by score |
| `fraud_tier` | Claim Pipeline span | Filter by severity |
| `pattern_flags` | Claim Pipeline span | Which patterns triggered |
| `report_generated` | Claim Pipeline span | Was a report produced? |
| `enrichment_completeness` | Claim Pipeline span | Did enrichment succeed? |
| `prompt_template` | Claim Pipeline span | Which YAML prompt was used |
| `prompt_version` | Claim Pipeline span | Which version of the prompt |
| `agent.name` | LLM spans | Which agent made this call |
| `llm.model.name` | LLM spans | Which model was used |
| `input.value` | All spans | What went in |
| `output.value` | All spans | What came out |

### Debugging Example
**Problem**: Claim CLM-2026-005 scored 0 but should be flagged.

1. In Arize, search for traces where `claim.id = CLM-2026-005`
2. Open the trace → find the Fraud Pattern Analyzer span
3. Expand each pattern's LLM span
4. Check `input.value` — was the enriched data included?
5. Check `output.value` — did the LLM return valid JSON?
6. Found it: `output.value = {"status": "ok"}` — the mock ADK routing didn't match!
