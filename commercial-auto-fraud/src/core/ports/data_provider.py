from abc import ABC, abstractmethod
from typing import Dict, Any

class IEnrichmentProvider(ABC):
    """Interface for fetching data from external systems for claim enrichment."""
    
    @abstractmethod
    async def get_claimant_history(self, claimant_id: str) -> Dict[str, Any]:
        pass
        
    @abstractmethod
    async def get_provider_network(self, provider_id: str, provider_type: str) -> Dict[str, Any]:
        pass
        
    @abstractmethod
    async def get_vehicle_valuation(self, vin: str, year: int, make: str, model: str) -> Dict[str, Any]:
        pass
        
    @abstractmethod
    async def get_policy_details(self, policy_number: str) -> Dict[str, Any]:
        pass

