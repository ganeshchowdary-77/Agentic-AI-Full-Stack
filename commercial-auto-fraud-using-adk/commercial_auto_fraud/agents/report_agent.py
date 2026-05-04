"""
Investigation Report Generator Agent
Produces Markdown reports for flagged claims.
Uses Gemini Flash.
"""

from google.adk.agents import LlmAgent
from google.adk.models import ModelConfig
from ..tools.report_tools import save_report_artifact
from ..prompts.manager import prompt_manager

report_agent = LlmAgent(
    name="investigation_report_generator",
    instruction=prompt_manager.get("report_system"),
    model=ModelConfig(
        provider="google",
        model="gemini-2.5-flash",
        temperature=0.0,
    ),
    tools=[save_report_artifact],
)
