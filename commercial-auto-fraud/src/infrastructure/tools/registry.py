"""
Tool Registry — Dependency Injection Pattern
=============================================
Centralizes tool registration per agent. The agent never instantiates
tools directly — it asks the registry.

Usage:
    registry = ToolRegistry()
    registry.register(MyTool())
    tool = registry.get("my_tool_name")
    result = await tool.run(param=value)

Adding a new tool:
    1. Create your tool (subclass BaseTool)
    2. registry.register(YourTool()) in the agent's __init__
    Done. No other changes needed.
"""

from typing import Dict
from src.infrastructure.tools.base_tool import BaseTool


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool by its name."""
        self._tools[tool.name] = tool
        print(f"[ToolRegistry] Registered tool: '{tool.name}'")

    def get(self, name: str) -> BaseTool:
        """Retrieve a registered tool by name. Raises KeyError if not found."""
        if name not in self._tools:
            available = list(self._tools.keys())
            raise KeyError(
                f"Tool '{name}' not found. Available tools: {available}"
            )
        return self._tools[name]

    def list_tools(self) -> list[dict]:
        """Returns tool metadata for LLM tool-listing and agent cards."""
        return [
            {"name": t.name, "description": t.description}
            for t in self._tools.values()
        ]

    def __len__(self):
        return len(self._tools)
