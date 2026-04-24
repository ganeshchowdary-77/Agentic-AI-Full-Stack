import json
import os
from typing import Dict, Any
from src.core.ports.repository import IStorageRepository

class LocalStorageRepository(IStorageRepository):
    def __init__(self, base_dir: str = "fraud_data_store"):
        self.base_dir = base_dir
        self.batches_dir = os.path.join(base_dir, "claim_batches")
        self.reports_dir = os.path.join(base_dir, "investigation_reports")
        os.makedirs(self.batches_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)
        
    async def save_batch(self, batch_id: str, data: Dict[str, Any]) -> None:
        path = os.path.join(self.batches_dir, f"{batch_id}.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
            
    async def load_batch(self, batch_id: str) -> Dict[str, Any]:
        path = os.path.join(self.batches_dir, f"{batch_id}.json")
        if not os.path.exists(path):
            return {}
        with open(path, "r") as f:
            return json.load(f)
            
    async def save_investigation_report(self, claim_id: str, report_data: Dict[str, Any]) -> None:
        path = os.path.join(self.reports_dir, f"{claim_id}.json")
        with open(path, "w") as f:
            json.dump(report_data, f, indent=2)
            
    async def load_investigation_report(self, claim_id: str) -> Dict[str, Any]:
        path = os.path.join(self.reports_dir, f"{claim_id}.json")
        if not os.path.exists(path):
            return {}
        with open(path, "r") as f:
            return json.load(f)

