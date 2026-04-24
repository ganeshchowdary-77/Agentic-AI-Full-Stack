# Arize AX — Practical Setup & Advanced Usage Guide

This document teaches you how to set up Arize AX from zero, configure it for AI agents, build custom dashboards, and use it for debugging and evaluation.

---

## 1. What is Arize AX?

Arize AX is an **AI observability platform**. It collects traces from your AI agents and lets you:
- **Debug**: See exactly what prompt was sent and what the LLM returned
- **Monitor**: Track latency, error rates, and quality over time
- **Evaluate**: Compare prompt versions, models, and agent configurations
- **Alert**: Get notified when something goes wrong

### Arize vs Other Platforms

| Platform | Focus | Pricing | Best For |
|----------|-------|---------|----------|
| **Arize AX** | AI/ML observability | Free tier + paid | LLM debugging, trace visualization |
| **LangSmith** | LangChain-specific | Free tier + paid | LangChain apps |
| **Weights & Biases** | ML experiment tracking | Free tier + paid | Model training |
| **Datadog** | General APM | Paid | Full-stack monitoring |
| **Jaeger** | Distributed tracing | Free (self-hosted) | Microservice tracing |

---

## 2. Setup from Zero

### Step 1: Create Arize Account
1. Go to https://app.arize.com
2. Sign up (free tier available)
3. Create a new **Space** (workspace)
4. Get your `Space ID` and `API Key` from Settings

### Step 2: Configure Environment
```bash
# .env file
ARIZE_SPACE_ID=your_space_id_here
ARIZE_API_KEY=your_api_key_here
```

### Step 3: Install Dependencies
```bash
pip install opentelemetry-api opentelemetry-sdk
pip install opentelemetry-exporter-otlp-proto-http
```

### Step 4: Initialize Telemetry
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# 1. Define your service
resource = Resource(attributes={
    "service.name": "my-ai-agent",
    "openinference.project.name": "my-ai-agent",  # Project name in Arize
})

# 2. Create tracer provider
provider = TracerProvider(resource=resource)

# 3. Add Arize exporter
exporter = OTLPSpanExporter(
    endpoint="https://otlp.arize.com/v1/traces",
    headers={"space_id": "YOUR_SPACE_ID", "api_key": "YOUR_API_KEY"},
)
provider.add_span_processor(BatchSpanProcessor(exporter))

# 4. Set global
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("my-ai-agent")
```

### Step 5: Instrument Your Code
```python
# Wrap any function in a span
with tracer.start_as_current_span("my-operation") as span:
    span.set_attribute("openinference.span.kind", "CHAIN")
    span.set_attribute("input.value", "my input")
    result = do_something()
    span.set_attribute("output.value", str(result))
```

---

## 3. OpenInference Attributes Reference

These are the attributes Arize AX understands. Set them correctly and Arize will visualize them properly.

### Universal Attributes (All Span Types)
```python
span.set_attribute("openinference.span.kind", "CHAIN")  # CHAIN, TOOL, LLM, RETRIEVER, EMBEDDING
span.set_attribute("input.value", "the input data")
span.set_attribute("output.value", "the output data")
span.set_attribute("error", True)  # Set on error
```

### LLM-Specific Attributes
```python
span.set_attribute("llm.model.name", "gemini-2.5-pro")
span.set_attribute("llm.token_count.prompt", 1500)
span.set_attribute("llm.token_count.completion", 350)
span.set_attribute("llm.token_count.total", 1850)

# For chat-style LLMs
span.set_attribute("llm.input_messages.0.role", "system")
span.set_attribute("llm.input_messages.0.content", "You are a fraud analyst...")
span.set_attribute("llm.input_messages.1.role", "user")
span.set_attribute("llm.input_messages.1.content", "Analyze claim CLM-001...")
span.set_attribute("llm.output_messages.0.role", "assistant")
span.set_attribute("llm.output_messages.0.content", '{"score": 85}')
```

### Tool-Specific Attributes
```python
span.set_attribute("tool.name", "lookup_claimant_history")
span.set_attribute("tool.parameters", '{"claimant_id": "C-4821"}')
```

### Custom Attributes (Your Business Logic)
```python
span.set_attribute("claim.id", "CLM-2026-001")
span.set_attribute("fraud_score", "85")
span.set_attribute("fraud_tier", "critical")
span.set_attribute("pattern_flags", "duplicate_similar,provider_network")
span.set_attribute("report_generated", "True")
```

---

## 4. Span Export: How Data Gets to Arize

### The Pipeline
```
Your Code → Span Created → BatchSpanProcessor → OTLPSpanExporter → Arize
                                 │
                                 ├── Buffers spans in memory
                                 ├── Sends batch every 5 seconds (default)
                                 └── Or when buffer is full (512 spans default)
```

### OTLP Protocol
OTLP = OpenTelemetry Protocol. It's the standard wire format for sending telemetry data.

```http
POST https://otlp.arize.com/v1/traces
Content-Type: application/x-protobuf
space_id: your_space_id
api_key: your_api_key

[Binary protobuf payload containing spans]
```

### Flushing on Shutdown
```python
def flush_telemetry():
    """Call before shutdown to ensure all spans are sent."""
    provider = trace.get_tracer_provider()
    if hasattr(provider, "force_flush"):
        provider.force_flush(timeout_millis=10_000)
```

---

## 5. Context Propagation — The Key to Distributed Traces

### Problem
Agent A (process 1) calls Agent B (process 2) over HTTP. How does Agent B's span link to Agent A's trace?

### Solution: W3C Trace Context

```python
# Agent A: INJECT trace context into HTTP headers
from opentelemetry import propagate

headers = {}
propagate.inject(headers)
# headers now contains: {"traceparent": "00-abc123-def456-01"}

response = await httpx.post(url, headers=headers, json=data)
```

```python
# Agent B: EXTRACT trace context from HTTP headers
from opentelemetry import propagate

ctx = propagate.extract(dict(request.headers))

# Create span as CHILD of Agent A's span
with tracer.start_as_current_span("Agent B Operation", context=ctx) as span:
    # This span will have the same Trace ID as Agent A's span
    result = await process(data)
```

### Without Context Propagation
```
Arize shows:
  Trace 1: Agent A spans (no children)
  Trace 2: Agent B spans (orphaned)
  → You can't see the full pipeline flow
```

### With Context Propagation
```
Arize shows:
  Trace 1: Agent A spans
    └── Agent B spans (linked as children)
    → Full end-to-end visibility
```

---

## 6. Advanced: Building Evaluation Pipelines with Arize

### Evaluating Prompt Quality
```python
# Log prompt version as span attribute
span.set_attribute("prompt_template", "duplicate_similar_cot")
span.set_attribute("prompt_version", "v2")

# In Arize, filter by prompt_version and compare:
# - Average fraud scores per version
# - False positive rates
# - Response latency
```

### Evaluating Model Performance
```python
# Log model info
span.set_attribute("llm.model.name", "gemini-2.5-pro")

# Switch to a different model for comparison:
span.set_attribute("llm.model.name", "gemini-2.5-flash")

# In Arize, compare models side-by-side
```

### Custom Evaluation Metrics
```python
# Calculate and log your own metrics
span.set_attribute("fraud_score", str(score))
span.set_attribute("confidence", confidence)
span.set_attribute("evidence_count", str(len(evidence)))
span.set_attribute("false_positive_risk", "high" if score < 30 else "low")
```

---

## 7. Debugging Checklist

When something goes wrong in your AI pipeline:

1. **Find the trace** in Arize by claim_id, timestamp, or error flag
2. **Walk the span tree** — which step failed or produced unexpected output?
3. **Check input.value** — was the right data sent to the LLM?
4. **Check output.value** — did the LLM return valid JSON? Garbage? Empty?
5. **Check span duration** — is something taking too long? (timeout?)
6. **Check error attribute** — was an exception recorded?
7. **Compare spans** — look at a working trace vs broken trace side by side

### Common Issues and Where to Look

| Symptom | Check This Span | Look For |
|---------|----------------|----------|
| Score always 0 | LLM spans | `output.value` = generic response (routing bug) |
| No reports generated | Claim Pipeline span | `fraud_score` < 40 (scoring issue) |
| Missing enrichment data | Enrichment TOOL spans | `output.value` = empty or error |
| Slow pipeline | Root CHAIN span | Which child span has the longest duration? |
| Duplicate traces | Trace list | Missing context propagation (orphaned spans) |

---

## 8. Complete Minimal Example: Instrumented AI Agent

```python
"""
Complete example: AI agent with Arize observability in 60 lines
"""
import os, json, asyncio
from opentelemetry import trace, propagate
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource

# Setup (use ConsoleSpanExporter for local testing, OTLPSpanExporter for Arize)
resource = Resource(attributes={"service.name": "demo-agent"})
provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("demo")

# Tool
async def lookup_database(item_id: str) -> dict:
    with tracer.start_as_current_span("Tool: lookup_database") as span:
        span.set_attribute("openinference.span.kind", "TOOL")
        span.set_attribute("input.value", item_id)
        result = {"item_id": item_id, "risk_score": 75}  # Mock
        span.set_attribute("output.value", json.dumps(result))
        return result

# Agent
async def analyze(data: dict) -> dict:
    with tracer.start_as_current_span("Agent: Analyzer") as span:
        span.set_attribute("openinference.span.kind", "CHAIN")
        span.set_attribute("input.value", json.dumps(data))

        # Call tool
        db_result = await lookup_database(data["id"])

        # "LLM call" (mock)
        with tracer.start_as_current_span("LLM: analyze") as llm_span:
            llm_span.set_attribute("openinference.span.kind", "LLM")
            llm_span.set_attribute("llm.model.name", "gemini-2.5-pro")
            llm_span.set_attribute("input.value", f"Analyze {data}")
            result = {"score": db_result["risk_score"], "tier": "high"}
            llm_span.set_attribute("output.value", json.dumps(result))

        span.set_attribute("output.value", json.dumps(result))
        return result

# Run
asyncio.run(analyze({"id": "CLM-001", "amount": 50000}))
provider.force_flush()
```

This prints span data to console. Replace `ConsoleSpanExporter` with `OTLPSpanExporter` to send to Arize.
