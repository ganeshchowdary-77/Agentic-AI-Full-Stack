"""
Arize OpenTelemetry Callbacks
Native ADK callbacks for automatic enterprise observability.
"""
import os
import json
from google.adk.tools import ToolContext

# Mock OpenTelemetry for this scaffolding, assuming real usage in production
class MockTracer:
    def start_as_current_span(self, name, attributes=None):
        class DummySpan:
            def __enter__(self): pass
            def __exit__(self, exc_type, exc_val, exc_tb): pass
            def set_attribute(self, key, val): pass
        return DummySpan()

tracer = MockTracer()

# --- Callbacks ---

async def arize_agent_start(agent, ctx):
    """Fired before LlmAgent executes."""
    # In a real implementation, this would open a new OTel Span
    print(f"[Arize Telemetry] Agent Started: {agent.name} (Session: {ctx.session.id})")

async def arize_tool_start(tool_name: str, args: dict, tool_context: ToolContext):
    """Fired before a FunctionTool executes."""
    print(f"[Arize Telemetry] Tool Executing: {tool_name} with args {json.dumps(args)}")

async def arize_llm_capture(agent, ctx, result):
    """Fired after the LLM returns, extracting tokens and latency."""
    tokens = result.usage_metadata.total_token_count if hasattr(result, "usage_metadata") else 0
    print(f"[Arize Telemetry] LLM Complete: {agent.name} (Tokens: {tokens})")
