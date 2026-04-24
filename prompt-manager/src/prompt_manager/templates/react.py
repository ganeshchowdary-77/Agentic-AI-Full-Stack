"""
ReAct Template Implementation for ADK.

Note: In ADK, tool execution is usually natively handled by the framework loop.
This prompt reinforces the Thought/Action structure if needed for specific models.
"""

from typing import Any, Dict
from .base import PromptTemplate
from ..core.exceptions import PromptRenderError

class ReActTemplate(PromptTemplate):
    """
    Concrete implementation for ReAct ADK instruction.
    Provides strict rules for the agent's interaction loop.
    """

    def build_task_instruction(self, variables: Dict[str, Any]) -> str:
        if not self.definition.user_message_template:
            return ""
            
        try:
            rendered_task = self.definition.user_message_template.format(**variables)
            return f"<task>\n{rendered_task}\n</task>"
        except KeyError as e:
            raise PromptRenderError(f"Failed to inject variable into ReAct template: {e}")

    def build_examples(self) -> str:
        if not self.definition.examples:
            return ""

        compiled_examples = ["<trajectory_examples>"]
        for i, example in enumerate(self.definition.examples, 1):
            trajectory = example.explanation or "Thought: I have the answer.\nFinal Answer: "
            block = (f"  <example index=\"{i}\">\n"
                     f"    <question>{example.input}</question>\n"
                     f"    <trajectory>\n{trajectory}\n    </trajectory>\n"
                     f"    <final_answer>{example.output}</final_answer>\n"
                     f"  </example>")
            compiled_examples.append(block)

        compiled_examples.append("</trajectory_examples>")
        return "\n".join(compiled_examples)

    def build_constraints(self) -> str:
        rules = """<constraints>
You run in a strict loop of Thought, Action, PAUSE, Observation.
At the end of the loop you output an Answer.

FORMAT RULES:
Thought: Describe your thoughts about the question.
Action: The name of the tool to use.
Action Input: The parameters to pass to the tool.
PAUSE
Observation: The result of the tool execution.
... (repeat)
Final Answer: The final response to the user's request.
</constraints>"""
        return rules