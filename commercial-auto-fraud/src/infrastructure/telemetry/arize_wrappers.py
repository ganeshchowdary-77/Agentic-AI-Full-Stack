"""
Arize AX Telemetry Module
--------------------------
Provides manual OpenInference-compliant span instrumentation for the
Commercial Auto Fraud Detection Pipeline.

IMPORTANT: We use MANUAL spans only — no FastAPI/HTTPX auto-instrumentors.
This ensures only meaningful agent-level spans appear in Arize, not noisy
HTTP transport spans.

Span hierarchy produced:
  CHAIN: Orchestrator: Batch Pipeline
    CHAIN: Claim Pipeline [CLM-XXX]
      TOOL:  Claim Data Enrichment Agent [CLM-XXX]
        TOOL:  Tool: lookup_claimant_history
        TOOL:  Tool: lookup_provider_network
        TOOL:  Tool: lookup_vehicle_valuation
        TOOL:  Tool: lookup_policy_details
      CHAIN: Fraud Pattern Analyzer [CLM-XXX]
        LLM:   duplicate_similar_analyzer.run
        LLM:   suspicious_timing_analyzer.run
        LLM:   inflated_amounts_analyzer.run
        LLM:   provider_network_analyzer.run
      CHAIN: Investigation Report Generator [CLM-XXX]
        LLM:   investigation_report_generator.run
"""

import os
from contextlib import contextmanager
from functools import wraps
from opentelemetry import trace, context
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from dotenv import load_dotenv

load_dotenv()

def setup_telemetry():
    space_id = os.environ.get("ARIZE_SPACE_ID", "")
    api_key  = os.environ.get("ARIZE_API_KEY", "")

    resource = Resource(attributes={
        "service.name": "commercial-auto-fraud-pipeline",
        "openinference.project.name": "commercial-auto-fraud-pipeline",
    })

    provider = TracerProvider(resource=resource)

    if space_id and api_key:
        exporter = OTLPSpanExporter(
            endpoint="https://otlp.arize.com/v1/traces",
            headers={
                "space_id": space_id,
                "api_key": api_key,
            },
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
    return trace.get_tracer("commercial-auto-fraud")

tracer = setup_telemetry()


def flush_telemetry():
    """Forces all buffered spans to export immediately."""
    provider = trace.get_tracer_provider()
    if hasattr(provider, "force_flush"):
        provider.force_flush(timeout_millis=10_000)


# ─────────────────────────────────────────────
# Low-level span helpers
# ─────────────────────────────────────────────

@contextmanager
def span_chain(name: str, input_value: str = "", **extra_attrs):
    """Context manager that creates a CHAIN span."""
    with tracer.start_as_current_span(name) as span:
        span.set_attribute("openinference.span.kind", "CHAIN")
        if input_value:
            span.set_attribute("input.value", input_value[:4000])
        for k, v in extra_attrs.items():
            span.set_attribute(k, str(v))
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_attribute("error", True)
            raise


@contextmanager
def span_tool(name: str, input_value: str = "", **extra_attrs):
    """Context manager that creates a TOOL span."""
    with tracer.start_as_current_span(name) as span:
        span.set_attribute("openinference.span.kind", "TOOL")
        if input_value:
            span.set_attribute("input.value", input_value[:4000])
        for k, v in extra_attrs.items():
            span.set_attribute(k, str(v))
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_attribute("error", True)
            raise


@contextmanager
def span_llm(name: str, model: str, input_value: str = "", **extra_attrs):
    """Context manager that creates an LLM span."""
    with tracer.start_as_current_span(name) as span:
        span.set_attribute("openinference.span.kind", "LLM")
        span.set_attribute("llm.model.name", model)
        if input_value:
            span.set_attribute("input.value", input_value[:4000])
        for k, v in extra_attrs.items():
            span.set_attribute(k, str(v))
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_attribute("error", True)
            raise


# ─────────────────────────────────────────────
# Decorators (backward-compat wrappers)
# ─────────────────────────────────────────────

def trace_llm_call(func):
    """
    Decorator for Agent.run(prompt) methods.
    Creates an LLM span with the agent name & model as attributes.
    """
    @wraps(func)
    async def wrapper(self, prompt: str, *args, **kwargs):
        with span_llm(
            f"{self.name}.run",
            model=self.model,
            input_value=str(prompt),
            **{"agent.name": self.name},
        ) as span:
            result = await func(self, prompt, *args, **kwargs)
            span.set_attribute("output.value", str(result)[:4000])
            return result
    return wrapper


def trace_agent_step(name: str, kind: str = "CHAIN"):
    """Decorator that wraps an async method in a named CHAIN or TOOL span."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            ctx_mgr = span_chain if kind == "CHAIN" else span_tool
            with ctx_mgr(name) as span:
                result = await func(*args, **kwargs)
                return result
        return wrapper
    return decorator

