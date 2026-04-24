"""
LLM Provider — Centralized Model Wrapper
==========================================
The ONLY place that instantiates google.adk.Agent.
No other module should call Agent() directly.

Switching from mock ADK → real Gemini API:
  1. Replace the Agent import below with the real client
  2. Done — zero changes needed in any agent module

Models configured in src/config/settings.py.
"""

from google.adk import Agent
from src.config.settings import settings


class LLMProvider:
    """Factory for creating and caching named Agent instances."""

    def __init__(self):
        self._agents: dict = {}

    def get_agent(self, name: str, model: str | None = None, instruction: str = "") -> Agent:
        """
        Returns a cached Agent for the given name (created once, reused).

        Args:
            name:        Unique agent name (used for Arize span labels)
            model:       Model identifier. Defaults to settings.default_model.
            instruction: System instruction for the agent.
        """
        if name not in self._agents:
            resolved_model = model or settings.default_model
            self._agents[name] = Agent(
                name=name,
                model=resolved_model,
                instruction=instruction,
            )
        return self._agents[name]

    def list_agents(self) -> list[str]:
        return list(self._agents.keys())


# Module-level singleton — import this everywhere
llm_provider = LLMProvider()
