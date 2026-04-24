"""
BaseTool — Abstract Tool Interface
====================================
Every tool in this system inherits from BaseTool.
Enforces a predictable contract:
  - name / description metadata for the LLM and ToolRegistry
  - async execute() for the tool logic
  - Automatic Arize TOOL span via run()

Adding a new tool = subclass BaseTool, register in a ToolRegistry.
"""

from abc import ABC, abstractmethod
from typing import Any
from src.infrastructure.telemetry.arize_wrappers import span_tool


class BaseTool(ABC):
    """Abstract base for all agent tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool identifier used by the LLM and ToolRegistry."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description shown to the LLM in tool listings."""
        ...

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """
        Perform the tool's action.
        Override in each concrete tool. All args validated by caller.
        """
        ...

    async def run(self, **kwargs) -> Any:
        """
        Public entry point — wraps execute() in an Arize TOOL span.
        Always call tool.run(**kwargs), never execute() directly.
        """
        with span_tool(f"Tool: {self.name}", input_value=str(kwargs)[:500]) as span:
            result = await self.execute(**kwargs)
            span.set_attribute("output.value", str(result)[:1000])
            return result
