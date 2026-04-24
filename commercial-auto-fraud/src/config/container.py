"""
Dependency Injection Container
================================
Single wiring point for the entire application.
All dependencies flow inward — no module imports siblings directly.

To add a new agent:
  1. Build the agent module in src/application/agents/{name}/
  2. Import and instantiate here
  3. Pass to anything that needs it

To swap a component (e.g., real DB instead of local JSON storage):
  1. Implement IStorageRepository
  2. Change the single line below — nothing else
"""

from src.infrastructure.adapters.local_storage import LocalStorageRepository
from src.infrastructure.adapters.mock_apis import MockEnrichmentProvider
from src.presentation.a2a.client import (
    A2AEnrichmentClient,
    A2AAnalyzerClient,
    A2AReportGeneratorClient,
)
from src.application.agents.orchestrator.agent import OrchestratorAgent


class Container:
    def __init__(self):
        # Infrastructure layer
        self.storage            = LocalStorageRepository()
        self.data_provider      = MockEnrichmentProvider()

        # A2A transport clients
        self.enrichment_client  = A2AEnrichmentClient()
        self.analyzer_client    = A2AAnalyzerClient()
        self.report_client      = A2AReportGeneratorClient()

        # Agents (injected with their dependencies)
        self.orchestrator = OrchestratorAgent(
            enrichment_client=self.enrichment_client,
            analyzer_client=self.analyzer_client,
            report_client=self.report_client,
            storage=self.storage,
        )
