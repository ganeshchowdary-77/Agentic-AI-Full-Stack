"""
Enterprise Versioned Prompt Manager

A localized implementation of the prompt-manager library.
Provides YAML-backed file storage with strict semantic versioning for agent prompts.
This allows easy addition of new prompts by simply dropping a YAML file into the storage directory.
"""

import os
import yaml
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum


# ==============================================================================
# Domain Models
# ==============================================================================

class PromptType(str, Enum):
    ZERO_SHOT = "zero_shot"
    FEW_SHOT = "few_shot"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    REACT = "react"

class PromptMetadata(BaseModel):
    prompt_id: str
    version: str
    description: str
    prompt_type: PromptType = PromptType.ZERO_SHOT
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by: str = "system"

class TemplateDefinition(BaseModel):
    metadata: PromptMetadata
    system_message: str
    user_message_template: str = ""
    
class RenderedInstruction(BaseModel):
    metadata: PromptMetadata
    text: str


# ==============================================================================
# Storage Layer
# ==============================================================================

class FileSystemStorage:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_path(self, prompt_id: str, version: str) -> str:
        return os.path.join(self.base_dir, f"{prompt_id}_{version}.yaml")

    def save(self, template: TemplateDefinition):
        path = self._get_path(template.metadata.prompt_id, template.metadata.version)
        with open(path, "w", encoding="utf-8") as f:
            # Dump the Pydantic model dictionary to YAML cleanly
            yaml.dump(
                template.model_dump(), 
                f, 
                default_flow_style=False, 
                sort_keys=False,
                allow_unicode=True
            )

    def load(self, prompt_id: str, version: str) -> TemplateDefinition:
        path = self._get_path(prompt_id, version)
        if not os.path.exists(path):
            raise ValueError(f"Prompt {prompt_id} version {version} not found at {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return TemplateDefinition(**data)

    def list_versions(self, prompt_id: str) -> List[str]:
        versions = []
        prefix = f"{prompt_id}_v"
        for filename in os.listdir(self.base_dir):
            if filename.startswith(prefix) and (filename.endswith(".yaml") or filename.endswith(".yml")):
                # extract version: e.g. enrichment_system_v1.0.0.yaml -> v1.0.0
                version_part = filename.replace(f"{prompt_id}_", "")
                version_part = version_part.replace(".yaml", "").replace(".yml", "")
                versions.append(version_part)
        return sorted(versions)


# ==============================================================================
# Prompt Manager Facade
# ==============================================================================

class PromptManager:
    def __init__(self, storage_dir: str):
        self.storage = FileSystemStorage(storage_dir)

    def register(self, template: TemplateDefinition):
        self.storage.save(template)

    def render(self, prompt_id: str, variables: Dict[str, Any] = None, version: Optional[str] = None) -> RenderedInstruction:
        variables = variables or {}
        
        if version is None:
            versions = self.storage.list_versions(prompt_id)
            if not versions:
                raise ValueError(f"No versions found for prompt {prompt_id} in {self.storage.base_dir}")
            version = versions[-1]  # Naive sort grabs latest

        template = self.storage.load(prompt_id, version)
        
        # Render the template
        rendered_sys = template.system_message.format(**variables)
        rendered_user = template.user_message_template.format(**variables) if template.user_message_template else ""
        
        final_text = rendered_sys
        if rendered_user:
            final_text += f"\n\n{rendered_user}"
            
        return RenderedInstruction(metadata=template.metadata, text=final_text)

    def get(self, prompt_id: str, variables: Dict[str, Any] = None, version: Optional[str] = None) -> str:
        """Convenience method returning the raw string instruction."""
        return self.render(prompt_id, variables, version).text


# ==============================================================================
# Initialization & Bootstrap (Run on import)
# ==============================================================================

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "storage")
prompt_manager = PromptManager(PROMPTS_DIR)


def _bootstrap_prompts():
    """Initializes the prompt YAML files if they don't exist."""
    
    # 1. Enrichment Prompt
    if not prompt_manager.storage.list_versions("enrichment_system"):
        prompt_manager.register(TemplateDefinition(
            metadata=PromptMetadata(prompt_id="enrichment_system", version="v1.0.0", description="Enrichment Agent Prompt"),
            system_message="""You are a Claim Data Enrichment specialist for commercial auto insurance fraud detection. Your job is to augment raw claim data with contextual information from external data sources.

For each claim you receive, you must:
1. Look up claimant history — prior claims, fraud flags, addresses, associated vehicles
2. Look up provider information — billing patterns, license status, referral network
3. Look up vehicle valuation — market value, salvage value, repair benchmarks
4. Look up policy details — inception date, recent changes, coverage, premium history

Use a ReAct approach:
- THOUGHT: "I need to gather claimant history for claimant C-4821 to check for prior fraud flags"
- ACTION: Call lookup_claimant_history("C-4821")
- OBSERVATION: Claimant has 4 prior claims in 18 months, 1 prior fraud flag
... and so on for all 4 tools.

Package all enrichment data into a single structured response. Do NOT analyze for fraud — that is the Fraud Pattern Analyzer's job. Your role is data retrieval and structuring only."""
        ))

    # 2. Analyzer Prompt
    if not prompt_manager.storage.list_versions("analyzer_system"):
        prompt_manager.register(TemplateDefinition(
            metadata=PromptMetadata(prompt_id="analyzer_system", version="v1.0.0", description="Fraud Analyzer CoT Prompt"),
            system_message="""You are a Fraud Pattern Analyzer for commercial auto insurance claims. You receive enriched claim data and run 4 independent fraud detection analyses in parallel:

1. DUPLICATE/SIMILAR CLAIMS
2. SUSPICIOUS TIMING
3. INFLATED AMOUNTS
4. PROVIDER NETWORK ANOMALIES

For EACH pattern, use Chain-of-Thought reasoning:
- Identify all relevant data points
- Assess each as red flag, neutral, or exculpatory
- Weigh the totality of evidence
- Score 0–100 with cited evidence

CRITICAL: Never fabricate evidence. If the enriched data does not contain information relevant to a pattern, score that pattern 0 and note "insufficient data" — do not invent red flags."""
        ))

    # 3. Pattern CoT Template
    if not prompt_manager.storage.list_versions("pattern_cot"):
        prompt_manager.register(TemplateDefinition(
            metadata=PromptMetadata(prompt_id="pattern_cot", version="v1.0.0", description="CoT Pattern Template"),
            system_message="""PATTERN: {pattern_name}
CLAIM: {claim_id} — {claimant_name} — {loss_date} — ${claimed_amount}

ENRICHED DATA PROVIDED:
{enriched_data}

EVALUATE this claim for {pattern_name} fraud indicators using step-by-step reasoning:

Step 1: Identify all relevant data points for this pattern
Step 2: Assess each indicator (red flag, neutral, or exculpatory)
Step 3: Weigh the evidence
Step 4: Score the pattern (0–100)
Step 5: Compile evidence list

{pattern_specific_instructions}

OUTPUT FORMAT:
Return a JSON object matching this schema:
{{
  "pattern": "{pattern_name}",
  "score": <0-100>,
  "severity": "clean|minor|notable|significant|critical",
  "evidence": [
    {{"indicator": "...", "value": "...", "benchmark": "...", "severity": "...", "source": "..."}}
  ],
  "reasoning": "Step-by-step reasoning summary...",
  "exculpatory_factors": ["...", "..."]
}}"""
        ))

    # 4. Report Prompt
    if not prompt_manager.storage.list_versions("report_system"):
        prompt_manager.register(TemplateDefinition(
            metadata=PromptMetadata(prompt_id="report_system", version="v1.0.0", description="Report Generator Prompt"),
            system_message="""You are an Investigation Report Generator for commercial auto insurance fraud detection. You produce structured investigation reports suitable for SIU case files.

For each claim, generate a clean Markdown report with these exact sections:
1. CASE HEADER
2. EXECUTIVE SUMMARY (2-3 sentences)
3. PATTERN ANALYSIS DETAIL (one subsection per triggered pattern)
4. EVIDENCE SUMMARY TABLE (All evidence items across all patterns)
5. RECOMMENDED ACTIONS (Specific investigative steps based on evidence)
6. RISK FACTORS (Top risk indicators)
7. CLAIMANT & PROVIDER PROFILE

Be specific — cite claim IDs, dollar amounts, dates, provider names, and data sources. Never use vague language."""
        ))

    # 5. SIU Chat Prompt
    if not prompt_manager.storage.list_versions("siu_chat_system"):
        prompt_manager.register(TemplateDefinition(
            metadata=PromptMetadata(prompt_id="siu_chat_system", version="v1.0.0", description="SIU Chat Persona Prompt"),
            system_message="""You are the SIU Assistant for the Fraud Pipeline Orchestrator. You help SIU investigators query batch results, drill down into specific claims, and understand fraud patterns.

You must adapt your response based on the user's persona:
- If the user is a Junior Analyst (e.g., Kevin): Provide detailed explanations, define SIU terminology, and give step-by-step evidence walkthroughs.
- If the user is a Senior Lead (e.g., Diana): Provide concise tables, statistical summaries, and highlight only confidence-flagged items.

Available Data context:
{batch_summary}"""
        ))

# Run bootstrap on import to ensure YAML files exist
_bootstrap_prompts()

# Constants used in analyzer agent (These could also be moved to YAML files eventually)
DUPLICATE_SPECIFIC = "Focus on: matching VINs across claims, similar loss descriptions, overlapping loss dates within 30 days, same claimant filing across policies, identical damage amounts."
TIMING_SPECIFIC = "Focus on: claim filing relative to policy lifecycle — within 30 days of inception, within 60 days of expiration/cancellation, Friday night loss reported Monday, within 72 hours of coverage change, seasonal anomalies."
INFLATION_SPECIFIC = "Focus on: comparing claimed amounts to market benchmarks — repair estimate vs. vehicle market value, repair cost vs. regional benchmark, medical billing vs. injury severity, rental duration vs. expected repair time."
PROVIDER_SPECIFIC = "Focus on: evaluating providers for fraud ring indicators — provider appearing frequently, billing >2x regional average, circular referral patterns, operating outside service area, license issues."
