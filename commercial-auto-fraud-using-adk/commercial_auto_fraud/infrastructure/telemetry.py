import logging
from typing import Any, Optional, Dict
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

logger = logging.getLogger("commercial_auto_fraud.telemetry")

class ArizeTelemetryPlugin(BasePlugin):
    """
    ADK Plugin to trace agent, LLM, and tool calls to Arize AI.
    Uses OpenTelemetry standard spans.
    """
    def __init__(self, name: str = "arize_telemetry"):
        super().__init__(name=name)
        self.tracer = trace.get_tracer(__name__)
        self._spans: Dict[str, Any] = {}

    async def before_agent_callback(self, *, agent: BaseAgent, callback_context: CallbackContext) -> None:
        span_name = f"AGENT:{agent.name}"
        span = self.tracer.start_span(span_name)
        span.set_attribute("agent.name", agent.name)
        span.set_attribute("agent.description", agent.description or "")
        span.set_attribute("invocation_id", callback_context.invocation_id)
        self._spans[f"agent_{id(callback_context)}"] = span

    async def after_agent_callback(self, *, agent: BaseAgent, callback_context: CallbackContext) -> None:
        span = self._spans.pop(f"agent_{id(callback_context)}", None)
        if span:
            span.end()

    async def before_model_callback(self, *, callback_context: CallbackContext, llm_request: LlmRequest) -> None:
        span_name = "LLM_CALL"
        span = self.tracer.start_span(span_name)
        span.set_attribute("llm.model", str(llm_request.model))
        # Add prompt context if safe/short
        self._spans[f"llm_{id(llm_request)}"] = span

    async def after_model_callback(self, *, callback_context: CallbackContext, llm_response: LlmResponse) -> None:
        span = self._spans.pop(f"llm_{id(llm_response.request)}", None)
        if span:
            if llm_response.usage:
                span.set_attribute("llm.usage.prompt_tokens", llm_response.usage.prompt_token_count)
                span.set_attribute("llm.usage.completion_tokens", llm_response.usage.candidates_token_count)
            span.end()

    async def before_tool_callback(self, *, tool: BaseTool, tool_args: dict[str, Any], tool_context: ToolContext) -> None:
        span_name = f"TOOL:{tool.name}"
        span = self.tracer.start_span(span_name)
        span.set_attribute("tool.name", tool.name)
        span.set_attribute("tool.args", str(tool_args))
        self._spans[f"tool_{id(tool_context)}"] = span

    async def after_tool_callback(self, *, tool: BaseTool, tool_args: dict[str, Any], tool_context: ToolContext, result: dict) -> None:
        span = self._spans.pop(f"tool_{id(tool_context)}", None)
        if span:
            span.set_attribute("tool.result", str(result))
            span.end()

    async def on_tool_error_callback(self, *, tool: BaseTool, tool_args: dict[str, Any], tool_context: ToolContext, error: Exception) -> None:
        span = self._spans.pop(f"tool_{id(tool_context)}", None)
        if span:
            span.set_status(Status(StatusCode.ERROR, str(error)))
            span.record_exception(error)
            span.end()
