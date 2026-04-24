from abc import ABC, abstractmethod
from typing import Dict, Any

class IStorageRepository(ABC):
    """Interface for saving and loading batches, claims, and reports."""
    
    @abstractmethod
    async def save_batch(self, batch_id: str, data: Dict[str, Any]) -> None:
        pass
        
    @abstractmethod
    async def load_batch(self, batch_id: str) -> Dict[str, Any]:
        pass
        
    @abstractmethod
    async def save_investigation_report(self, claim_id: str, report_data: Dict[str, Any]) -> None:
        pass
        
    @abstractmethod
    async def load_investigation_report(self, claim_id: str) -> Dict[str, Any]:
        pass

